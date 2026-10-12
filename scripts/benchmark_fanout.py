#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P72: bounded Linux wire delivery benchmark, QoS0/1/2, fan-out and mTLS."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import select
import socket
import ssl
import statistics
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
import benchmark_baseline as baseline

ROOT = Path(__file__).resolve().parents[1]
f = baseline.fixtures
PASSWORD = b'p72-public-test-password'


def fixture_hash(admin):
    """Use the real admin's protected prompt in a test-owned pseudoterminal."""
    import pty
    pid, descriptor = pty.fork()
    if pid == 0:
        os.execl(str(admin), str(admin), 'hash-password')
    data = b''
    prompts = 0
    deadline = time.monotonic() + 15
    waited = False
    try:
        while time.monotonic() < deadline:
            if select.select([descriptor], [], [], .1)[0]:
                try:
                    chunk = os.read(descriptor, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                data += chunk
                if prompts == 0 and b'Password: ' in data:
                    os.write(descriptor, PASSWORD + b'\n')
                    prompts = 1
                if prompts == 1 and b'Confirm password: ' in data:
                    os.write(descriptor, PASSWORD + b'\n')
                    prompts = 2
                if b'password_hash = "' in data:
                    _, status = os.waitpid(pid, 0)
                    waited = True
                    if status != 0:
                        raise AssertionError('test hash generator failed')
                    return data.split(b'password_hash = "', 1)[1].split(b'"', 1)[0].decode()
        raise AssertionError('test hash generator deadline')
    finally:
        os.close(descriptor)
        if not waited:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)


def security(root, admin):
    spec = importlib.util.spec_from_file_location(
        'c27', ROOT.parent / 'xmqr-client/validation/C27-integration.py')
    c27 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c27)
    c27.certificates(root)
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
        (root / 'client.crt').read_text())).hexdigest()
    policy = root / 'security.toml'
    policy.write_text("version=1\n[[users]]\nusername='p72-device'\n"
                      f"password_hash='{fixture_hash(admin)}'\n"
                      f"cert_sha256='sha256:{fingerprint}'\n"
                      "publish=['benchmark/value']\nsubscribe=['benchmark/#']\n")
    policy.chmod(0o600)
    for key in root.glob('*.key'):
        key.chmod(0o600)
    context = ssl.create_default_context(cafile=str(root / 'ca.crt'))
    context.load_cert_chain(root / 'client.crt', root / 'client.key')
    return context


class Broker(f.Broker):
    def __init__(self, root, binary, security_root=None):
        super().__init__(root)
        self.binary = binary
        self.security_root = security_root

    def start(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('MQTT_')}
        env.update(MQTT_MODE='open-lab', MQTT_BIND=f'127.0.0.1:{self.port}',
                   MQTT_STATE_DIR=str(self.state), RUST_LOG='error')
        if self.security_root:
            root = self.security_root
            env.update(MQTT_MODE='secure-mtls', MQTT_SERVER_CERT=str(root / 'server.crt'),
                       MQTT_SERVER_KEY=str(root / 'server.key'),
                       MQTT_CLIENT_CA=str(root / 'ca.crt'),
                       MQTT_SECURITY_BUNDLE=str(root / 'security.toml'))
        # A file avoids a blocked stderr pipe; keep diagnostics outside reports.
        self.log = (self.root / 'broker.log').open('wb')
        self.process = subprocess.Popen([str(self.binary)], env=env,
                                        stdout=subprocess.DEVNULL, stderr=self.log)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError('test broker exited; inspect temporary diagnostics')
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=.1):
                    return
            except OSError:
                time.sleep(.02)
        raise AssertionError('test broker readiness deadline')

    def shutdown(self):
        try:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.terminate()
                try:
                    code = self.process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
                    raise
                if code != 0:
                    raise AssertionError(f'test broker shutdown exit {code}')
        finally:
            if hasattr(self, 'log'):
                self.log.close()


class Client(f.WireClient):
    def __init__(self, broker, identifier, context=None, password=PASSWORD):
        self.socket = socket.create_connection(('127.0.0.1', broker.port), timeout=5)
        try:
            if context is not None:
                self.socket = context.wrap_socket(self.socket, server_hostname='127.0.0.1')
            flags = 2 | (0xc0 if context is not None else 0)
            body = f.text('MQTT') + bytes([4, flags, 0, 30]) + f.text(identifier)
            if context is not None:
                body += f.text('p72-device') + len(password).to_bytes(2, 'big') + password
            self.send(0x10, body)
            if self.receive() != (0x20, b'\0\0'):
                raise AssertionError('test CONNECT refused')
        except BaseException:
            self.close()
            raise


