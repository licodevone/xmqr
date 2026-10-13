#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91: measured, bounded Linux TCP/mTLS soak and process-crash recovery."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
import benchmark_pressure as pressure

ROOT = Path(__file__).resolve().parents[1]
f = pressure.f


def expect(client, header, identifier):
    received_header, received_body = client.receive()
    if (received_header, received_body) != (header, identifier):
        raise AssertionError(f'ACK mismatch expected_header={header} received_header={received_header} '
                             f'body_size={len(received_body)} matching_identifier={received_body == identifier}')


def payload(sequence):
    value = sequence.to_bytes(8, 'big')
    return value + hashlib.sha256(value).digest() + b'x' * 984


def publish(client, sequence, qos, retained=False, complete=True):
    identifier = ((sequence % 65535) + 1).to_bytes(2, 'big') if qos else b''
    client.send(0x30 | qos << 1 | int(retained), f.text('benchmark/value') + identifier + payload(sequence))
    if qos:
        expect(client, 0x40 if qos == 1 else 0x50, identifier)
        if qos == 2 and complete:
            client.send(0x62, identifier)
            expect(client, 0x70, identifier)
    return identifier


def receive(client, expected, qos, retained=False, acknowledge=True):
    header, body = client.receive()
    size = int.from_bytes(body[:2], 'big')
    offset = 2 + size
    identifier = body[offset:offset + 2] if qos else b''
    if ((header & 0xf7) != (0x30 | qos << 1 | int(retained))
            or body[2:offset] != b'benchmark/value'
            or body[offset + (2 if qos else 0):] != payload(expected)
            or (qos and identifier == b'\0\0')):
        raise AssertionError('logical sequence, bytes, flags or QoS mismatch')
    duplicate = bool(header & 8)
    if qos == 0 and duplicate:
        raise AssertionError('QoS0 delivery must not set DUP')
    if acknowledge and qos == 1:
        client.send(0x40, identifier)
    elif acknowledge and qos == 2:
        client.send(0x50, identifier)
        expect(client, 0x62, identifier)
        client.send(0x70, identifier)
    return identifier, duplicate


