#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91 strict TLS EOF regression: client DISCONNECT versus server SIGTERM."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import ssl
import sys
import tempfile
import time

sys.dont_write_bytecode = True
import benchmark_pressure as pressure


class StrictContext:
    def __init__(self, context):
        self.context = context

    def wrap_socket(self, *args, **kwargs):
        return self.context.wrap_socket(*args, suppress_ragged_eofs=False, **kwargs)


def scenario(root, binary, context, version, kind, repetition):
    case = root / f'{version}-{kind}-{repetition}'
    case.mkdir()
    broker = pressure.Broker(case, binary, root)
    client = None
    began = time.monotonic()
    result = dict(tls_version=version, scenario=kind, repetition=repetition, status='RUNNING')
    try:
        broker.start()
        client = pressure.Client(broker, 'strict-tls-eof', StrictContext(context))
        client.ping()
        result['negotiated_version'] = client.socket.version()
        if kind == 'client_disconnect':
            client.send(0xe0)
        else:
            broker.shutdown()
            result['broker_exit_code'] = broker.process.returncode
        try:
            received = client.socket.recv(1)
            result['clean_tls_eof'] = received == b''
            if received != b'':
                raise AssertionError('unexpected MQTT bytes at TLS shutdown boundary')
            result['status'] = 'PASS'
        except ssl.SSLEOFError as failure:
            result.update(status='FAIL', clean_tls_eof=False, error_type=type(failure).__name__,
                          error_reason=getattr(failure, 'reason', 'unexpected TLS EOF'))
        return result
    finally:
        if client:
            client.close()
        if broker.process and broker.process.poll() is None:
            broker.shutdown()
        result['seconds'] = round(time.monotonic() - began, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', required=True, type=Path)
    parser.add_argument('--admin', required=True, type=Path)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and new report required')
    args.broker = args.broker.resolve(strict=True)
    args.admin = args.admin.resolve(strict=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p91-tls-eof-', dir=args.state_root) as temporary:
        root = Path(temporary)
        binary = root / 'mqtt-broker'
        shutil.copyfile(args.broker, binary)
        binary.chmod(0o700)
        context = pressure.fanout.security(root, args.admin)
        for version, protocol in [('TLS1.2', ssl.TLSVersion.TLSv1_2), ('TLS1.3', ssl.TLSVersion.TLSv1_3)]:
            context.minimum_version = context.maximum_version = protocol
            results.append(scenario(root, binary, context, version, 'client_disconnect', 1))
            for repetition in range(1, 4):
                results.append(scenario(root, binary, context, version, 'server_sigterm', repetition))
    report = dict(schema_version=1, status='PASS' if all(item['status'] == 'PASS' for item in results) else 'FAIL',
                  broker_binary_sha256=hashlib.sha256(args.broker.read_bytes()).hexdigest(),
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  completed_utc=datetime.now(timezone.utc).isoformat(), scenarios=results,
                  limitations=['owned synthetic mTLS fixture only', 'process shutdown, not physical power-loss'])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report), flush=True)
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
