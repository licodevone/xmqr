#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P80: isolated Linux admission/slow-peer campaigns; not a production SLA."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

sys.dont_write_bytecode = True
import benchmark_fanout as fanout

f = fanout.f
ROOT = Path(__file__).resolve().parents[1]


def unused_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def wait_for(predicate, seconds=15):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(.03)
    raise TimeoutError('test-owned scenario deadline')


class Broker(fanout.Broker):
    def __init__(self, root, binary, security_root, connections=64, inflight=32, offline=64):
        super().__init__(root, binary, security_root)
        self.monitor = unused_port()
        self.limits = connections, inflight, offline

    def start(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('MQTT_')}
        env.update(MQTT_MODE='open-lab', MQTT_BIND=f'127.0.0.1:{self.port}',
                   MQTT_STATE_DIR=str(self.state), RUST_LOG='error',
                   MQTT_MAX_CONNECTIONS=str(self.limits[0]),
                   MQTT_MAX_INFLIGHT=str(self.limits[1]), MQTT_MAX_OFFLINE=str(self.limits[2]),
                   MQTT_MONITOR_ENABLED='true', MQTT_MONITOR_BIND=f'127.0.0.1:{self.monitor}')
        if self.security_root:
            root = self.security_root
            env.update(MQTT_MODE='secure-mtls', MQTT_SERVER_CERT=str(root/'server.crt'),
                       MQTT_SERVER_KEY=str(root/'server.key'), MQTT_CLIENT_CA=str(root/'ca.crt'),
                       MQTT_SECURITY_BUNDLE=str(root/'security.toml'))
        self.log = (self.root/'broker.log').open('wb')
        self.process = subprocess.Popen([str(self.binary)], env=env,
                                        stdout=subprocess.DEVNULL, stderr=self.log)
        def ready():
            if self.process.poll() is not None:
                raise AssertionError('test broker exited before readiness')
            try:
                return self.metrics().get('xmqr_ready') == 1
            except (OSError, ValueError):
                return False
        wait_for(ready)

    def metrics(self):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.monitor}/metrics', timeout=2) as response:
            return dict((line.split()[0], float(line.split()[1])) for line in
                        response.read(16385).decode().splitlines() if line and not line.startswith('#'))


class Client(f.WireClient):
    def __init__(self, broker, identifier, context=None, clean=True, small_buffer=False):
        self.socket = socket.socket()
        self.socket.settimeout(5)
        if small_buffer:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
        try:
            self.socket.connect(('127.0.0.1', broker.port))
            if context:
                self.socket = context.wrap_socket(self.socket, server_hostname='127.0.0.1')
            flags = (2 if clean else 0) | (0xc0 if context else 0)
            body = f.text('MQTT') + bytes([4, flags, 0, 60]) + f.text(identifier)
            if context:
                body += f.text('p72-device') + len(fanout.PASSWORD).to_bytes(2, 'big') + fanout.PASSWORD
            self.send(0x10, body)
            self.connack = self.receive()
            if self.connack not in ((0x20, b'\0\0'), (0x20, b'\1\0')):
                raise AssertionError('test CONNECT refused')
        except BaseException:
            self.close()
            raise


def disconnect(client):
    try:
        client.send(0xe0)
    except OSError:
        pass
    client.close()


def latency(values):
    return {name: fanout.baseline.percentile(values, fraction)
            for name, fraction in [('p50', .5), ('p95', .95), ('p99', .99)]}


def publish(client, qos, sequence, topic='benchmark/value', size=256):
    identifier = (sequence + 1).to_bytes(2, 'big') if qos else b''
    client.send(0x30 | qos << 1, f.text(topic) + identifier + sequence.to_bytes(8, 'big') + b'x'*(size-8))
    if qos:
        fanout.expect(client, 0x40 if qos == 1 else 0x50, identifier)
        if qos == 2:
            client.send(0x62, identifier)
            fanout.expect(client, 0x70, identifier)


def receive_publish(client, qos, sequence, topic='benchmark/value', size=256):
    header, body = client.receive()
    offset = 2 + int.from_bytes(body[:2], 'big')
    identifier = body[offset:offset+2] if qos else b''
    if (header & 0xf7 != 0x30 | qos << 1 or body[2:offset] != topic.encode()
            or body[offset+(2 if qos else 0):] != sequence.to_bytes(8, 'big') + b'x'*(size-8)):
        raise AssertionError('delivery flags/topic/sequence/payload mismatch')
    if qos and identifier == b'\0\0':
        raise AssertionError('zero packet identifier')
    return identifier, bool(header & 8)


