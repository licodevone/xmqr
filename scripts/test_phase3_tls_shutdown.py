#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91 strict TLS EOF regression: client DISCONNECT versus server SIGTERM."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import socket
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
    stalled = None
    began = time.monotonic()
    result = dict(tls_version=version, scenario=kind, repetition=repetition, status='RUNNING')
    try:
        broker.start()
        client = pressure.Client(broker, 'strict-tls-eof', StrictContext(context))
        client.ping()
        result['negotiated_version'] = client.socket.version()
        if kind == 'server_sigterm_partial_handshake':
            stalled = socket.create_connection(('127.0.0.1', broker.port), timeout=5)
            stalled.sendall(b'\x16\x03\x03\x00\x05\x01')  # unfinished TLS record/ClientHello
            pressure.wait_for(lambda: broker.metrics()['xmqr_tcp_accepted_total'] >= 2)
        if kind == 'client_disconnect':
            client.send(0xe0)
        else:
            stopping = time.monotonic()
            broker.shutdown()
            result['broker_exit_code'] = broker.process.returncode
            result['shutdown_seconds'] = round(time.monotonic() - stopping, 3)
            if time.monotonic() - stopping > 15.5:
                raise AssertionError('server shutdown exceeded shared actor/transport deadline')
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
    except Exception as failure:
        result.update(status='FAIL', error_type=type(failure).__name__,
                      error_reason=str(failure) if isinstance(failure, AssertionError)
                      else 'bounded TLS scenario operation failed')
        return result
    finally:
        if client:
            client.close()
        if stalled:
            stalled.close()
        if broker.process and broker.process.poll() is None:
            try:
                broker.shutdown()
            except Exception as failure:
                result.update(status='FAIL', cleanup_error_type=type(failure).__name__)
        result['seconds'] = round(time.monotonic() - began, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', required=True, type=Path)
    parser.add_argument('--admin', required=True, type=Path)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    parser.add_argument('--label', choices=('baseline', 'candidate'), default='baseline')
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and new report required')
    args.broker = args.broker.resolve(strict=True)
    args.admin = args.admin.resolve(strict=True)
    harness_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    fixture_hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                      for name in ('benchmark_pressure.py', 'benchmark_fanout.py', 'benchmark_baseline.py',
                                   'verify_interop.py', 'verify_docker.py')}
    results = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p91-tls-eof-', dir=args.state_root) as temporary:
        root = Path(temporary)
        binary = root / 'mqtt-broker'
        shutil.copyfile(args.broker, binary)
        binary.chmod(0o700)
        admin = root / 'mqtt-admin'
        shutil.copyfile(args.admin, admin)
        admin.chmod(0o700)
        binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
        admin_hash = hashlib.sha256(admin.read_bytes()).hexdigest()
        context = pressure.fanout.security(root, admin)
        for version, protocol in [('TLS1.2', ssl.TLSVersion.TLSv1_2), ('TLS1.3', ssl.TLSVersion.TLSv1_3)]:
            context.minimum_version = context.maximum_version = protocol
            results.append(scenario(root, binary, context, version, 'client_disconnect', 1))
            for repetition in range(1, 4):
                results.append(scenario(root, binary, context, version, 'server_sigterm', repetition))
            results.append(scenario(root, binary, context, version, 'server_sigterm_partial_handshake', 1))
    report = dict(schema_version=1, label=args.label,
                  status='PASS' if all(item['status'] == 'PASS' for item in results) else 'FAIL',
                  broker_binary_sha256=binary_hash, admin_binary_sha256=admin_hash,
                  harness_sha256=harness_hash, fixture_sha256=fixture_hashes,
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
