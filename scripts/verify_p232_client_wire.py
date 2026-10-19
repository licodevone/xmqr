#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P232: bounded synthetic-server audit probes; never contacts a real broker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time

from verify_phase6_vbi import frame, packet, text


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Peer:
    def __init__(self, binary, folder, command, extra):
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(1)
        self.listener.settimeout(4)
        self.stream = None
        self.output = tempfile.TemporaryFile(dir=folder)
        self.errors = tempfile.TemporaryFile(dir=folder)
        environment = {k: v for k, v in os.environ.items() if not k.startswith('MQTT_')}
        arguments = [str(binary), command, '--open-lab', '--protocol-version', '5',
                     '--host', '127.0.0.1', '--port', str(self.listener.getsockname()[1]),
                     '--client-id', 'p232-audit', '--topic', 'p232/topic',
                     '--timeout-seconds', '2', '--total-timeout-seconds', '8']
        arguments += (['--message', 'synthetic-audit'] if command == 'pub'
                      else ['--output', 'jsonl'])
        self.process = subprocess.Popen(arguments + extra, env=environment,
                                        stdout=self.output, stderr=self.errors)

    def handshake(self, properties=b'', connack=None):
        self.stream, _ = self.listener.accept()
        self.stream.settimeout(2)
        if packet(self.stream)[0] != 0x10:
            raise AssertionError('client did not send CONNECT to private listener')
        self.stream.sendall(connack if connack is not None
                            else frame(0x20, b'\0\0' + bytes([len(properties)]) + properties))

    def receive(self):
        try:
            return packet(self.stream)
        except (EOFError, ConnectionResetError):
            return None

    def subscribe(self):
        request = self.receive()
        if request is None or request[0] != 0x82:
            raise AssertionError('canonical subscription control failed')
        requested_qos = request[1][-1] & 3  # Single synthetic filter/options.
        self.stream.sendall(frame(0x90, request[1][:2] + bytes([0, requested_qos])))

    def finish_subscriber(self):
        reply = self.receive()
        if reply and reply[0] == 0xa2:
            self.stream.sendall(frame(0xb0, reply[1][:2] + b'\0\0'))
            reply = self.receive()
        if reply is not None and reply[0] != 0xe0:
            raise AssertionError(f'unexpected subscriber cleanup packet {reply[0]:02x}')
        return self.process.wait(timeout=3)

    def finish_publisher(self, publish, ack_header=0x40):
        if publish is None:
            return self.process.wait(timeout=3)
        if publish[0] >> 4 != 3:
            raise AssertionError('expected PUBLISH or rejection')
        qos = (publish[0] >> 1) & 3
        if qos:
            size = int.from_bytes(publish[1][:2], 'big')
            identifier = publish[1][2 + size:4 + size]
            self.stream.sendall(frame(ack_header, identifier))
        # Both accepted and correctly rejected malformed ACK paths are allowed.
        self.receive()
        return self.process.wait(timeout=3)

    def close(self):
        if self.stream is not None:
            self.stream.close()
        self.listener.close()
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
                raise AssertionError('private client required forced termination')
        for stream in (self.output, self.errors):
            stream.seek(0, 2)
            if stream.tell() > 4 * 1024 * 1024:
                raise AssertionError('client output exceeded audit bound')
            stream.close()


def publisher_case(binary, folder, name, *, properties=b'', connack=None,
                   retain=False, invalid_ack=False, must_reject=False, fresh_resume=False):
    extra = ['--qos', '1', '--retain', str(retain).lower()]
    if fresh_resume:
        extra += ['--clean-start', 'false', '--session-expiry-seconds', '60']
    peer = Peer(binary, folder, 'pub', extra)
    try:
        peer.handshake(properties, connack)
        publish = peer.receive()
        code = peer.finish_publisher(publish, 0x41 if invalid_ack else 0x40)
        if must_reject:
            compliant = publish is None and code != 0
        elif invalid_ack:
            compliant = code != 0
        else:
            compliant = publish is not None and code == 0
        return {'name': name, 'status': 'PASS' if compliant else 'FAIL',
                'observed_header': publish[0] if publish else None,
                'process_exit': code, 'kind': 'wire_probe'}
    finally:
        peer.close()