def admission(args, security_root, context, n):
    clients = []
    client_lock = threading.Lock()
    with tempfile.TemporaryDirectory(prefix='xmqr-p80-admission-', dir=args.state_root) as temporary:
        broker = Broker(temporary, args.broker, security_root, connections=n)
        try:
            broker.start()
            def connect(index):
                started = time.perf_counter()
                errors = 0
                until = time.monotonic() + 45
                while True:
                    try:
                        client = Client(broker, f'burst-{index}', context)
                        item = client, (time.perf_counter()-started)*1000, errors
                        with client_lock:
                            clients.append(item)
                        return item
                    except (OSError, EOFError, AssertionError):
                        errors += 1
                        if time.monotonic() > until:
                            raise TimeoutError('bounded connection retry deadline')
                        time.sleep(.05 + index % 7 * .017)
            with fanout.baseline.Sampler(broker.process.pid) as sampler:
                with ThreadPoolExecutor(max_workers=n) as pool:
                    list(pool.map(connect, range(n)))
                for client, _, _ in clients:
                    client.ping()
                before = broker.metrics()
                with socket.create_connection(('127.0.0.1', broker.port), timeout=5) as extra:
                    try:
                        if extra.recv(1) != b'':
                            raise AssertionError('N+1 connection accepted')
                    except ConnectionResetError:
                        pass
                wait_for(lambda: broker.metrics().get('xmqr_rejections_total{reason="admission"}', 0)
                         > before.get('xmqr_rejections_total{reason="admission"}', 0))
                disconnect(clients[0][0])
                wait_for(lambda: broker.metrics()['xmqr_connections_active'] == n-1)
                with Client(broker, 'replacement', context) as replacement:
                    replacement.ping()
                    replacement.send(0xe0)
                time.sleep(.5)
            return dict(scenario='simultaneous_admission', limit=n, admitted=n,
                        refusal_attempts=sum(item[2] for item in clients), n_plus_one_refused=True,
                        released_slot_reused=True, connection_ms=latency([item[1] for item in clients]),
                        metrics=broker.metrics(), **sampler.result())
        finally:
            for client, _, _ in clients:
                disconnect(client)
            broker.shutdown()


def initial_timeout(args, security_root, context):
    with tempfile.TemporaryDirectory(prefix='xmqr-p80-handshake-', dir=args.state_root) as temporary:
        broker = Broker(temporary, args.broker, security_root, connections=1)
        try:
            broker.start()
            started = time.perf_counter()
            with socket.create_connection(('127.0.0.1', broker.port), timeout=5) as silent:
                try:
                    assert silent.recv(1) == b''
                except ConnectionResetError:
                    pass
            elapsed = time.perf_counter()-started
            with Client(broker, 'after-silent', context) as replacement:
                replacement.ping()
                replacement.send(0xe0)
            return dict(scenario='silent_initial_bytes', closure_seconds=elapsed, released_slot_reused=True,
                        metrics=broker.metrics())
        finally:
            broker.shutdown()


def drain(client, qos, count):
    sequences = []
    pending = set()
    while len(sequences) < count or pending:
        header, body = client.receive()
        if header == 0x62 and qos == 2:
            if body not in pending:
                raise AssertionError('unexpected PUBREL identifier')
            client.send(0x70, body)
            pending.remove(body)
            continue
        offset = 2 + int.from_bytes(body[:2], 'big')
        identifier = body[offset:offset+2]
        sequence = int.from_bytes(body[offset+2:offset+10], 'big')
        if header & 0xf7 != 0x30 | qos << 1 or body[2:offset] != b'benchmark/value':
            raise AssertionError('wrong drain publication')
        if sequence != len(sequences) or body[offset+2:] != sequence.to_bytes(8, 'big') + b'x'*248:
            raise AssertionError('drain ordering/payload mismatch')
        if identifier == b'\0\0' or identifier in pending:
            raise AssertionError('drain identifier mismatch')
        sequences.append(sequence)
        client.send(0x40 if qos == 1 else 0x50, identifier)
        if qos == 2:
            pending.add(identifier)
    client.ping()
    return len(sequences)


