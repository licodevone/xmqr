#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P227C: blackbox MQTT5 shared fairness and takeover Will expiry, private loopback only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
from verify_phase6_vbi import Laboratory, frame, integer, packet, text


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def connect(lab, identity, *, persistent=False, will_expiry=None):
    stream = lab.peer()
    properties = b'\x11\xff\xff\xff\xff' if persistent else b''
    flags = 2 | (0x24 if will_expiry is not None else 0)
    body = b'\0\x04MQTT\x05' + bytes([flags]) + b'\0\x1e'
    body += integer(len(properties)) + properties + text(identity)
    if will_expiry is not None:
        will_properties = b'\x18\0\0\0\x3c\x02' + will_expiry.to_bytes(4, 'big')
        body += integer(len(will_properties)) + will_properties
        body += text(b'p227c/will') + text(b'private-will-fixture')
    stream.sendall(frame(0x10, body))
    header, reply = packet(stream)
    require(header == 0x20 and len(reply) >= 3 and reply[:2] == b'\0\0',
            'Clean Start CONNECT must succeed without Session Present')
    return stream


def subscribe(stream, topic):
    stream.sendall(frame(0x82, b'\0\x01\0' + text(topic) + b'\0'))
    require(packet(stream) == (0x90, b'\0\x01\0\0'), 'QoS0 SUBACK mismatch')


def ping(stream):
    stream.sendall(b'\xc0\0')
    require(packet(stream) == (0xd0, b''), 'unexpected packet before PINGRESP barrier')


def quiet(streams, seconds=.15):
    require(not select.select(streams, [], [], seconds)[0],
            'unexpected delivery or connection closure during quiet window')


def publish_qos1(stream, topic, payload, identifier):
    stream.sendall(frame(0x32, text(topic) + identifier.to_bytes(2, 'big') + b'\0' + payload))
    header, ack = packet(stream)
    require(header == 0x40 and len(ack) >= 2 and ack[:2] == identifier.to_bytes(2, 'big')
            and (len(ack) == 2 or ack[2] == 0), 'publisher PUBACK mismatch')


def delivery(stream, topic, payload, *, retained=False, expiry=None):
    header, body = packet(stream)
    require(header == (0x31 if retained else 0x30), 'QoS0 PUBLISH flags mismatch')
    require(len(body) >= 3, 'PUBLISH response truncated')
    length = int.from_bytes(body[:2], 'big')
    require(body[2:2 + length] == topic, 'PUBLISH topic mismatch')
    position = 2 + length
    size = 0
    for index in range(4):
        require(position < len(body), 'PUBLISH Property Length truncated')
        digit = body[position]
        position += 1
        size += (digit & 127) << (7 * index)
        if not digit & 128:
            break
    else:
        raise AssertionError('PUBLISH Property Length exceeds four bytes')
    require(position + size <= len(body), 'PUBLISH properties exceed packet')
    properties = body[position:position + size]
    require(body[position + size:] == payload, 'PUBLISH payload mismatch')
    if expiry is None:
        require(properties == b'', 'unexpected PUBLISH metadata')
    else:
        require(len(properties) == 5 and properties[0] == 2,
                'takeover Will must preserve Message Expiry property')
        remaining = int.from_bytes(properties[1:], 'big')
        require(0 < remaining <= expiry, 'Will remaining expiry outside configured lifetime')