class Laboratory:
    def __init__(self, root, binary, security, context):
        self.broker = pressure.Broker(root, binary, security)
        self.context = context
        self.clients = []
        self.restarts = 0
        self.crashes = 0
        self.stage = 'start'
        self.operation = 'start'
        self.health_diagnostic = None

    def client(self, identifier, clean=True):
        self.operation = 'connect_' + identifier
        client = pressure.Client(self.broker, identifier, self.context, clean=clean)
        self.clients.append(client)
        return client

    def disconnect_all(self):
        for client in self.clients:
            pressure.disconnect(client)
        self.clients.clear()

    def restart(self, crash=False):
        # Closing the sockets after kill prevents accidental client DISCONNECT
        # before the durable state boundary being tested.
        if crash:
            self.broker.process.kill()
            self.broker.process.wait(timeout=10)
            self.broker.log.close()
            self.crashes += 1
        else:
            self.broker.shutdown()
            self.restarts += 1
        for client in self.clients:
            client.close()
        self.clients.clear()
        self.broker.start()

    def clear_persistent(self, identifier):
        client = self.client(identifier, clean=True)
        client.ping()
        pressure.disconnect(client)
        self.clients.remove(client)

    def live(self, start, batch):
        self.stage = 'live'
        source = self.client('soak-source')
        subscribers = [self.client(f'soak-fanout-{n}') for n in range(4)]
        messages = deliveries = 0
        for qos in (0, 1, 2):
            self.stage = 'live_qos_' + str(qos)
            for sub in subscribers:
                self.operation = 'subscribe'
                if sub.subscribe([('benchmark/#', qos)]) != (0x90, b'\0\1' + bytes([qos])):
                    raise AssertionError('SUBACK does not match requested QoS')
            for index in range(batch):
                sequence = start + messages
                self.operation = 'publish'
                publish(source, sequence, qos)
                for sub in subscribers:
                    self.operation = 'receive_fanout'
                    receive(sub, sequence, qos)
                    deliveries += 1
                messages += 1
        for client in self.clients:
            self.operation = 'ping_barrier'
            client.ping()  # drains ACKs in order before normal DISCONNECT
        self.disconnect_all()
        return messages, deliveries

    def offline(self, sequence):
        self.stage = 'offline'
        for qos in (1, 2):
            subscriber = self.client('soak-offline', clean=False)
            if subscriber.subscribe([('benchmark/#', qos)]) != (0x90, b'\0\1' + bytes([qos])):
                raise AssertionError('offline subscription rejected')
            subscriber.ping()
            self.disconnect_all()
            source = self.client('soak-offline-source')
            for offset in range(4):
                publish(source, sequence + offset, qos)
            source.ping()
            self.disconnect_all()
            resumed = self.client('soak-offline', clean=False)
            if resumed.connack != (0x20, b'\1\0'):
                raise AssertionError('persistent session not resumed')
            if qos == 1:
                for offset in range(4):
                    receive(resumed, sequence + offset, qos)
            else:
                identifiers = []
                for offset in range(4):
                    identifier, _ = receive(resumed, sequence + offset, qos, acknowledge=False)
                    if identifier in identifiers:
                        raise AssertionError('reused packet identifier in inflight batch')
                    identifiers.append(identifier)
                    resumed.send(0x50, identifier)
                outstanding = set(identifiers)
                for _ in range(4):
                    header, identifier = resumed.receive()
                    if header != 0x62 or identifier not in outstanding:
                        raise AssertionError('offline PUBREL ID does not match outstanding QoS2')
                    outstanding.remove(identifier)
                    resumed.send(0x70, identifier)
            resumed.ping()
            self.disconnect_all()
            self.clear_persistent('soak-offline')
            self.disconnect_all()

    def retained(self, sequence):
        self.stage = 'retained_restart'
        source = self.client('soak-retained-source')
        publish(source, sequence, 1, retained=True)
        source.ping()
        self.disconnect_all()
        self.restart(crash=False)
        replay = self.client('soak-retained-observer')
        replay.subscribe([('benchmark/#', 1)])
        receive(replay, sequence, 1, retained=True)
        replay.ping()
        self.disconnect_all()
        source = self.client('soak-retained-delete')
        source.send(0x33, f.text('benchmark/value') + b'\0\1')
        pressure.fanout.expect(source, 0x40, b'\0\1')
        source.ping()
        self.disconnect_all()

    def inflight(self, sequence):
        self.stage = 'inbound_qos2_pubrec_crash'
        # Broker inbound responsibility persisted at PUBREC, before PUBREL.
        source = self.client('soak-inbound', clean=False)
        identifier = publish(source, sequence, 2, retained=True, complete=False)
        self.restart(crash=True)
        resumed = self.client('soak-inbound', clean=False)
        if resumed.connack != (0x20, b'\1\0'):
            raise AssertionError('inbound QoS2 session lost at process crash')
        resumed.send(0x62, identifier)
        expect(resumed, 0x70, identifier)
        resumed.ping()
        self.disconnect_all()
        replay = self.client('soak-inbound-observer')
        replay.subscribe([('benchmark/#', 2)])
        receive(replay, sequence, 2, retained=True)
        replay.ping()
        self.disconnect_all()
        self.clear_persistent('soak-inbound')
        self.disconnect_all()
        source = self.client('soak-delete')
        source.send(0x33, f.text('benchmark/value') + b'\0\1')
        pressure.fanout.expect(source, 0x40, b'\0\1')
        source.ping()
        self.disconnect_all()

        # Broker outbound responsibility at PUBREL, before receiver PUBCOMP.
        self.stage = 'outbound_qos2_pubrel_crash'
        recipient = self.client('soak-outbound', clean=False)
        recipient.subscribe([('benchmark/#', 2)])
        source = self.client('soak-outbound-source')
        publish(source, sequence + 1, 2)
        delivery_id, _ = receive(recipient, sequence + 1, 2, acknowledge=False)
        recipient.send(0x50, delivery_id)
        expect(recipient, 0x62, delivery_id)
        self.restart(crash=True)
        resumed = self.client('soak-outbound', clean=False)
        if resumed.connack != (0x20, b'\1\0'):
            raise AssertionError('outbound QoS2 session lost at process crash')
        expect(resumed, 0x62, delivery_id)
        resumed.send(0x70, delivery_id)
        resumed.ping()
        self.disconnect_all()
        self.clear_persistent('soak-outbound')
        self.disconnect_all()

        self.stage = 'outbound_qos1_puback_missing_crash'
        recipient = self.client('soak-qos1', clean=False)
        recipient.subscribe([('benchmark/#', 1)])
        source = self.client('soak-qos1-source')
        publish(source, sequence + 2, 1)
        delivery_id, _ = receive(recipient, sequence + 2, 1, acknowledge=False)
        self.restart(crash=True)
        resumed = self.client('soak-qos1', clean=False)
        replay_id, duplicate = receive(resumed, sequence + 2, 1)
        if replay_id != delivery_id or not duplicate:
            raise AssertionError('QoS1 inflight replay requires same ID and DUP after reconnect')
        resumed.ping()
        self.disconnect_all()
        self.clear_persistent('soak-qos1')
        self.disconnect_all()

    def close(self):
        self.disconnect_all()
        self.broker.shutdown()