def pressure(args, security_root, context, qos, inflight, offline):
    clients = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p80-pressure-', dir=args.state_root) as temporary:
        broker = Broker(temporary, args.broker, security_root, inflight=inflight, offline=offline)
        try:
            broker.start()
            slow = Client(broker, 'slow', context, clean=False)
            fast = Client(broker, 'fast', context)
            publisher = Client(broker, 'pressure-source', context, clean=False)
            clients += [slow, fast, publisher]
            assert slow.subscribe([('benchmark/value', qos)]) == (0x90, b'\0\1'+bytes([qos]))
            assert fast.subscribe([('benchmark/healthy', 1)]) == (0x90, b'\0\1\1')
            count = inflight + offline
            with fanout.baseline.Sampler(broker.process.pid) as sampler:
                elapsed = []
                for sequence in range(count):
                    started = time.perf_counter()
                    publish(publisher, qos, sequence)
                    elapsed.append((time.perf_counter()-started)*1000)
                at_limit = broker.metrics()
                assert at_limit['xmqr_offline_messages'] == offline
                assert at_limit['xmqr_inflight_messages'] == inflight
                identifier = (count+1).to_bytes(2, 'big')
                publisher.send(0x30 | qos << 1, f.text('benchmark/value') + identifier
                               + count.to_bytes(8, 'big') + b'x'*248)
                if qos == 2:
                    # PUBREC accepts durable ownership, not completed fan-out.
                    fanout.expect(publisher, 0x50, identifier)
                    publisher.send(0x62, identifier)
                try:
                    publisher.receive()
                except (EOFError, ConnectionResetError):
                    pass
                else:
                    raise AssertionError('quota refusal emitted terminal ACK')
                with Client(broker, 'healthy-source', context) as healthy:
                    publish(healthy, 1, 0, topic='benchmark/healthy')
                    identifier_fast, _ = receive_publish(fast, 1, 0, topic='benchmark/healthy')
                    fast.send(0x40, identifier_fast)
                    fast.ping()
                    healthy.send(0xe0)
                # Restart while slow subscriber withheld all ACKs.
                for client in clients:
                    client.close()
                clients.clear()
            broker.shutdown()
            broker.start()
            resumed = Client(broker, 'slow', context, clean=False)
            clients.append(resumed)
            assert resumed.connack == (0x20, b'\1\0')
            drained = drain(resumed, qos, count)
            if qos == 2:
                recovered = Client(broker, 'pressure-source', context, clean=False)
                clients.append(recovered)
                assert recovered.connack == (0x20, b'\1\0')
                recovered.send(0x62, (count+1).to_bytes(2, 'big'))
                fanout.expect(recovered, 0x70, (count+1).to_bytes(2, 'big'))
                extra, _ = receive_publish(resumed, 2, count)
                resumed.send(0x50, extra)
                fanout.expect(resumed, 0x62, extra)
                resumed.send(0x70, extra)
                resumed.ping()
            wait_for(lambda: broker.metrics()['xmqr_offline_messages'] == 0
                     and broker.metrics()['xmqr_inflight_messages'] == 0)
            return dict(scenario='withheld_ack_restart_drain', qos=qos, inflight=inflight,
                        offline=offline, accepted_before_refusal=count, drained_after_restart=drained,
                        terminal_ack_refused=True, independent_peer_progress=True,
                        qos2_ownership_completed_after_restart=qos == 2, publish_terminal_ack_ms=latency(elapsed),
                        metrics_at_limit=at_limit, metrics_after_drain=broker.metrics(), **sampler.result())
        finally:
            for client in clients:
                disconnect(client)
            broker.shutdown()


def nonreader_batch(sent, now, until):
    """Packet budget exhaustion pauses sending; only wall deadline fails."""
    if now >= until:
        raise TimeoutError('nonreader was not closed within bounded campaign')
    if not 0 <= sent <= 5000:
        raise AssertionError('nonreader packet budget exceeded')
    return min(32, 5000 - sent)