def shared_fairness(lab):
    publisher = connect(lab, b'p227c-source')
    members = []
    for identity, group in [(b'a0', b'a'), (b'a1', b'a'), (b'b0', b'b'), (b'b1', b'b')]:
        member = connect(lab, b'p227c-' + identity)
        subscribe(member, b'$share/' + group + b'/p227c/' + group)
        members.append(member)
    counts = [0, 0, 0, 0]
    for sequence in range(4):
        for group_index, group in enumerate((b'a', b'b')):
            payload = bytes([sequence, group_index])
            publish_qos1(publisher, b'p227c/' + group, payload, 1 + sequence * 2 + group_index)
            ready, _, _ = select.select(members, [], [], 3)
            require(len(ready) == 1, 'expected exactly one shared recipient per publication')
            winner = members.index(ready[0])
            require(winner // 2 == group_index, 'publication crossed independent shared groups')
            delivery(ready[0], b'p227c/' + group, payload)
            counts[winner] += 1
            for member in members:
                ping(member)
            quiet(members, .05)
    require(counts == [2, 2, 2, 2], 'interleaved shared groups must each distribute two plus two')
    return dict(publications=8, recipient_counts=counts)


def takeover(lab, expiry):
    watcher = connect(lab, b'p227c-watcher')
    subscribe(watcher, b'p227c/will')
    source = connect(lab, b'p227c-will-source', persistent=True, will_expiry=expiry)
    # Both registrations are live. Replacement CONNACK and prior EOF are barriers,
    # avoiding any guess about TCP close -> router unregister timing.
    began = time.monotonic()
    replacement = connect(lab, b'p227c-will-source', persistent=True)
    require(source.recv(1) == b'', 'takeover must close the previous connection generation')
    ping(replacement)
    if expiry == 0:
        ping(watcher)
        quiet([watcher])
        probe = connect(lab, b'p227c-zero-retained-probe')
        subscribe(probe, b'p227c/will')
        ping(probe)
        quiet([probe])
        return dict(will_forwarded=False, retained_present=False)
    delivery(watcher, b'p227c/will', b'private-will-fixture', expiry=1)
    probe = connect(lab, b'p227c-live-retained-probe')
    subscribe(probe, b'p227c/will')
    delivery(probe, b'p227c/will', b'private-will-fixture', retained=True, expiry=1)
    # A measured real wait is necessary for expiry, but never orders the takeover.
    time.sleep(max(0, began + 1.4 - time.monotonic()))
    after = connect(lab, b'p227c-expired-retained-probe')
    subscribe(after, b'p227c/will')
    ping(after)
    quiet([after])
    return dict(will_forwarded=True, retained_before_expiry=True, retained_after_expiry=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    parser.add_argument('--label', choices=('baseline', 'candidate'), default='candidate')
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and exclusive new report required')
    if not args.broker.is_file() or not os.access(args.broker, os.X_OK):
        parser.error('explicit executable broker required')
    filesystem = subprocess.check_output(['stat', '-f', '-c', '%T', str(args.state_root)], text=True).strip()
    if filesystem not in ('ext2/ext3', 'ext4', 'xfs', 'btrfs', 'zfs'):
        parser.error('native Linux disk-backed state root required')
    report = dict(schema_version=1, label=args.label, status='RUNNING', scenarios=[], filesystem=filesystem,
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  helper_sha256=hashlib.sha256(Path(__file__).with_name('verify_phase6_vbi.py').read_bytes()).hexdigest(),
                  clauses=['MQTT5 section4.8.2', 'MQTT5 section3.1.3.2.4', 'MQTT5 section3.3.2.3.3'],
                  limitations=['synthetic open-lab loopback TCP only', 'fairness within one process lifetime',
                               'not independent library interop, TLS, power loss or global phase6 acceptance'])
    began = time.monotonic()
    cases = [('shared_interleaved_groups', shared_fairness),
             ('takeover_will_expiry0', lambda lab: takeover(lab, 0)),
             ('takeover_will_expiry1', lambda lab: takeover(lab, 1))]
    root = None
    try:
        with tempfile.TemporaryDirectory(prefix='xmqr-p227c-', dir=args.state_root) as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            binary = root / 'mqtt-broker'
            shutil.copyfile(args.broker.resolve(strict=True), binary)
            binary.chmod(0o700)
            report['broker_binary_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
            environment = {key: value for key, value in os.environ.items() if not key.startswith('MQTT_')}
            report['broker_version'] = subprocess.check_output([str(binary), '--version'], env=environment,
                                                                 text=True, timeout=5).strip()
            for index, (name, exercise) in enumerate(cases):
                state = root / f'state-{index}'
                state.mkdir(mode=0o700)
                lab = Laboratory(binary, state)
                case_began = time.monotonic()
                result = dict(scenario=name, status='RUNNING')
                try:
                    lab.start()
                    result['observed'] = exercise(lab)
                    require(lab.process.poll() is None, 'private broker exited during wire scenario')
                    result['status'] = 'PASS'
                except Exception as failure:
                    result.update(status='FAIL', error_type=type(failure).__name__,
                                  error=str(failure) if isinstance(failure, AssertionError)
                                  else 'bounded private wire operation failed')
                finally:
                    try:
                        lab.stop()
                        result['cleanup'] = 'PASS'
                    except Exception as failure:
                        result.update(status='FAIL', cleanup='FAIL', cleanup_error_type=type(failure).__name__)
                result['seconds'] = round(time.monotonic() - case_began, 3)
                report['scenarios'].append(result)
                print(json.dumps(result), flush=True)
    except Exception as failure:
        report.update(fixture_error_type=type(failure).__name__,
                      fixture_error='private fixture setup or cleanup failed')
    report['cleanup'] = 'PASS' if root is not None and not root.exists() and all(
        case.get('cleanup') == 'PASS' for case in report['scenarios']) else 'FAIL'
    report.update(status='PASS' if report['cleanup'] == 'PASS' and 'fixture_error_type' not in report
                  and len(report['scenarios']) == len(cases)
                  and all(case['status'] == 'PASS' for case in report['scenarios']) else 'FAIL',
                  observed_seconds=round(time.monotonic() - began, 3),
                  completed_utc=datetime.now(timezone.utc).isoformat())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    if report['status'] != 'PASS':
        raise SystemExit(1)
    print('P227_SHARED_WILL_PASS', flush=True)


if __name__ == '__main__':
    main()
