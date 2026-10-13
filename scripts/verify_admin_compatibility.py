#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P92: exercise released independent admin against this broker, own labs only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--admin', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and a new owned report path required')
    broker = args.broker.resolve(strict=True)
    admin = args.admin.resolve(strict=True)
    version = tomllib.loads((root / 'Cargo.toml').read_text())['package']['version']
    broker_version = subprocess.check_output([str(broker), '--version'], text=True).strip()
    admin_version = subprocess.check_output([str(admin), '--version'], text=True).strip()
    if broker_version != 'mqtt-broker ' + version or admin_version != 'xmqr-admin 0.1.0':
        raise ValueError('wrong broker/admin executable versions')
    # Reuse the accepted A03 fixture without changing the admin repository/pin.
    # Its historical version fields are not evidence; versions above are observed.
    fixture = root.parent / 'xmqr-admin/scripts/integration.py'
    with tempfile.TemporaryDirectory(prefix='xmqr-p92-admin-') as temporary:
        raw = Path(temporary) / 'integration.json'
        subprocess.run([sys.executable, '-B', str(fixture), '--broker', str(broker),
                        '--admin', str(admin), '--report', str(raw)], check=True,
                       stdout=subprocess.DEVNULL)
        result = json.loads(raw.read_text())
    if result.get('status') != 'PASS' or result.get('count') != 18:
        raise AssertionError('independent admin integration not accepted')
    report = dict(status='PASS', scenarios=result['scenarios'], count=result['count'],
                  broker_version=broker_version, admin_version=admin_version,
                  broker_sha256=hashlib.sha256(broker.read_bytes()).hexdigest(),
                  admin_sha256=hashlib.sha256(admin.read_bytes()).hexdigest(),
                  fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  limits=['private Linux loopback labs', 'unchanged admin core Git pin',
                          'no administrative mutation API or production conformance'])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print('ADMIN_COMPATIBILITY_PASS', report['count'])


if __name__ == '__main__':
    main()
