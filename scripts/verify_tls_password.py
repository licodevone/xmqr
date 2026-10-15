#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P97/C48: isolated TLS-password broker/client integration; no installed services."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_multi_endpoint import free_port, hash_fixture, wait_port, wait_subscription
from verify_tls_rotation import rotate


def run_client(binary, root, port, password_file, *args):
    command = [binary, *args, '--tls-password', '--host', '127.0.0.1',
               '--port', str(port), '--output', 'jsonl']
    for flag, value in (('--ca', root / 'ca.crt'),
                        ('--username', 'fixture-device'),
                        ('--password-file', password_file)):
        if flag not in args:
            command.extend([flag, value])
    return subprocess.run(
        command,
        capture_output=True, text=True, timeout=12)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('broker', 'client', 'admin'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        'c27', ROOT.parent / 'xmqr-client/validation/C27-integration.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix='xmqr-p97-') as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        fixture.certificates(root)
        second = root / 'next'
        second.mkdir()
        fixture.certificates(second)
        for name in ('server.crt', 'server.key'):
            shutil.copyfile(root / name, root / ('active-' + name))
        password = secrets.token_urlsafe(24)
        (root / 'password').write_text(password)
        (root / 'password').chmod(0o600)
        (root / 'wrong-password').write_text(secrets.token_urlsafe(24))
        (root / 'wrong-password').chmod(0o600)
        (root / 'users.toml').write_text(
            "[[users]]\nusername='fixture-device'\n"
            f"password_hash='{hash_fixture(args.admin, password)}'\n")
        (root / 'acl.toml').write_text(
            "[[rules]]\nusername='fixture-device'\n"
            "publish=['p97/value']\nsubscribe=['p97/#']\n")
        port = free_port()
        (root / 'broker.toml').write_text(
            'version=1\n[broker]\nmode="tls-password"\n'
            f'bind="127.0.0.1:{port}"\nstate_dir="state"\n'
            '[tls]\nserver_cert="active-server.crt"\nserver_key="active-server.key"\n'
            '[security]\nusers_file="users.toml"\nacl_file="acl.toml"\n')
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('MQTT_')}
        environment['MQTT_CONFIG'] = str(root / 'broker.toml')
        environment['RUST_LOG'] = 'info'
        with (root / 'broker.log').open('wb') as log:
            broker = subprocess.Popen([args.broker], env=environment, stdout=log, stderr=log)
            try:
                wait_port(broker, port)
                for qos in range(3):
                    subscriber = subprocess.Popen(
                        [args.client, 'sub', '--tls-password', '--host', '127.0.0.1',
                         '--port', str(port), '--ca', root / 'ca.crt',
                         '--username', 'fixture-device', '--password-file', root / 'password',
                         '--topic', 'p97/#', '--qos', str(qos), '--count', '1',
                         '--client-id', f'p97-sub-{qos}', '--output', 'jsonl'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    try:
                        wait_subscription(subscriber)
                        published = run_client(
                            args.client, root, port, root / 'password',
                            'pub', '--topic', 'p97/value', '--message', f'value-{qos}',
                            '--qos', str(qos), '--client-id', f'p97-pub-{qos}')
                        assert published.returncode == 0, published.stderr
                        out, err = subscriber.communicate(timeout=12)
                        assert subscriber.returncode == 0, err
                        event = json.loads(out.strip())
                        assert event['qos'] == qos
                        assert bytes(event['payload_bytes']) == f'value-{qos}'.encode()
                    finally:
                        if subscriber.poll() is None:
                            subscriber.kill()
                            subscriber.communicate(timeout=3)
                for extra in (
                    ('--username', 'unknown-fixture'),
                    ('--password-file', str(root / 'wrong-password')),
                    ('--ca', str(root / 'other.crt')),
                ):
                    denied = run_client(args.client, root, port, root / 'password',
                                        'pub', '--topic', 'p97/value', '--message', 'denied', *extra)
                    assert denied.returncode != 0, f'negative accepted: {extra[0]}'
                    assert password not in denied.stderr
                denied_acl = run_client(args.client, root, port, root / 'password',
                                        'sub', '--topic', 'denied/#', '--count', '1')
                assert denied_acl.returncode != 0, 'ACL-negative subscription accepted'
                context = ssl.create_default_context(cafile=str(root / 'ca.crt'))
                with socket.create_connection(('127.0.0.1', port), timeout=3) as raw:
                    try:
                        context.wrap_socket(raw, server_hostname='wrong.invalid')
                    except ssl.SSLCertVerificationError:
                        pass
                    else:
                        raise AssertionError('wrong SAN was accepted')
                print('PASS: TLS without client certificate; QoS0/1/2; password, CA, SAN and ACL negatives')
                (root / 'c50-password.toml').write_text(
                    'version=1\n[connection]\ntls_password=true\n'
                    'host="wrong.invalid"\nport=1\nusername="fixture-device"\n'
                    'ca="wrong-ca.crt"\npassword_file="password"\nqos=1\n'
                    'clean_session=false\nreconnect_attempts=1\n'
                    'total_timeout_seconds=15\n')
                client_environment = environment.copy()
                client_environment['MQTT_CLIENT_HOST'] = 'wrong.invalid'
                client_environment['MQTT_CLIENT_PORT'] = str(port)
                client_environment['MQTT_CA_CERT'] = str(root / 'ca.crt')
                profiled = subprocess.run(
                    [args.client, 'pub', '--profile', root / 'c50-password.toml',
                     '--host', '127.0.0.1', '--topic', 'p97/value', '--message', 'c50-tls-password'],
                    env=client_environment, capture_output=True, text=True, timeout=15)
                assert profiled.returncode == 0, profiled.stderr
                print('PASS: C50 TLS-password profile < environment < CLI with private password file')
                (root / 'active-server.key').write_text('invalid-key')
                rotate(broker, root / 'broker.log', False)
                old = run_client(args.client, root, port, root / 'password',
                                 'pub', '--topic', 'p97/value', '--message', 'old-still-active')
                assert old.returncode == 0, 'invalid key replaced TLS-password generation'
                for name in ('server.crt', 'server.key'):
                    shutil.copyfile(second / name, root / ('active-' + name))
                rotate(broker, root / 'broker.log', True)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    changed = run_client(args.client, root, port, root / 'password',
                                         'pub', '--topic', 'p97/value', '--message', 'new',
                                         '--ca', second / 'ca.crt')
                    if changed.returncode == 0:
                        break
                    time.sleep(.1)
                assert changed.returncode == 0, 'TLS-password certificate rotation failed'
                assert run_client(args.client, root, port, root / 'password',
                                  'pub', '--topic', 'p97/value', '--message', 'old').returncode != 0
                for name in ('server.crt', 'server.key'):
                    shutil.copyfile(root / name, root / ('active-' + name))
                rotate(broker, root / 'broker.log', True)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    recovered = run_client(args.client, root, port, root / 'password',
                                           'pub', '--topic', 'p97/value', '--message', 'rollback')
                    if recovered.returncode == 0:
                        break
                    time.sleep(.1)
                assert recovered.returncode == 0, 'TLS-password rollback failed'
                print('PASS: TLS-password invalid key rollback and server certificate rotation')
            finally:
                broker.terminate()
                assert broker.wait(timeout=12) == 0
        assert (root / 'state' / '.mqtt-broker-profile').read_text().strip() == 'tls-password'
        good_config = (root / 'broker.toml').read_text()
        for addition in ('client_ca="ca.crt"\n', 'client_crl="missing.crl"\n'):
            (root / 'broker.toml').write_text(good_config.replace(
                '[security]', addition + '[security]'))
            rejected = subprocess.run([args.broker], env=environment,
                                      capture_output=True, timeout=5)
            assert rejected.returncode != 0, 'client CA/CRL accepted in tls-password mode'
        (root / 'broker.toml').write_text(good_config)
        rejected = run_client(args.client, root, port, root / 'password',
                              'pub', '--topic', 'p97/value', '--message', 'x',
                              '--cert', root / 'client.crt')
        assert rejected.returncode != 0, 'client certificate accepted with --tls-password'
        print('PASS: client identity inputs rejected by broker configuration and client CLI')


if __name__ == '__main__':
    main()
