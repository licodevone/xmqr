#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91 diagnostic: queued QoS1 ACKs plus bounded readiness after quiescence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

sys.dont_write_bytecode = True
import benchmark_pressure as pressure


def wait_healthy(broker, seconds=15, interval=.05):
    deadline = time.monotonic() + seconds
    began = time.monotonic()
    probes = []
    while time.monotonic() < deadline:
        values = broker.metrics()
        elapsed = time.monotonic() - began
        probes.append(dict(seconds=round(elapsed, 3), metrics=values))
        if values['xmqr_persistence_errors_total'] != 0:
            raise AssertionError('persistence errors are never accepted as transient readiness')
        if values['xmqr_ready'] == 1 and time.monotonic() <= deadline:
            return values, probes
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise TimeoutError('actor/writer did not recover within explicit health deadline')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and new report required')
    binary = args.broker.resolve(strict=True)
    report = dict(schema_version=1, label='diagnostic', status='RUNNING', observations=[],
                  broker_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    began = time.monotonic()
    clients = []
    try:
        with tempfile.TemporaryDirectory(prefix='xmqr-p91-health-', dir=args.state_root) as temporary:
            broker = pressure.Broker(temporary, binary, None)
            try:
                broker.start()
                for repetition in range(3):
                    for number in range(64):
                        clients.append(pressure.Client(broker, f'health-{number}'))
                    before = broker.metrics()['xmqr_messages_received_total{qos="1"}']
                    for number, client in enumerate(clients):
                        value = (repetition * 64 + number).to_bytes(8, 'big') + b'x' * 1016
                        client.send(0x33, pressure.f.text('benchmark/value') + b'\0\1' + value)
                    busy = broker.metrics()
                    for client in clients:
                        pressure.fanout.expect(client, 0x40, b'\0\1')
                        client.ping()
                    for client in clients:
                        pressure.disconnect(client)
                    clients.clear()
                    healthy, probes = wait_healthy(broker)
                    if (healthy['xmqr_messages_received_total{qos="1"}'] - before != 64
                            or healthy['xmqr_retained_messages'] != 1):
                        raise AssertionError('acknowledged publication accounting is not conserved')
                    report['observations'].append(dict(repetition=repetition + 1, publications=64,
                                                       acked=64, busy=busy, recovery_probes=probes,
                                                       process_alive=broker.process.poll() is None,
                                                       status='PASS'))
            finally:
                for client in clients:
                    pressure.disconnect(client)
                broker.shutdown()
        report['status'] = 'PASS'
    except Exception as failure:
        report['status'] = 'FAIL'
        report['error_type'] = type(failure).__name__
        report['error'] = str(failure) if isinstance(failure, (AssertionError, TimeoutError)) else 'bounded diagnostic operation failed'
    report['observed_seconds'] = round(time.monotonic() - began, 3)
    report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print('PHASE3_HEALTH_' + report['status'], flush=True)
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
