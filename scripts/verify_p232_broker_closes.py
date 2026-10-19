#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe mandatory close separately from optional/recommended diagnostics."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from verify_phase6_vbi import Laboratory, binary_digest, frame, packet, text


def observe_close(stream):
    first = stream.recv(1)
    response = packet(stream, first[0]) if first else None
    if first and stream.recv(1) != b'':
        raise AssertionError('connection did not close after its response')
    return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and exclusive new report required')
    filesystem = subprocess.check_output(['stat', '-f', '-c', '%T', str(args.state_root)], text=True).strip()
    if filesystem not in ('ext2/ext3', 'ext4', 'xfs', 'btrfs', 'zfs'):
        parser.error('native Linux disk-backed state required')
    binary = args.broker.resolve(strict=True)
    before = binary_digest(binary)
    report = {'schema_version': 1, 'audit': 'P232', 'scenarios': [], 'filesystem': filesystem,
              'broker_sha256': before, 'harness_sha256': binary_digest(Path(__file__)),
              'helper_sha256': binary_digest(Path(__file__).with_name('verify_phase6_vbi.py')),
              'limitations': ['loopback open-lab only',
                              'PASS means observed mandatory close, not entire-clause conformance',
                              'diagnostic interpretation remains separate from factual absence']}
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='xmqr-p232-closes-', dir=args.state_root) as folder:
        state = Path(folder) / 'state'
        state.mkdir(mode=0o700)
        lab = Laboratory(binary, state)
        try:
            lab.start()
            for name, wire in [
                ('zero_subscription_identifier', frame(0x82, b'\0\x01\x02\x0b\0' + text(b'p232/#') + b'\0')),
                ('empty_topic_without_alias', frame(0x30, text(b'') + b'\0synthetic')),
            ]:
                peer = lab.connect(name.encode())
                peer.sendall(wire)
                response = observe_close(peer)
                report['scenarios'].append({'name': name, 'mandatory_close': 'PASS',
                                            'diagnostic_header': response[0] if response else None,
                                            'diagnostic_body_hex': response[1].hex() if response else None})
            previous = lab.connect(b'p232-takeover')
            current = lab.connect(b'p232-takeover')
            response = observe_close(previous)
            current.sendall(b'\xc0\0')
            if packet(current) != (0xd0, b''):
                raise AssertionError('new takeover connection failed canonical ping control')
            report['scenarios'].append({'name': 'takeover_previous_connection', 'mandatory_close': 'PASS',
                                        'diagnostic_header': response[0] if response else None,
                                        'diagnostic_body_hex': response[1].hex() if response else None,
                                        'new_connection_ping': 'PASS'})
            current.sendall(b'\xe0\0')
        finally:
            lab.stop()
            report['cleanup'] = 'PASS'
    report['binary_unchanged'] = before == binary_digest(binary)
    report['elapsed_seconds'] = round(time.monotonic() - began, 3)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'mandatory_close': '3/3PASS', 'cleanup': report['cleanup'],
                      'diagnostics_observed': sum(row['diagnostic_header'] is not None for row in report['scenarios'])}))


if __name__ == '__main__':
    main()