def nonreader(args, security_root, context):
    clients = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p80-nonreader-', dir=args.state_root) as temporary:
        broker = Broker(temporary, args.broker, security_root, connections=3)
        try:
            broker.start()
            slow = Client(broker, 'nonreader', context, small_buffer=True)
            publisher = Client(broker, 'qos0-source', context)
            healthy = Client(broker, 'qos1-source', context)
            clients += [slow, publisher, healthy]
            assert slow.subscribe([('benchmark/value', 0)]) == (0x90, b'\0\1\0')
            sent = 0
            waited_at_budget = False
            peer_latency = []
            until = time.monotonic()+60
            with fanout.baseline.Sampler(broker.process.pid) as sampler:
                while broker.metrics()['xmqr_connections_active'] == 3:
                    try:
                        batch = nonreader_batch(sent, time.monotonic(), until)
                    except (AssertionError, TimeoutError):
                        print(json.dumps(dict(status='FAIL', scenario='socket_nonreader_qos0',
                                              attempted_messages=sent, metrics=broker.metrics())), flush=True)
                        raise
                    if batch == 0:
                        waited_at_budget = True
                        time.sleep(.02)
                        continue
                    for _ in range(batch):
                        publish(publisher, 0, sent, size=4096)
                        sent += 1
                    publisher.ping()
                    started = time.perf_counter()
                    publish(healthy, 1, sent, topic='benchmark/healthy')
                    peer_latency.append((time.perf_counter()-started)*1000)
                with Client(broker, 'after-nonreader', context) as replacement:
                    replacement.ping()
                    replacement.send(0xe0)
            return dict(scenario='socket_nonreader_qos0', attempted_messages=sent,
                        waited_at_packet_budget=waited_at_budget,
                        payload_bytes=4096, effective_receive_buffer=slow.socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
                        slow_peer_closed=True, released_slot_reused=True, independent_puback_ms=latency(peer_latency),
                        metrics=broker.metrics(), **sampler.result())
        finally:
            for client in clients:
                disconnect(client)
            broker.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--admin', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--limits', nargs='+', type=int, default=[1, 8, 32, 64])
    parser.add_argument('--only', choices=['all', 'nonreader'], default='all')
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 10 or not args.limits or any(n < 1 or n > 64 for n in args.limits) or len(set(args.limits)) != len(args.limits):
        parser.error('invalid bounded campaign arguments')
    if args.report.exists() or args.report.is_symlink():
        parser.error('report exists; choose a new filename')
    if sys.platform != 'linux' or not args.state_root.is_dir():
        parser.error('Linux and an existing native state-root required')
    for name in ('broker', 'admin'):
        path = getattr(args, name).resolve(strict=True)
        if not os.access(path, os.X_OK):
            parser.error('executable required')
        setattr(args, name, path)
    hashes = {name: hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() for name in ('broker', 'admin')}
    results = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p80-security-', dir=args.state_root) as temporary:
        root = Path(temporary)
        context = fanout.security(root, args.admin)
        policy = root/'security.toml'
        policy.write_text(policy.read_text().replace("publish=['benchmark/value']", "publish=['benchmark/value','benchmark/healthy']")
                          .replace("subscribe=['benchmark/#']", "subscribe=['benchmark/#','benchmark/value','benchmark/healthy']"))
        for repetition in range(1, args.repetitions+1):
            for transport in ('open-lab', 'mtls'):
                selected_root = root if transport == 'mtls' else None
                selected = context if transport == 'mtls' else None
                cases = [(admission, (n,)) for n in args.limits]
                cases += [(initial_timeout, ())]
                cases += [(pressure, (qos, inflight, offline)) for qos in (1, 2) for inflight, offline in ((4, 8), (32, 64))]
                cases += [(nonreader, ())]
                if args.only == 'nonreader':
                    cases = [(nonreader, ())]
                for function, tail in cases:
                    result = function(args, selected_root, selected, *tail)
                    result.update(transport=transport, repetition=repetition, status='PASS')
                    results.append(result)
                    print(json.dumps(result), flush=True)
    assert hashes == {name: hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() for name in hashes}
    report = dict(schema_version=1, completed_utc=datetime.now(timezone.utc).isoformat(),
                  source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  broker_version=subprocess.check_output([str(args.broker), '--version'], text=True).strip(),
                  binary_sha256=hashes, harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  dependency_sha256={name: hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in ('benchmark_fanout.py', 'benchmark_baseline.py', 'verify_interop.py')},
                  environment=dict(kernel=platform.release(), python=platform.python_version(),
                                   cpu=next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
                                   logical_cpus=len(os.sched_getaffinity(0)),
                                   state_filesystem=subprocess.check_output(['stat', '-f', '-c', '%T', str(args.state_root)], text=True).strip()),
                  parameters=dict(repetitions=args.repetitions, connection_limits=args.limits, selection=args.only), results=results,
                  limitations=['Bounded campaign, not maximum throughput or production SLA', 'Monitoring enabled, CPU ticks coarse,100%=one core',
                               'Admission latencies include finite retries; mTLS hash boundary may refuse bursts', 'WSL and concurrent workloads affect results',
                               'Process restart is not proof of power loss', 'Physical ESP32 NOT_RUN'])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print('PRESSURE_COMPLETE', args.report)


if __name__ == '__main__':
    main()