def expect(client, header, identifier):
    if client.receive() != (header, identifier):
        raise AssertionError('unexpected QoS acknowledgment or packet identifier')


def delivery(publisher, subscribers, qos, sequence, size):
    identifier = ((sequence % 65535) + 1).to_bytes(2, 'big') if qos else b''
    payload = sequence.to_bytes(8, 'big') + b'x' * (size - 8)
    publisher.send(0x30 | qos << 1, f.text('benchmark/value') + identifier + payload)
    if qos == 1:
        expect(publisher, 0x40, identifier)
    elif qos == 2:
        expect(publisher, 0x50, identifier)
        publisher.send(0x62, identifier)
        expect(publisher, 0x70, identifier)
    for subscriber in subscribers:
        header, body = subscriber.receive()
        if header != 0x30 | qos << 1:
            raise AssertionError('unexpected publication flags/QoS')
        topic_size = int.from_bytes(body[:2], 'big')
        offset = 2 + topic_size
        packet_id = body[offset:offset + 2] if qos else b''
        if body[2:offset] != b'benchmark/value' or body[offset + (2 if qos else 0):] != payload:
            raise AssertionError('delivery topic/payload/sequence mismatch')
        if qos and packet_id == b'\0\0':
            raise AssertionError('zero delivery packet identifier')
        if qos == 1:
            subscriber.send(0x40, packet_id)
        elif qos == 2:
            subscriber.send(0x50, packet_id)
            expect(subscriber, 0x62, packet_id)
            subscriber.send(0x70, packet_id)


def scenario(args, transport, qos, fanout, repetition, security_root, context):
    clients = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p72-state-', dir=args.state_root) as temporary:
        broker = Broker(temporary, args.broker, security_root if transport == 'mtls' else None)
        try:
            broker.start()
            selected = context if transport == 'mtls' else None
            publisher = Client(broker, 'publisher', selected)
            clients.append(publisher)
            subscribers = []
            for index in range(fanout):
                subscriber = Client(broker, f'subscriber-{index}', selected)
                clients.append(subscriber)
                subscribers.append(subscriber)
                if subscriber.subscribe([('benchmark/#', qos)]) != (0x90, b'\0\x01' + bytes([qos])):
                    raise AssertionError('SUBACK mismatch')
            deadline = time.monotonic() + args.scenario_seconds
            latency = []
            for index in range(args.warmup):
                if time.monotonic() > deadline:
                    raise TimeoutError('scenario total deadline')
                delivery(publisher, subscribers, qos, index, args.payload_bytes)
            with baseline.Sampler(broker.process.pid) as sampler:
                for index in range(args.messages):
                    if time.monotonic() > deadline:
                        raise TimeoutError('scenario total deadline')
                    start = time.perf_counter_ns()
                    delivery(publisher, subscribers, qos, index + args.warmup, args.payload_bytes)
                    latency.append((time.perf_counter_ns() - start) / 1e6)
            # Ordered PING barriers drain ACKs before disconnect/shutdown.
            for client in clients:
                client.ping()
            return dict(transport=transport, qos=qos, fanout=fanout, repetition=repetition,
                        messages=len(latency), deliveries=len(latency) * fanout,
                        warmup_messages=args.warmup, payload_bytes=args.payload_bytes,
                        messages_per_second=len(latency) / sampler.elapsed,
                        deliveries_per_second=len(latency) * fanout / sampler.elapsed,
                        latency_ms=dict(mean=statistics.mean(latency),
                                        p50=baseline.percentile(latency, .5),
                                        p95=baseline.percentile(latency, .95),
                                        p99=baseline.percentile(latency, .99)), **sampler.result())
        finally:
            for client in clients:
                try:
                    client.send(0xe0)
                except OSError:
                    pass
                client.close()
            broker.shutdown()