def subscriber_string_case(binary, folder, name, topic, *, must_reject):
    peer = Peer(binary, folder, 'sub', ['--count', '1', '--qos', '0'])
    try:
        peer.handshake()
        peer.subscribe()
        peer.stream.sendall(frame(0x30, text(topic) + b'\0synthetic-audit'))
        code = peer.finish_subscriber()
        peer.output.seek(0)
        rows = [json.loads(line) for line in peer.output.read(65536).splitlines()]
        delivered = [row for row in rows if row.get('event') == 'publish']
        matches = (len(delivered) == 1 and delivered[0].get('payload_bytes') == list(b'synthetic-audit')
                   and delivered[0].get('topic', '').encode('utf-8') == topic)
        compliant = (code != 0 and not delivered) if must_reject else (code == 0 and matches)
        return {'name': name, 'status': 'PASS' if compliant else 'FAIL',
                'process_exit': code, 'displayed_rows': len(delivered),
                'displayed_expected_topic_and_payload': matches, 'kind': 'wire_probe'}
    finally:
        peer.close()


def qos2_repeat_case(binary, folder):
    peer = Peer(binary, folder, 'sub', ['--count', '2', '--qos', '2'])
    try:
        peer.handshake()
        peer.subscribe()
        peer.stream.sendall(frame(0x34, text(b'p232/topic') + b'\0\x49\0first'))
        if peer.receive() != (0x50, b'\0\x49'):
            raise AssertionError('canonical QoS2 PUBREC control failed')
        peer.stream.sendall(frame(0x62, b'\0\x49'))
        first = peer.receive()
        if first is None or first[0] != 0x70 or first[1][:2] != b'\0\x49':
            raise AssertionError('canonical QoS2 PUBCOMP control failed')
        peer.stream.sendall(frame(0x62, b'\0\x49'))
        repeated = peer.receive()
        compliant = repeated is not None and repeated[0] == 0x70 and repeated[1][:2] == b'\0\x49'
        if compliant:
            peer.stream.sendall(frame(0x30, text(b'p232/topic') + b'\0last'))
            code = peer.finish_subscriber()
        else:
            code = peer.process.wait(timeout=3)
        return {'name': 'qos2_repeated_pubrel', 'status': 'PASS' if compliant else 'FAIL',
                'canonical_qos2_cycle': 'PASS', 'process_exit': code,
                'repeated_reply_header': repeated[0] if repeated else None,
                'clauses': ['MQTT-4.3.3-11'], 'kind': 'wire_probe'}
    finally:
        peer.close()


