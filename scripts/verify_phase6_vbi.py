#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P227A: independent MQTT5 minimal-VBI wire vectors and MQTT311 controls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True


def binary_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def integer(value):
    output = bytearray()
    while True:
        digit, value = value % 128, value // 128
        output.append(digit | (128 if value else 0))
        if not value:
            return bytes(output)


def redundant(value, length=2):
    output = bytearray(integer(value))
    if len(output) >= length or length > 4:
        raise AssertionError('redundant test encoding must actually add digits')
    while len(output) < length:
        output[-1] |= 128
        output.append(0)
    return bytes(output)


def text(value):
    return len(value).to_bytes(2, 'big') + value


def frame(header, body, overlong=False):
    return bytes([header]) + (redundant(len(body)) if overlong else integer(len(body))) + body


def exact(stream, count):
    output = bytearray()
    while len(output) < count:
        chunk = stream.recv(count - len(output))
        if not chunk:
            raise EOFError('peer closed during bounded MQTT response')
        output.extend(chunk)
    return bytes(output)


def packet(stream, first=None):
    header = exact(stream, 1)[0] if first is None else first
    remaining = 0
    for index in range(4):
        digit = exact(stream, 1)[0]
        remaining += (digit & 127) << (7 * index)
        if remaining > 65536:
            raise AssertionError('response exceeded test packet bound')
        if not digit & 128:
            return header, exact(stream, remaining)
    raise AssertionError('response Remaining Length exceeded four digits')


def connect_body(identity, *, mqtt5=True, will=None, properties=b'', property_length=None,
                 will_length=None):
    body = b'\0\x04MQTT' + bytes([5 if mqtt5 else 4, 6 if will else 2]) + b'\0\x1e'
    if mqtt5:
        body += integer(len(properties)) if property_length is None else property_length
        body += properties
    body += text(identity)
    if will:
        if mqtt5:
            body += b'\0' if will_length is None else will_length
        body += text(will[0]) + text(will[1])
    return body


class Laboratory:
    def __init__(self, binary, state):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.port = probe.getsockname()[1]
        environment = {key: value for key, value in os.environ.items() if not key.startswith('MQTT_')}
        environment.update(MQTT_MODE='open-lab', MQTT_BIND=f'127.0.0.1:{self.port}',
                           MQTT_STATE_DIR=str(state), RUST_LOG='error')
        self.environment = environment
        self.binary = binary
        self.process = None
        self.peers = []

    def start(self):
        self.process = subprocess.Popen([str(self.binary)], env=self.environment,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError('private broker exited before readiness')
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=.1):
                    return
            except OSError:
                time.sleep(.05)
        raise TimeoutError('private broker readiness deadline')

    def peer(self):
        stream = socket.create_connection(('127.0.0.1', self.port), timeout=4)
        stream.settimeout(4)
        self.peers.append(stream)
        return stream

    def connect(self, identity, **options):
        stream = self.peer()
        stream.sendall(frame(0x10, connect_body(identity, **options)))
        header, body = packet(stream)
        if header != 0x20 or len(body) < 2 or body[1] != 0:
            raise AssertionError('canonical control CONNECT was not accepted')
        return stream

    def release_peers(self):
        for peer in self.peers:
            peer.close()
        self.peers.clear()

    def stop(self):
        self.release_peers()
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
        try:
            code = self.process.wait(timeout=16)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=4)
            raise AssertionError('private broker shutdown deadline') from None
        if code != 0:
            raise AssertionError('private broker did not exit successfully')


def subscribe(stream, topic, properties=b''):
    stream.sendall(frame(0x82, b'\0\x01' + integer(len(properties)) + properties + text(topic) + b'\0'))
    if packet(stream) != (0x90, b'\0\x01\0\0'):
        raise AssertionError('canonical control subscription was not acknowledged')


def invalid_established(lab, name, make_frame, *, fragmented=False):
    prefix = ('p227a/' + name).encode()
    watcher = lab.connect(b'watch-' + name.encode())
    subscribe(watcher, prefix + b'/#')
    will_payload = b'expected-will'
    source = lab.connect(b'source-' + name.encode(), will=(prefix + b'/will', will_payload))
    wire = make_frame(prefix)
    if fragmented:
        source.sendall(wire[:-1])
        source.settimeout(.2)
        try:
            source.recv(1)
        except socket.timeout:
            pass
        else:
            raise AssertionError('incomplete VBI was rejected before terminating digit')
        source.settimeout(4)
        source.sendall(wire[-1:])
    else:
        source.sendall(wire)
    if packet(source) != (0xe0, b'\x81\0'):
        raise AssertionError('noncanonical MQTT5 VBI did not produce DISCONNECT0x81')
    if source.recv(1) != b'':
        raise AssertionError('invalid MQTT5 connection stayed open')
    header, body = packet(watcher)
    topic_length = int.from_bytes(body[:2], 'big')
    topic = body[2:2 + topic_length]
    payload = body[3 + topic_length:]  # QoS0, canonical empty Property Length.
    if header != 0x30 or topic != prefix + b'/will' or payload != will_payload:
        raise AssertionError('invalid frame was applied or original Will was not preserved')
    watcher.sendall(b'\xe0\0')