def tls_negatives(args, root, context):
    with tempfile.TemporaryDirectory(prefix='xmqr-p72-negative-', dir=args.state_root) as temporary:
        broker = Broker(temporary, args.broker, root)
        try:
            broker.start()
            wrong = ssl.create_default_context(cafile=str(root / 'other.crt'))
            wrong.load_cert_chain(root / 'client.crt', root / 'client.key')
            try:
                Client(broker, 'wrong-ca', wrong)
            except ssl.SSLCertVerificationError:
                pass
            else:
                raise AssertionError('wrong CA was accepted')
            try:
                Client(broker, 'wrong-password', context, password=b'wrong-test-password')
            except (AssertionError, EOFError):
                pass
            else:
                raise AssertionError('wrong password was accepted')
            with Client(broker, 'valid-after-negatives', context) as client:
                client.ping()
            return ['wrong_ca_refused', 'wrong_password_refused', 'valid_connection_after_negatives']
        finally:
            broker.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    parser.add_argument('--admin', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--messages', type=int, default=300)
    parser.add_argument('--warmup', type=int, default=20)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--payload-bytes', type=int, default=256)
    parser.add_argument('--scenario-seconds', type=int, default=120)
    parser.add_argument('--fanouts', type=int, nargs='+', default=[1, 8])
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Linux /proc and pty required')
    if not (10 <= args.messages <= 10000 and 1 <= args.warmup <= 1000
            and 1 <= args.repetitions <= 10 and 8 <= args.payload_bytes <= 4096
            and 10 <= args.scenario_seconds <= 600 and args.fanouts
            and all(1 <= n <= 32 for n in args.fanouts)
            and len(args.fanouts) == len(set(args.fanouts))):
        parser.error('invalid benchmark bounds')
    if args.report.exists() or args.report.is_symlink():
        parser.error('report exists; choose a new filename')
    if not args.state_root.is_dir():
        parser.error('existing state-root directory required')
    for name in ('broker', 'admin'):
        binary = getattr(args, name).resolve(strict=True)
        if not os.access(binary, os.X_OK):
            parser.error(f'{name} executable required')
        setattr(args, name, binary)
    binary_hash = hashlib.sha256(args.broker.read_bytes()).hexdigest()
    source_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    version = subprocess.check_output([str(args.broker), '--version'], text=True, timeout=5).strip()
    results = []
    with tempfile.TemporaryDirectory(prefix='xmqr-p72-security-', dir=args.state_root) as temporary:
        root = Path(temporary)
        context = security(root, args.admin)
        negatives = tls_negatives(args, root, context)
        for repetition in range(1, args.repetitions + 1):
            for transport in ('open-lab', 'mtls'):
                for qos in (0, 1, 2):
                    for fanout in args.fanouts:
                        result = scenario(args, transport, qos, fanout, repetition, root, context)
                        results.append(result)
                        print(json.dumps(result), flush=True)
    if hashlib.sha256(args.broker.read_bytes()).hexdigest() != binary_hash:
        raise AssertionError('broker binary changed during campaign')
    report = dict(schema_version=1, completed_utc=datetime.now(timezone.utc).isoformat(),
                  source_head=source_head, broker_version=version, broker_sha256=binary_hash,
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  dependency_sha256={name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                                     for name in ('benchmark_baseline.py', 'verify_interop.py')},
                  parameters=dict(messages=args.messages, warmup=args.warmup,
                                  repetitions=args.repetitions, fanouts=args.fanouts,
                                  payload_bytes=args.payload_bytes,
                                  scenario_seconds=args.scenario_seconds,
                                  retained=False, socket_tcp_nodelay=False),
                  environment=dict(kernel=platform.release(), python=platform.python_version(),
                                   cpu=next((line.split(':', 1)[1].strip() for line in
                                             Path('/proc/cpuinfo').read_text().splitlines()
                                             if line.startswith('model name')), 'unknown'),
                                   logical_cpus=len(os.sched_getaffinity(0)),
                                   filesystem=subprocess.check_output(
                                       ['stat', '-f', '-c', '%T', str(args.state_root)], text=True).strip()),
                  tls_negatives=negatives, results=results,
                  limitations=['Sequential wire delivery plus ACK exchange, not business processing',
                               'No maximum throughput, saturation or production claim',
                               'TLS connection setup excluded from measurement',
                               'CPU ticks are coarse; 100% means one core',
                               'WSL and competing workloads affect results'])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(f'FANOUT_COMPLETE: {args.report}')


if __name__ == '__main__':
    main()
