#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P101: real mTLS endpoint authentication, ACL and durable identity isolation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import ssl
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_multi_endpoint import free_port, hash_fixture, wait_port, wait_subscription


def client(binary, root, port, command, *args):
    return [binary, command, '--host', '127.0.0.1', '--port', str(port),
            '--ca', root / 'ca.crt', '--cert', root / 'client.crt',
            '--key', root / 'client.key', '--username', 'fixture-device',
            '--password-file', root / 'password', '--output', 'jsonl', *args]


def run(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=10)


def publish(binary, root, port, topic, message):
    return run(client(binary, root, port, 'pub', '--topic', topic,
                      '--message', message, '--qos', '1', '--client-id', 'scoped-pub'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('broker', 'client', 'admin'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        'c27', ROOT.parent / 'xmqr-client/validation/C27-integration.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix='xmqr-p101-') as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        fixture.certificates(root)
        password = secrets.token_urlsafe(24)
        (root / 'password').write_text(password)
        (root / 'password').chmod(0o600)
        fingerprint = hashlib.sha256(
            ssl.PEM_cert_to_DER_cert((root / 'client.crt').read_text())).hexdigest()
        user = "[[users]]\nusername='fixture-device'\n" + \
            f"password_hash='{hash_fixture(args.admin, password)}'\n" + \
            f"cert_sha256='sha256:{fingerprint}'\n"
        for suffix in ('a', 'b'):
            (root / f'users-{suffix}.toml').write_text(user)
        (root / 'acl-a.toml').write_text(
            "[[rules]]\nusername='fixture-device'\n"
            "publish=['scope/a','scope/common']\nsubscribe=['scope/a']\n")
        (root / 'acl-b.toml').write_text(
            "[[rules]]\nusername='fixture-device'\n"
            "publish=['scope/b']\nsubscribe=['scope/b','scope/common']\n")
        ports = [free_port(), free_port()]
        assert ports[0] != ports[1]
        common = ('version=1\n[broker]\nmode="secure-mtls"\n'
                  f'bind="127.0.0.1:{ports[0]}"\n'
                  f'additional_binds=["127.0.0.1:{ports[1]}"]\n'
                  'state_dir="state"\n[tls]\nserver_cert="server.crt"\n'
                  'server_key="server.key"\nclient_ca="ca.crt"\n')
        entries = [f'[[endpoint_policies]]\nbind="127.0.0.1:{port}"\n'
                   f'users_file="users-{suffix}.toml"\nacl_file="acl-{suffix}.toml"\n'
                   for port, suffix in zip(ports, ('a', 'b'))]
        config = root / 'broker.toml'
        config.write_text(common + ''.join(entries))
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('MQTT_')}
        environment['MQTT_CONFIG'] = str(config)
        with (root / 'broker.log').open('wb') as log:
            broker = subprocess.Popen([args.broker], env=environment, stdout=log, stderr=log)
            try:
                for port in ports:
                    wait_port(broker, port)
                subscribers = []
                try:
                    for port, topic in zip(ports, ('scope/a', 'scope/common')):
                        subscriber = subprocess.Popen(
                            client(args.client, root, port, 'sub', '--topic', topic,
                                   '--count', '1', '--qos', '1',
                                   '--client-id', 'same-physical-id'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        subscribers.append(subscriber)
                        wait_subscription(subscriber)
                    assert publish(args.client, root, ports[0], 'scope/a', 'for-a').returncode == 0
                    assert publish(args.client, root, ports[0], 'scope/common', 'for-b').returncode == 0
                    for subscriber, topic in zip(subscribers, ('scope/a', 'scope/common')):
                        out, err = subscriber.communicate(timeout=10)
                        assert subscriber.returncode == 0, err
                        assert topic in out, 'same client ID caused cross-endpoint takeover'
                finally:
                    for subscriber in subscribers:
                        if subscriber.poll() is None:
                            subscriber.kill(); subscriber.communicate(timeout=3)
                assert publish(args.client, root, ports[0], 'scope/b', 'denied').returncode != 0
                assert publish(args.client, root, ports[1], 'scope/a', 'denied').returncode != 0
                assert publish(args.client, root, ports[1], 'scope/b', 'allowed').returncode == 0
                (root / 'wrong-password').write_text(secrets.token_urlsafe(24))
                wrong = client(args.client, root, ports[1], 'pub', '--topic', 'scope/b',
                               '--message', 'denied')
                wrong[wrong.index('--password-file') + 1] = root / 'wrong-password'
                assert run(wrong).returncode != 0
                (root / 'c50-mtls.toml').write_text(
                    'version=1\n[connection]\nhost="wrong.invalid"\nport=1\n'
                    'username="fixture-device"\nca="wrong-ca.crt"\n'
                    'cert="client.crt"\nkey="client.key"\npassword_file="password"\n'
                    'qos=1\nclean_session=false\nreconnect_attempts=1\n'
                    'total_timeout_seconds=15\n')
                client_environment = environment.copy()
                client_environment['MQTT_CLIENT_HOST'] = 'wrong.invalid'
                client_environment['MQTT_CLIENT_PORT'] = str(ports[1])
                client_environment['MQTT_CA_CERT'] = str(root / 'ca.crt')
                profiled = subprocess.run(
                    [args.client, 'pub', '--profile', root / 'c50-mtls.toml',
                     '--host', '127.0.0.1', '--topic', 'scope/b', '--message', 'c50-mtls'],
                    env=client_environment, capture_output=True, text=True, timeout=15)
                assert profiled.returncode == 0, profiled.stderr
                print('PASS: C50 mTLS profile < environment < CLI with private password file')
                retained = client(args.client, root, ports[0], 'pub', '--topic', 'scope/common',
                                  '--message', 'retained-after-restart', '--retain', 'true',
                                  '--qos', '1', '--client-id', 'scoped-retained')
                assert run(retained).returncode == 0
                print('PASS: same username/client ID isolated; endpoint ACLs and shared router verified')
            finally:
                broker.send_signal(signal.SIGTERM)
                assert broker.wait(timeout=12) == 0
        assert (root / 'state/.mqtt-broker-profile').read_text().strip() == 'secure-mtls-scoped'
        with (root / 'restart.log').open('wb') as log:
            broker = subprocess.Popen([args.broker], env=environment, stdout=log, stderr=log)
            try:
                for port in ports:
                    wait_port(broker, port)
                replay = run(client(args.client, root, ports[1], 'sub',
                                    '--topic', 'scope/common', '--count', '1',
                                    '--client-id', 'scoped-replay'))
                assert replay.returncode == 0, replay.stderr
                event = json.loads(replay.stdout.strip())
                assert event['retain'] and bytes(event['payload_bytes']) == b'retained-after-restart'
            finally:
                broker.send_signal(signal.SIGTERM)
                assert broker.wait(timeout=12) == 0
        print('PASS: retained from primary replays under secondary ACL after restart')
        for candidate in (common + entries[0], common + entries[0] * 2,
                          common + entries[0] + entries[1].replace(str(ports[1]), '9999'),
                          common + '[security]\nbundle="missing.toml"\n' + ''.join(entries),
                          common.replace('state_dir="state"', 'state_dir="old-state"') +
                          ''.join(entries)):
            if 'old-state' in candidate:
                old = root / 'old-state'
                old.mkdir()
                (old / '.mqtt-broker-profile').write_text('secure-mtls\n')
            config.write_text(candidate)
            rejected = subprocess.run([args.broker], env=environment,
                                      capture_output=True, timeout=5)
            assert rejected.returncode != 0, 'invalid scoped configuration started'
        print('PASS: incomplete/duplicate/foreign/bundle mappings and old state rejected')


if __name__ == '__main__':
    main()