def invalid_initial(lab, name, *, property_length=None, will_length=None, overlong=False, maximum=None):
    identity = b'initial-' + name.encode()
    watcher = lab.connect(b'initial-observer-' + name.encode())
    subscribe(watcher, b'p227a/initial/will')
    properties = b'' if maximum is None else b'\x27' + maximum.to_bytes(4, 'big')
    will = (b'p227a/initial/will', b'forbidden-will')
    body = connect_body(identity, will=will, properties=properties,
                        property_length=property_length, will_length=will_length)
    stream = lab.peer()
    stream.sendall(frame(0x10, body, overlong=overlong))
    first = stream.recv(1)
    if maximum == 4 and first:
        raise AssertionError('initial rejection exceeded known Maximum Packet Size4')
    if first:
        if packet(stream, first[0]) != (0x20, b'\0\x81\0'):
            raise AssertionError('invalid initial CONNECT received acceptance or wrong reason')
        if stream.recv(1) != b'':
            raise AssertionError('initial rejected connection stayed open')
    elif overlong or will_length is not None:
        if maximum != 4:
            raise AssertionError('known initial MQTT5 boundary omitted expected CONNACK0x81')
    watcher.sendall(b'\xc0\0')
    if packet(watcher) != (0xd0, b''):
        raise AssertionError('rejected initial CONNECT registered or published its Will')
    watcher.settimeout(.2)
    try:
        watcher.recv(1)
    except socket.timeout:
        pass
    else:
        raise AssertionError('rejected initial CONNECT produced a delayed Will')
    watcher.settimeout(4)
    watcher.sendall(b'\xe0\0')


