#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P227D: independent reasons for invalid versus valid-but-unmapped Topic Alias."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
from verify_phase6_vbi import Laboratory, connect_body, frame, packet, subscribe, text


def publish(stream, topic, alias, payload, *, invalid=False):
    properties = b'\x23' + alias.to_bytes(2, 'big')
    body = text(topic) + (b'\0\x11' if invalid else b'') + bytes([len(properties)]) + properties + payload
    stream.sendall(frame(0x33 if invalid else 0x30, body))


def invalid_case(lab, name, topic_present, alias, reason, maximum=None):
    prefix = b'p227d/' + name.encode()
    watcher = lab.connect(b'watch-' + name.encode())
    subscribe(watcher, prefix + b'/#')
    options = {'properties': b'\x27' + maximum.to_bytes(4, 'big')} if maximum else {}
    source = lab.connect(b'source-' + name.encode(), will=(prefix + b'/will', b'expected-will'), **options)
    publish(source, prefix + b'/data' if topic_present else b'', alias, b'forbidden', invalid=True)
    reply = packet(source)
    if reply != (0xe0, bytes([reason, 0])):
        raise AssertionError(f'expected DISCONNECT0x{reason:02x}, observed header0x{reply[0]:02x}/body{reply[1].hex()}')
    if source.recv(1) != b'':
        raise AssertionError('invalid alias connection stayed open or acknowledged the rejected PUBLISH')
    if packet(watcher) != (0x30, text(prefix + b'/will') + b'\0expected-will'):
        raise AssertionError('invalid alias reached subscriber or original Will was not preserved')
    watcher.sendall(b'\xc0\0')
    if packet(watcher) != (0xd0, b''):
        raise AssertionError('invalid alias produced an extra publication')
    late = lab.connect(b'late-' + name.encode())
    subscribe(late, prefix + b'/#')
    late.sendall(b'\xc0\0')
    if packet(late) != (0xd0, b''):
        raise AssertionError('invalid alias mutated retained state')
    watcher.sendall(b'\xe0\0')
    late.sendall(b'\xe0\0')


def valid_mapping(lab):
    watcher = lab.connect(b'valid-watch')
    subscribe(watcher, b'p227d/valid/#')
    source = lab.connect(b'valid-source')
    for name, payload, expected in ((b'p227d/valid/a', b'first', b'p227d/valid/a'),
                                    (b'', b'second', b'p227d/valid/a'),
                                    (b'p227d/valid/b', b'third', b'p227d/valid/b'),
                                    (b'', b'fourth', b'p227d/valid/b')):
        publish(source, name, 1, payload)
        if packet(watcher) != (0x30, text(expected) + b'\0' + payload):
            raise AssertionError('valid alias establishment/use/replacement changed')
    source.sendall(b'\xe0\0')
    watcher.sendall(b'\xe0\0')


def legacy_control(lab):
    watcher = lab.connect(b'legacy-watch')
    subscribe(watcher, b'p227d/legacy')
    source = lab.peer()
    source.sendall(frame(0x10, connect_body(b'legacy-source', mqtt5=False)))
    if packet(source) != (0x20, b'\0\0'):
        raise AssertionError('MQTT311 CONNECT changed')
    payload = b'\x03\x23\0\x01legacy'
    source.sendall(frame(0x30, text(b'p227d/legacy') + payload))
    if packet(watcher) != (0x30, text(b'p227d/legacy') + b'\0' + payload):
        raise AssertionError('MQTT311 payload was parsed as alias properties')
    source.sendall(b'\xe0\0')
    watcher.sendall(b'\xe0\0')


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
        parser.error('native Linux disk-backed state required')
    helpers = Path(__file__).with_name('verify_phase6_vbi.py')
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(schema_version=1, label=args.label, status='RUNNING', scenarios=[], filesystem=filesystem,
                  harness_sha256=digest(Path(__file__)), helper_sha256=digest(helpers),
                  clauses=['MQTT5 section3.3.4 TopicAlias case3a'],
                  limitations=['synthetic open-lab TCP only', 'not global phase6 acceptance or TLS evidence'])
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='xmqr-p227d-', dir=args.state_root) as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        binary = root / 'mqtt-broker'
        shutil.copyfile(args.broker.resolve(strict=True), binary)
        binary.chmod(0o700)
        report['broker_binary_sha256'] = digest(binary)
        report['broker_version'] = subprocess.check_output([str(binary), '--version'], text=True, timeout=5).strip()
        state = root / 'state'
        state.mkdir(mode=0o700)
        lab = Laboratory(binary, state)
        cases = [
            ('zero', lambda: invalid_case(lab, 'zero', True, 0, 0x94)),
            ('above_maximum', lambda: invalid_case(lab, 'above_maximum', True, 17, 0x94)),
            ('unmapped_1', lambda: invalid_case(lab, 'unmapped_1', False, 1, 0x82)),
            ('unmapped_16', lambda: invalid_case(lab, 'unmapped_16', False, 16, 0x82)),
            ('unmapped_max_packet_7', lambda: invalid_case(lab, 'unmapped_max_packet_7', False, 1, 0x82, 7)),
            ('valid_establish_use_replace', lambda: valid_mapping(lab)),
            ('new_connection_no_mapping', lambda: invalid_case(lab, 'new_connection_no_mapping', False, 1, 0x82)),
            ('mqtt311_control', lambda: legacy_control(lab)),
        ]
        try:
            lab.start()
            for name, exercise in cases:
                case_began = time.monotonic()
                result = dict(scenario=name, status='RUNNING')
                try:
                    exercise()
                    if lab.process.poll() is not None:
                        raise AssertionError('private broker died during alias scenario')
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
            report.update(fixture_error_type=type(failure).__name__, fixture_error='private fixture failed')
        finally:
            try:
                lab.stop()
                report['cleanup'] = 'PASS'
            except Exception as failure:
                report.update(cleanup='FAIL', cleanup_error_type=type(failure).__name__)
    report.update(status='PASS' if report.get('cleanup') == 'PASS' and 'fixture_error_type' not in report
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


if __name__ == '__main__':
    main()