def qos2_duplicate_case(binary, folder):
    peer = Peer(binary, folder, 'sub', ['--count', '2', '--qos', '2'])
    try:
        peer.handshake()
        peer.subscribe()
        body = text(b'p232/topic') + b'\0\x49\0first'
        peer.stream.sendall(frame(0x34, body))
        if peer.receive() != (0x50, b'\0\x49'):
            raise AssertionError('canonical QoS2 PUBREC control failed')
        # Synthetic duplicate to exercise receiver 4.3.3-10, not sender retry permission.
        peer.stream.sendall(frame(0x3c, body))
        if peer.receive() != (0x50, b'\0\x49'):
            raise AssertionError('retransmitted QoS2 did not receive PUBREC')
        peer.stream.settimeout(.2)
        try:
            early = peer.receive()
        except socket.timeout:
            early = 'waiting'
        peer.stream.settimeout(2)
        if early == 'waiting':
            peer.stream.sendall(frame(0x62, b'\0\x49'))
            reply = peer.receive()
            if reply is None or reply[0] != 0x70:
                raise AssertionError('QoS2 PUBCOMP missing')
            peer.stream.sendall(frame(0x30, text(b'p232/topic') + b'\0last'))
            code = peer.finish_subscriber()
        elif early is not None and early[0] == 0xa2:
            peer.stream.sendall(frame(0xb0, early[1][:2] + b'\0\0'))
            peer.receive()
            code = peer.process.wait(timeout=3)
        else:
            raise AssertionError('unexpected response to duplicated QoS2')
        peer.output.seek(0)
        rows = [json.loads(line) for line in peer.output.read(65536).splitlines()]
        first_count = sum(row.get('payload_bytes') == list(b'first') for row in rows)
        compliant = first_count == 1 and code == 0
        return {'name': 'qos2_duplicate_delivery', 'status': 'PASS' if compliant else 'FAIL',
                'displayed_same_transaction': first_count, 'process_exit': code,
                'clauses': ['MQTT-4.3.3-10'], 'kind': 'wire_probe'}
    finally:
        peer.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--client-source-commit', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and an exclusive new report are required')
    if not re.fullmatch('[0-9a-f]{40}', args.client_source_commit):
        parser.error('full lowercase client source SHA required')
    binary = args.client.resolve(strict=True)
    before = digest(binary)
    version = subprocess.check_output([str(binary), '--version'], text=True, timeout=5).strip()
    report = {'schema_version': 1, 'audit': 'P232', 'binary_sha256': before,
              'version': version, 'source_commit_declared': args.client_source_commit,
              'harness_sha256': digest(Path(__file__)),
              'helper_sha256': digest(Path(__file__).with_name('verify_phase6_vbi.py')),
              'scenarios': [], 'limitations': [
                  'synthetic loopback TCP server, not TLS or production',
                  'declared source must be tied to package evidence separately',
                  'a PASS is only the stated probe, not whole-clause conformance',
                  'FAIL of a receiving recommendation is not automatically a MUST violation']}
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='xmqr-p232-client-', dir=args.state_root) as folder:
        cases = [
            ('canonical_pub_qos1', lambda: publisher_case(binary, folder, 'canonical_pub_qos1')),
            ('canonical_sub', lambda: subscriber_string_case(binary, folder, 'canonical_sub', b'p232/topic', must_reject=False)),
            ('nul_topic', lambda: subscriber_string_case(binary, folder, 'nul_topic', b'p232/\0topic', must_reject=True)),
            ('malformed_utf8_topic', lambda: subscriber_string_case(binary, folder, 'malformed_utf8_topic', b'p232/\xff', must_reject=True)),
            ('nonminimal_connack_vbi', lambda: publisher_case(binary, folder, 'nonminimal_connack_vbi', connack=b'\x20\x83\0\0\0\0', must_reject=True)),
            ('reserved_puback_flags', lambda: publisher_case(binary, folder, 'reserved_puback_flags', invalid_ack=True)),
            ('maximum_qos_zero', lambda: publisher_case(binary, folder, 'maximum_qos_zero', properties=b'\x24\0', must_reject=True)),
            ('retain_unavailable', lambda: publisher_case(binary, folder, 'retain_unavailable', properties=b'\x25\0', retain=True, must_reject=True)),
            ('resume_without_local_session_state', lambda: publisher_case(binary, folder, 'resume_without_local_session_state', connack=b'\x20\x03\x01\0\0', fresh_resume=True, must_reject=True)),
            ('nul_user_property', lambda: publisher_case(binary, folder, 'nul_user_property', properties=b'\x26' + text(b'x') + text(b'\0'), must_reject=True)),
            ('qos2_repeated_pubrel', lambda: qos2_repeat_case(binary, folder)),
            ('qos2_duplicate_delivery', lambda: qos2_duplicate_case(binary, folder)),
        ]
        for name, operation in cases:
            try:
                result = operation()
            except Exception as error:
                result = {'name': name, 'status': 'BLOCKED', 'error_type': type(error).__name__,
                          'reason': str(error)[:180], 'kind': 'harness_or_prerequisite'}
            if name in {'maximum_qos_zero', 'retain_unavailable', 'resume_without_local_session_state',
                        'qos2_repeated_pubrel', 'qos2_duplicate_delivery'}:
                result['category'] = 'MANDATORY_CLIENT_BEHAVIOR'
            elif name in {'canonical_pub_qos1', 'canonical_sub'}:
                result['category'] = 'POSITIVE_CONTROL'
            else:
                result['category'] = 'RECEIVE_RECOMMENDATION'
            report['scenarios'].append(result)
    report['binary_unchanged'] = digest(binary) == before
    report['elapsed_seconds'] = round(time.monotonic() - began, 3)
    report['counts'] = {status: sum(row['status'] == status for row in report['scenarios'])
                        for status in ('PASS', 'FAIL', 'BLOCKED')}
    report['status'] = 'PASS' if all(row['status'] == 'PASS' for row in report['scenarios']) else 'FAIL'
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'counts': report['counts'],
                      'elapsed_seconds': report['elapsed_seconds']}))
    return 0 if report['status'] == 'PASS' and report['binary_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
