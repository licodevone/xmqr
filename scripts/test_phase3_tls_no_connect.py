#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91 strict EOF when TLS finishes but no MQTT CONNECT bytes are sent."""
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


def scenario(root, binary, context, version):
    state = root / version
    state.mkdir()
    broker = pressure.Broker(state, binary, root)
    client = None
    result = dict(tls_version=version, scenario='server_sigterm_tls_without_connect', status='RUNNING')
    began = time.monotonic()
    try:
        broker.start()
        transport = socket.create_connection(('127.0.0.1', broker.port), timeout=5)
        try:
            client = context.wrap_socket(transport, server_hostname='127.0.0.1', suppress_ragged_eofs=False)
        except Exception:
            transport.close()
            raise
        # wrap_socket performs the TLS handshake; intentionally send zero MQTT bytes.
        result.update(negotiated_version=client.version(), no_mqtt_sent=True)
        stopping = time.monotonic()
        broker.shutdown()
        result.update(broker_exit_code=broker.process.returncode,
                      shutdown_seconds=round(time.monotonic() - stopping, 3))
        if time.monotonic() - stopping > 15.5:
            raise AssertionError('shutdown exceeded shared actor/transport deadline')
        result['clean_tls_eof'] = client.recv(1) == b''
        if not result['clean_tls_eof']:
            raise AssertionError('unexpected bytes before MQTT CONNECT')
        result['status'] = 'PASS'
    except Exception as failure:
        result.update(status='FAIL', error_type=type(failure).__name__,
                      error_reason=getattr(failure, 'reason', None) or
                      (str(failure) if isinstance(failure, AssertionError) else 'bounded TLS operation failed'))
        if isinstance(failure, ssl.SSLEOFError):
            result['clean_tls_eof'] = False
    finally:
        if client:
            client.close()
        if broker.process and broker.process.poll() is None:
            try:
                broker.shutdown()
            except Exception as failure:
                result.update(status='FAIL', cleanup_error_type=type(failure).__name__)
        result['seconds'] = round(time.monotonic() - began, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--admin', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    parser.add_argument('--label', choices=('baseline', 'candidate'), default='baseline')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and new report required')
    report = dict(schema_version=1, label=args.label,
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scenarios=[])
    with tempfile.TemporaryDirectory(prefix='xmqr-p91-tls-no-connect-', dir=args.state_root) as temporary:
        root = Path(temporary)
        for name, source in [('mqtt-broker', args.broker), ('mqtt-admin', args.admin)]:
            target = root / name
            shutil.copyfile(source.resolve(strict=True), target)
            target.chmod(0o700)
            report[name.replace('mqtt-', '') + '_binary_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        context = pressure.fanout.security(root, root / 'mqtt-admin')
        for version, protocol in [('TLS1.2', ssl.TLSVersion.TLSv1_2), ('TLS1.3', ssl.TLSVersion.TLSv1_3)]:
            context.minimum_version = context.maximum_version = protocol
            report['scenarios'].append(scenario(root, root / 'mqtt-broker', context, version))
    report.update(status='PASS' if all(item['status'] == 'PASS' for item in report['scenarios']) else 'FAIL',
                  completed_utc=datetime.now(timezone.utc).isoformat(),
                  limitations=['owned synthetic mTLS fixture only', 'zero MQTT bytes, not authenticated MQTT session'])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report), flush=True)
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