def scenario(args, binary, security, context, transport, repetition, cancelled, failures):
    samples = []
    counts = dict(live_messages=0, fanout_deliveries=0, offline_batches=0, retained_restarts=0,
                  inbound_outbound_crash_pairs=0, qos1_replay_crashes=0)
    with tempfile.TemporaryDirectory(prefix='xmqr-p91-soak-', dir=args.state_root) as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        lab = Laboratory(root, binary, security if transport == 'mtls' else None,
                         context if transport == 'mtls' else None)
        began = time.monotonic()
        sequence = cycles = 0
        last_recovery = -args.recovery_interval
        last_progress = 0
        first_rss = None
        try:
            lab.broker.start()
            first_rss = pressure.fanout.baseline.process_sample(lab.broker.process.pid)['rss_kib']
            while time.monotonic() - began < args.seconds:
                if cancelled.is_set():
                    raise AssertionError('parallel owned scenario failed; campaign cancelled')
                messages, deliveries = lab.live(sequence, args.batch)
                sequence += messages
                cycles += 1
                counts['live_messages'] += messages
                counts['fanout_deliveries'] += deliveries
                if time.monotonic() - began - last_recovery >= args.recovery_interval:
                    lab.offline(sequence)
                    sequence += 4
                    counts['offline_batches'] += 2
                    lab.retained(sequence)
                    sequence += 1
                    counts['retained_restarts'] += 1
                    lab.inflight(sequence)
                    sequence += 3
                    counts['inbound_outbound_crash_pairs'] += 1
                    counts['qos1_replay_crashes'] += 1
                    last_recovery = time.monotonic() - began
                sample = pressure.fanout.baseline.process_sample(lab.broker.process.pid)
                elapsed = time.monotonic() - began
                metrics = lab.broker.metrics()
                if metrics['xmqr_ready'] != 1 or metrics['xmqr_persistence_errors_total'] != 0:
                    initial = time.monotonic()
                    lab.health_diagnostic = [dict(seconds=0, metrics=metrics)]
                    for _ in range(3):
                        time.sleep(.1)
                        observed = lab.broker.metrics()
                        lab.health_diagnostic.append(dict(seconds=round(time.monotonic() - initial, 3), metrics=observed))
                    raise AssertionError('writer/actor is not healthy after load/recovery')
                if not (metrics['xmqr_connections_active'] <= 5 and metrics['xmqr_sessions'] <= 5
                        and metrics['xmqr_offline_messages'] <= 64 and metrics['xmqr_inflight_messages'] <= 32
                        and metrics['xmqr_retained_messages'] <= 1):
                    raise AssertionError('logical state exceeds declared finite budgets')
                if sample['rss_kib'] > 262144:
                    raise AssertionError('RSS exceeds test safety budget 256MiB')
                disk = sum(path.stat().st_size for path in lab.broker.state.iterdir() if path.is_file())
                if disk > 134217728:
                    raise AssertionError('test durable files exceed safety budget 128MiB')
                if len(samples) < 2000 and (not samples or elapsed - samples[-1]['seconds'] >= 1):
                    samples.append(dict(seconds=round(elapsed, 3), rss_kib=sample['rss_kib'],
                                        disk_bytes=disk, metrics=metrics, process_generation=lab.crashes + lab.restarts))
                if elapsed > args.seconds + 45:
                    raise TimeoutError('bounded total scenario deadline exceeded')
                if elapsed - last_progress >= 60:
                    print(json.dumps(dict(status='RUNNING', transport=transport, repetition=repetition,
                                          seconds=round(elapsed, 3), cycles=cycles, rss_kib=sample['rss_kib'],
                                          crashes=lab.crashes, **counts)), flush=True)
                    last_progress = elapsed
            elapsed = time.monotonic() - began
            final = lab.broker.metrics()
            generations = []
            for generation in sorted(set(item['process_generation'] for item in samples)):
                selected = [item for item in samples if item['process_generation'] == generation]
                generations.append(dict(generation=generation, samples=len(selected),
                                        observed_seconds=round(selected[-1]['seconds'] - selected[0]['seconds'], 3),
                                        rss_first_kib=selected[0]['rss_kib'], rss_last_kib=selected[-1]['rss_kib'],
                                        rss_growth_kib=selected[-1]['rss_kib'] - selected[0]['rss_kib']))
            result = dict(status='PASS', transport=transport, repetition=repetition,
                          requested_seconds=args.seconds, observed_seconds=round(elapsed, 3), cycles=cycles,
                          **counts, crashes=lab.crashes, graceful_restarts=lab.restarts,
                          rss_initial_kib=first_rss, rss_final_kib=sample['rss_kib'],
                          rss_growth_final_kib=sample['rss_kib'] - first_rss,
                          rss_peak_sampled_kib=max(item['rss_kib'] for item in samples),
                          metrics_final=final, memory_process_generations=generations, samples=samples)
            print(json.dumps({k: v for k, v in result.items() if k != 'samples'}), flush=True)
            return result
        except Exception as failure:
            if not cancelled.is_set():
                diagnostic = dict(transport=transport, repetition=repetition, stage=lab.stage,
                                  operation=lab.operation, next_sequence=sequence,
                                  error_type=type(failure).__name__,
                                  error=str(failure) if isinstance(failure, (AssertionError, TimeoutError))
                                  else 'bounded test operation failed')
                log = (root / 'broker.log').read_bytes().lower() if (root / 'broker.log').exists() else b''
                diagnostic.update(broker_exit_code=lab.broker.process.poll() if lab.broker.process else None,
                                  filesystem_free_bytes=shutil.disk_usage(args.state_root).free,
                                  enospc_marker=b'no space left on device' in log or b'os error 28' in log,
                                  eio_marker=b'input/output error' in log or b'os error 5' in log,
                                  persistence_marker=b'persistence' in log or b'durable' in log,
                                  panic_marker=b'panicked' in log)
                if lab.health_diagnostic:
                    diagnostic['health_probes'] = lab.health_diagnostic
                try:
                    failures.put_nowait(diagnostic)
                except queue.Full:
                    pass
            cancelled.set()
            raise
        finally:
            lab.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--admin', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--batch', type=int, default=8)
    parser.add_argument('--recovery-interval', type=int, default=120)
    parser.add_argument('--state-root', type=Path, default=Path('/var/tmp'))
    parser.add_argument('--label', choices=['baseline', 'candidate'], required=True)
    args = parser.parse_args()
    if sys.platform != 'linux' or not (5 <= args.seconds <= 3600 and 1 <= args.repetitions <= 5
                                      and 1 <= args.batch <= 32 and 1 <= args.recovery_interval <= 300):
        parser.error('Linux and bounded parameters required')
    if args.report.exists() or args.report.is_symlink():
        parser.error('report exists; choose another output')
    if args.label == 'candidate' and (args.seconds < 600 or args.repetitions < 3):
        parser.error('candidate acceptance requires three repetitions >=600s')
    args.broker = args.broker.resolve(strict=True)
    args.admin = args.admin.resolve(strict=True)
    args.state_root = args.state_root.resolve(strict=True)
    filesystem = subprocess.check_output(['stat', '-f', '-c', '%T', str(args.state_root)], text=True).strip()
    if (not args.state_root.is_dir() or not os.access(args.state_root, os.W_OK)
            or filesystem not in ('ext2/ext3', 'ext4', 'xfs', 'btrfs', 'zfs')
            or shutil.disk_usage(args.state_root).free < 536870912):
        parser.error('native disk-backed Linux filesystem and >=512MiB free required; no tmpfs/DrvFS')
    report = dict(schema_version=1, label=args.label, status='RUNNING', scenarios=[],
                  kernel=platform.release(), machine=platform.machine(), python=platform.python_version(),
                  source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  broker_binary_sha256=hashlib.sha256(args.broker.read_bytes()).hexdigest(),
                  admin_binary_sha256=hashlib.sha256(args.admin.read_bytes()).hexdigest(),
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  dependency_sha256={name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                                     for name in ('benchmark_pressure.py', 'benchmark_fanout.py',
                                                  'benchmark_baseline.py', 'verify_interop.py')},
                  parameters=dict(repetitions=args.repetitions, requested_seconds=args.seconds,
                                  recovery_interval_seconds=args.recovery_interval,
                                  fanout=4, batch_per_qos=args.batch, payload_bytes=1024,
                                  rss_limit_kib=262144, durable_file_limit_bytes=134217728),
                  filesystem=filesystem, filesystem_free_bytes_start=shutil.disk_usage(args.state_root).free,
                  limitations=['not a production SLA or throughput maximum', 'process crash is not power-loss',
                               '30min wall/60 process-minutes minimum; not days of stability',
                               'no new physical ESP32, native Windows, arm64 or exact MSRV acceptance'])
    began = time.monotonic()
    error = None
    try:
        with tempfile.TemporaryDirectory(prefix='xmqr-p91-fixtures-', dir=args.state_root) as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            binary = root / 'mqtt-broker'
            shutil.copyfile(args.broker, binary)
            binary.chmod(0o700)  # immutable test-owned copy across restarts
            context = pressure.fanout.security(root, args.admin)
            for repetition in range(1, args.repetitions + 1):
                cancelled = threading.Event()
                failures = queue.Queue(maxsize=1)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(scenario, args, binary, root, context, transport, repetition, cancelled, failures)
                               for transport in ('tcp', 'mtls')]
                    for future in as_completed(futures):
                        report['scenarios'].append(future.result())
        report['status'] = 'PASS'
    except Exception as failure:
        report['status'] = 'FAIL'
        report['error_type'] = type(failure).__name__
        # Exception messages created here are fixed invariants, never tool output.
        report['error'] = str(failure) if isinstance(failure, (AssertionError, TimeoutError)) else 'test harness operation failed'
        if 'failures' in locals() and not failures.empty():
            report['primary_failure'] = failures.get_nowait()
        error = failure
    finally:
        report['observed_wall_seconds'] = round(time.monotonic() - began, 3)
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print('PHASE3_SOAK_' + report['status'], flush=True)
    if error:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