def canonical_controls(lab):
    legacy = lab.peer()
    legacy.sendall(frame(0x10, connect_body(b'legacy-vbi', mqtt5=False), overlong=True))
    if packet(legacy) != (0x20, b'\0\0'):
        raise AssertionError('MQTT311 initial CONNECT Remaining Length behavior changed')
    legacy.sendall(b'\xc0\x80\0')
    if packet(legacy) != (0xd0, b''):
        raise AssertionError('MQTT311 historical Remaining Length behavior changed')
    legacy.sendall(b'\xe0\0')
    # Property Length128 and Subscription Identifier128 exercise canonical two-byte VBIs.
    properties = b'\x26' + text(b'k' * 61) + text(b'v' * 62)
    if len(properties) != 128:
        raise AssertionError('canonical property boundary fixture changed')
    subscriber = lab.connect(b'canonical-boundaries', properties=properties)
    subscribe(subscriber, b'p227a/canonical', b'\x0b' + integer(128))
    publisher = lab.connect(b'canonical-publisher')
    publisher.sendall(frame(0x30, text(b'p227a/canonical') + integer(len(properties)) + properties + b'ok'))
    header, body = packet(subscriber)
    if header != 0x30 or not body.endswith(b'ok'):
        raise AssertionError('canonical metadata publication failed')
    publisher.sendall(b'\xc0\0')
    if packet(publisher) != (0xd0, b''):
        raise AssertionError('canonical PINGREQ failed')
    for peer in (publisher, subscriber):
        peer.sendall(b'\xe0\0')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    parser.add_argument('--label', choices=('baseline', 'candidate'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and exclusive new report required')
    filesystem = subprocess.check_output(['stat', '-f', '-c', '%T', str(args.state_root)], text=True).strip()
    if filesystem not in ('ext2/ext3', 'ext4', 'xfs', 'btrfs', 'zfs'):
        parser.error('native Linux disk-backed state root required')
    report = dict(schema_version=1, label=args.label, status='RUNNING', scenarios=[],
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), filesystem=filesystem,
                  clauses=['MQTT-1.5.5-1', 'MQTT-4.13.1-1'],
                  limitations=['synthetic open-lab TCP only', 'not phase6 global acceptance or TLS evidence'])
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='xmqr-p227a-', dir=args.state_root) as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        binary = root / 'mqtt-broker'
        shutil.copyfile(args.broker.resolve(strict=True), binary)
        binary.chmod(0o700)
        report['broker_binary_sha256'] = binary_digest(binary)
        report['broker_version'] = subprocess.check_output([str(binary), '--version'], text=True, timeout=5).strip()
        state = root / 'state'
        state.mkdir(mode=0o700)
        lab = Laboratory(binary, state)
        cases = [('canonical_controls', lambda: canonical_controls(lab))]
        for length in (2, 3, 4):
            name = f'remaining_length_{length}'
            cases.append((name, lambda n=name, size=length:
                          invalid_established(lab, n, lambda _: b'\xc0' + redundant(0, size))))
        cases.append(('fragmented_remaining_length', lambda: invalid_established(
            lab, 'fragmented_remaining_length', lambda _: b'\xc0\x80\0', fragmented=True)))
        cases.append(('remaining_length_before_body', lambda: invalid_established(
            lab, 'remaining_length_before_body', lambda _: b'\x30\x81\0')))
        for name, header in [('publish', 0x31), ('subscribe', 0x82), ('unsubscribe', 0xa2),
                             ('puback', 0x40), ('pubrec', 0x50), ('pubrel', 0x62), ('pubcomp', 0x70),
                             ('auth', 0xf0), ('disconnect', 0xe0)]:
            def vector(prefix, kind=name, first=header):
                if kind == 'publish':
                    body = text(prefix + b'/data') + b'\x80\0invalid'
                elif kind in ('subscribe', 'unsubscribe'):
                    body = b'\0\x01\x80\0' + text(prefix + b'/sub') + (b'\0' if kind == 'subscribe' else b'')
                elif kind in ('auth', 'disconnect'):
                    body = bytes([0x19 if kind == 'auth' else 0]) + b'\x80\0'
                else:
                    body = b'\0\x01\0\x80\0'
                return frame(first, body)
            case_name = 'property_length_' + name
            cases.append((case_name, lambda n=case_name, make=vector: invalid_established(lab, n, make)))
        cases.append(('subscription_identifier', lambda: invalid_established(
            lab, 'subscription_identifier', lambda prefix:
            frame(0x82, b'\0\x01\x03\x0b\x81\0' + text(prefix + b'/sub') + b'\0'))))
        cases.extend([
            ('initial_remaining_length', lambda: invalid_initial(lab, 'rl', overlong=True)),
            ('initial_property_length', lambda: invalid_initial(lab, 'props', property_length=b'\x80\0')),
            ('initial_will_property_length', lambda: invalid_initial(lab, 'will', will_length=b'\x80\0')),
            ('initial_remaining_length_max4', lambda: invalid_initial(lab, 'max4', overlong=True, maximum=4)),
            ('initial_remaining_length_max5', lambda: invalid_initial(lab, 'max5', overlong=True, maximum=5)),
        ])
        try:
            lab.start()
            for name, exercise in cases:
                case_began = time.monotonic()
                result = dict(scenario=name, status='RUNNING')
                try:
                    exercise()
                    if lab.process.poll() is not None:
                        raise AssertionError('private broker died during VBI scenario')
                    result['status'] = 'PASS'
                except Exception as failure:
                    result.update(status='FAIL', error_type=type(failure).__name__,
                                  error=str(failure) if isinstance(failure, AssertionError)
                                  else 'bounded wire operation failed')
                finally:
                    lab.release_peers()
                result['seconds'] = round(time.monotonic() - case_began, 3)
                report['scenarios'].append(result)
                print(json.dumps(result), flush=True)
        except Exception as failure:
            report.update(fixture_error_type=type(failure).__name__,
                          fixture_error='private fixture startup or execution failed')
        finally:
            try:
                lab.stop()
                report['cleanup'] = 'PASS'
            except Exception as failure:
                report.update(cleanup='FAIL', cleanup_error_type=type(failure).__name__)
    report.update(status='PASS' if report.get('cleanup') == 'PASS' and
                  'fixture_error_type' not in report and len(report['scenarios']) == len(cases) and
                  all(case['status'] == 'PASS' for case in report['scenarios']) else 'FAIL',
                  observed_seconds=round(time.monotonic() - began, 3),
                  completed_utc=datetime.now(timezone.utc).isoformat())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    if report['status'] != 'PASS':
        raise SystemExit(1)
    print('P227_VBI_PASS', flush=True)


if __name__ == '__main__':
    main()
