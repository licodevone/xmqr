#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P62: isolated Linux open-lab RSS/CPU and sequential durable PUBACK baseline."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fixtures', ROOT / 'scripts/verify_interop.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def process_sample(pid):
    # Fields after the final ')' start at field3(state); utime/stime are14/15.
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    status = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
    return {'cpu_ticks': int(fields[11]) + int(fields[12]),
            'rss_kib': int(status['VmRSS'].split()[0]),
            'hwm_kib': int(status['VmHWM'].split()[0])}


class Sampler:
    def __init__(self, pid):
        self.pid = pid
        self.stop = threading.Event()
        self.samples = []
        self.error = None

    def collect(self):
        try:
            while not self.stop.wait(.02):
                self.samples.append(process_sample(self.pid))
        except Exception as error:
            self.error = error

    def __enter__(self):
        self.first = process_sample(self.pid)
        self.samples.append(self.first)
        self.start = time.perf_counter()
        self.thread = threading.Thread(target=self.collect, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=2)
        self.last = process_sample(self.pid)
        self.elapsed = time.perf_counter() - self.start
        self.samples.append(self.last)
        if self.error:
            raise self.error

    def result(self):
        ticks = self.last['cpu_ticks'] - self.first['cpu_ticks']
        return {'measurement_seconds': self.elapsed,
                'cpu_seconds': ticks / os.sysconf('SC_CLK_TCK'),
                'cpu_percent_one_core': 100 * ticks / os.sysconf('SC_CLK_TCK') / self.elapsed,
                'rss_median_kib': statistics.median(s['rss_kib'] for s in self.samples),
                'rss_peak_sampled_kib': max(s['rss_kib'] for s in self.samples),
                'process_lifetime_hwm_kib': self.last['hwm_kib'],
                'sample_count': len(self.samples)}


def percentile(values, fraction):
    # Nearest-rank: report definition, not interpolated percentiles.
    import math
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def scenario(args, repetition, connections=None):
    clients = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p62-', dir=args.state_root) as temporary:
        broker = fixtures.Broker(temporary)
        try:
            broker.start()
            if connections is not None:
                for index in range(connections):
                    client = fixtures.WireClient(broker, f'idle-{index}')
                    clients.append(client)
                time.sleep(.5)  # settle after CONNECT/CONNACK and durable setup
                with Sampler(broker.process.pid) as sampler:
                    time.sleep(args.idle_seconds)
                result = {'scenario': 'idle', 'connections': connections}
            else:
                client = fixtures.WireClient(broker, 'publisher')
                clients.append(client)
                payload = b'x' * args.payload_bytes
                topic = fixtures.text('benchmark/value')

                def publish(index):
                    identifier = ((index % 65535) + 1).to_bytes(2, 'big')
                    start = time.perf_counter_ns()
                    # Retained state changes for each sequence, not only empty
                    # routing state. Header0x33 is QoS1 with RETAIN set.
                    content = index.to_bytes(8, 'big') + payload[8:]
                    client.send(0x33, topic + identifier + content)
                    if client.receive() != (0x40, identifier):
                        raise AssertionError('unexpected PUBACK header or packet identifier')
                    return (time.perf_counter_ns() - start) / 1_000_000

                for index in range(args.warmup):
                    publish(index)
                latency = []
                with Sampler(broker.process.pid) as sampler:
                    for index in range(args.messages):
                        latency.append(publish(index + args.warmup))
                result = {'scenario': 'sequential_qos1_puback', 'connections': 1,
                          'messages': len(latency), 'payload_bytes': args.payload_bytes,
                          'warmup_messages': args.warmup,
                          'messages_per_second': len(latency) / sampler.elapsed,
                          'latency_ms': {'mean': statistics.mean(latency),
                                         'p50': percentile(latency, .5),
                                         'p95': percentile(latency, .95),
                                         'p99': percentile(latency, .99)}}
            result.update(repetition=repetition, **sampler.result())
            return result
        finally:
            for client in clients:
                try:
                    client.send(0xe0)
                except OSError:
                    pass
                client.close()
            if broker.process is not None:
                if broker.process.poll() is None:
                    broker.process.terminate()
                try:
                    code = broker.process.wait(timeout=20)
                    if code != 0:
                        raise AssertionError(f'broker did not stop cleanly: {code}')
                except subprocess.TimeoutExpired:
                    broker.process.kill()
                    broker.process.wait(timeout=5)
                    raise
                finally:
                    broker.process.stderr.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--messages', type=int, default=2000)
    parser.add_argument('--warmup', type=int, default=100)
    parser.add_argument('--state-root', type=Path, default=Path('/tmp'))
    parser.add_argument('--payload-bytes', type=int, default=256)
    parser.add_argument('--idle-seconds', type=float, default=1)
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Linux /proc required; use Ubuntu/WSL')
    if not (1 <= args.repetitions <= 10 and 10 <= args.messages <= 10000
            and 1 <= args.warmup <= 1000 and 8 <= args.payload_bytes <= 4096
            and .1 <= args.idle_seconds <= 30):
        parser.error('invalid benchmark bounds')
    fixtures.BROKER = args.broker.resolve(strict=True)
    if not os.access(fixtures.BROKER, os.X_OK):
        parser.error('broker executable required')
    # Never overwrite a report or any source/installation path accidentally.
    if args.report.exists():
        parser.error('report already exists; choose a new filename')
    if not args.state_root.is_dir():
        parser.error('state root must be an existing writable directory')
    cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')), 'unknown')
    results = []
    for repetition in range(1, args.repetitions + 1):
        for connections in (1, 8, 32, None):
            result = scenario(args, repetition, connections)
            results.append(result)
            print(json.dumps(result), flush=True)
    report = {'schema_version': 1, 'completed_utc': datetime.now(timezone.utc).isoformat(),
              'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'broker_binary_sha256': hashlib.sha256(fixtures.BROKER.read_bytes()).hexdigest(),
              'kernel': platform.release(), 'machine': platform.machine(),
              'cpu_model': cpu, 'logical_cpus_visible': os.cpu_count(),
              'memory_total_kib': int(Path('/proc/meminfo').read_text().splitlines()[0].split()[1]),
              'python': platform.python_version(),
              'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
              'profile': 'release, open-lab loopback; temporary state; default quotas; retained QoS1 with varying sequence',
              'state_filesystem': subprocess.check_output(['stat', '-f', '-c', '%T', str(args.state_root)], text=True).strip(),
              'percentiles': 'nearest-rank per repetition', 'sampling_interval_ms': 20,
              'parameters': {k: v for k, v in vars(args).items() if k not in ('broker', 'report', 'state_root')},
              'results': results,
              'limitations': ['Sequential publisher; not maximum throughput',
                              'PUBACK latency is not subscriber/application latency',
                              'No TLS, fan-out, slow consumers or connect storm measured',
                              'RSS sampled; HWM includes process startup; neither is total host RAM',
                              'CPU ticks are coarse; percent uses one core as100%',
                              'WSL environment and competing workloads affect measurements']}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(f'BASELINE_COMPLETE: {args.report}')


if __name__ == '__main__':
    main()
