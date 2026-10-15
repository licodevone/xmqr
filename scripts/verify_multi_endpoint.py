#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P96/C47: isolated real mTLS endpoints and client profiles, no installed services."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import select
import shlex
import socket
import ssl
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT.parent / 'xmqr-client/validation/C27-integration.py'


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def hash_fixture(admin, password):
    command = f'{shlex.quote(str(admin))} hash-password'
    run = subprocess.run(['script', '-q', '-e', '-c', command, '/dev/null'],
                         input=f'{password}\n{password}\n', capture_output=True,
                         text=True, timeout=20, check=True)
    match = re.search(r'password_hash = "(\$argon2id\$[^"\r\n]+)"', run.stdout)
    assert match, 'test hash was not produced'
    return match.group(1)


def wait_port(process, port):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        assert process.poll() is None, 'broker exited before readiness'
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.2):
                return
        except OSError:
            time.sleep(.05)
    raise AssertionError('broker did not bind endpoint')


def wait_subscription(process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        assert process.poll() is None, 'subscriber exited before SUBACK'
        ready, _, _ = select.select([process.stderr], [], [], .2)
        if ready and 'Assinatura ativa' in process.stderr.readline():
            return
    raise AssertionError('subscriber did not receive SUBACK')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('broker', 'client', 'admin'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('c27', FIXTURE)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix='xmqr-p96-') as temporary:
        root = Path(temporary)
        password = secrets.token_urlsafe(24)
        fixture.certificates(root)
        for name in ('ca.crt', 'server.crt', 'server.key', 'client.crt', 'client.key'):
            (root / name).chmod(0o600)
        (root / 'password').write_text(password)
        (root / 'password').chmod(0o600)
        (root / 'wrong-password').write_text(secrets.token_urlsafe(24))
        (root / 'wrong-password').chmod(0o600)
        der = ssl.PEM_cert_to_DER_cert((root / 'client.crt').read_text())
        fingerprint = hashlib.sha256(der).hexdigest()
        policy = root / 'security.toml'
        policy.write_text("version=1\n[[users]]\nusername='fixture-device'\n"
                          f"password_hash='{hash_fixture(args.admin, password)}'\n"
                          f"cert_sha256='sha256:{fingerprint}'\n"
                          "publish=['p96/value']\nsubscribe=['p96/#']\n")
        policy.chmod(0o600)
        ports = [free_port(), free_port()]
        assert ports[0] != ports[1]
        config = root / 'broker.toml'
        config.write_text('version=1\n[broker]\nmode="secure-mtls"\n'
                          f'bind="127.0.0.1:{ports[0]}"\n'
                          f'additional_binds=["127.0.0.1:{ports[1]}"]\n'
                          'state_dir="state"\n[tls]\nserver_cert="server.crt"\n'
                          'server_key="server.key"\nclient_ca="ca.crt"\n'
                          '[security]\nbundle="security.toml"\n'
                          '[limits]\nmax_connections=2\n')
        for index, port in enumerate(ports):
            (root / f'profile-{index}.toml').write_text(
                f'version=1\n[connection]\nhost="127.0.0.1"\nport={port}\n'
                'username="fixture-device"\nca="ca.crt"\ncert="client.crt"\n'
                'key="client.key"\npassword_file="password"\noutput="jsonl"\n')
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('MQTT_')}
        environment['MQTT_CONFIG'] = str(config)
        with (root / 'broker.log').open('wb') as log:
            broker = subprocess.Popen([args.broker], env=environment, stdout=log, stderr=log)
            try:
                for port in ports:
                    wait_port(broker, port)
                for qos in range(3):
                    sub = subprocess.Popen([args.client, 'sub', '--profile',
                                            root / 'profile-1.toml', '--topic', 'p96/#',
                                            '--qos', str(qos), '--count', '1',
                                            '--client-id', f'p96-sub-{qos}'],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True)
                    try:
                        wait_subscription(sub)
                        publication = subprocess.run(
                            [args.client, 'pub', '--profile', root / 'profile-0.toml',
                             '--topic', 'p96/value', '--message', f'from-primary-{qos}',
                             '--qos', str(qos), '--client-id', f'p96-pub-{qos}'],
                            capture_output=True, text=True, timeout=10)
                        assert publication.returncode == 0, publication.stderr
                        out, err = sub.communicate(timeout=10)
                        assert sub.returncode == 0, err
                        event = json.loads(out.strip())
                        assert event['topic'] == 'p96/value'
                        assert bytes(event['payload_bytes']) == f'from-primary-{qos}'.encode()
                        assert event['qos'] == qos
                    finally:
                        if sub.poll() is None:
                            sub.kill()
                            sub.communicate(timeout=5)
                for override in (['--ca', str(root / 'other.crt')],
                                 ['--username', 'unknown-fixture'],
                                 ['--password-file', str(root / 'wrong-password')]):
                    denied = subprocess.run(
                        [args.client, 'pub', '--profile', root / 'profile-0.toml',
                         '--topic', 'p96/value', '--message', 'never-delivered', *override],
                        capture_output=True, text=True, timeout=10)
                    assert denied.returncode != 0, f'negative accepted: {override[0]}'
                    assert password not in denied.stderr
                print('PASS: wrong CA, username and password rejected with profile overrides')
                time.sleep(.2)
                context = ssl.create_default_context(cafile=str(root / 'ca.crt'))
                context.load_cert_chain(root / 'client.crt', root / 'client.key')
                holders = []
                try:
                    for port in ports:
                        plain = socket.create_connection(('127.0.0.1', port), timeout=2)
                        holders.append(context.wrap_socket(plain, server_hostname='127.0.0.1'))
                    with socket.create_connection(('127.0.0.1', ports[0]), timeout=2) as extra:
                        extra.settimeout(2)
                        try:
                            assert extra.recv(1) == b'', 'third connection admitted above global limit'
                        except ConnectionResetError:
                            pass
                finally:
                    for holder in holders:
                        holder.close()
                print('PASS: shared N/N+1 admission limit across endpoints')
                time.sleep(.2)
                publication = subprocess.run(
                    [args.client, 'pub', '--profile', root / 'profile-0.toml',
                     '--topic', 'p96/value', '--message', 'retained-after-restart',
                     '--qos', '1', '--retain', 'true', '--client-id', 'p96-retained'],
                    capture_output=True, text=True, timeout=10)
                assert publication.returncode == 0, publication.stderr
                print('PASS: two mTLS endpoints, profile paths and cross-endpoint QoS0/1/2')
            finally:
                broker.terminate()
                assert broker.wait(timeout=10) == 0
        with (root / 'broker-restart.log').open('wb') as log:
            restarted = subprocess.Popen([args.broker], env=environment, stdout=log, stderr=log)
            try:
                for port in ports:
                    wait_port(restarted, port)
                replay = subprocess.run(
                    [args.client, 'sub', '--profile', root / 'profile-1.toml',
                     '--topic', 'p96/#', '--qos', '1', '--count', '1',
                     '--client-id', 'p96-replay'],
                    capture_output=True, text=True, timeout=10)
                assert replay.returncode == 0, replay.stderr
                event = json.loads(replay.stdout.strip())
                assert event['retain'] is True
                assert bytes(event['payload_bytes']) == b'retained-after-restart'
                print('PASS: retained replay on secondary endpoint after restart')
            finally:
                restarted.terminate()
                assert restarted.wait(timeout=10) == 0
        # A blocked secondary bind must fail startup and release the primary.
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', ports[1]))
            occupied.listen()
            failed = subprocess.run([args.broker], env=environment, capture_output=True,
                                    timeout=10)
            assert failed.returncode != 0
            with socket.socket() as released:
                released.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                released.bind(('127.0.0.1', ports[0]))
        print('PASS: occupied additional bind rejects startup and releases primary')


if __name__ == '__main__':
    main()
