#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P100: isolated SIGUSR1 TLS rotation across both mTLS endpoints."""
import argparse
import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import secrets
import select
import shutil
import signal
import ssl
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_multi_endpoint import free_port, hash_fixture, wait_port, wait_subscription


def openssl(root, *args):
    subprocess.run(['openssl', *map(str, args)], cwd=root, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)


def crl(root, name, revoked=False):
    config = root / 'ca.cnf'
    config.write_text('[ca]\ndefault_ca=local\n[local]\n'
                      f'database={root / "index"}\nnew_certs_dir={root / "newcerts"}\n'
                      f'certificate={root / "ca.crt"}\nprivate_key={root / "ca.key"}\n'
                      f'serial={root / "serial"}\ndefault_md=sha256\ndefault_crl_days=1\n'
                      'crl_extensions=crl_ext\n[crl_ext]\nauthorityKeyIdentifier=keyid:always\n')
    (root / 'newcerts').mkdir(exist_ok=True)
    (root / 'index').write_text('')
    (root / 'serial').write_text('04\n')
    if revoked:
        openssl(root, 'ca', '-config', config, '-revoke', root / 'client.crt', '-batch')
    openssl(root, 'ca', '-config', config, '-gencrl', '-out', root / name, '-batch')


def expired_ca(source, destination):
    pem = source.read_text()
    der = bytearray(ssl.PEM_cert_to_DER_cert(pem))
    dates = list(re.finditer(rb'\d{12}Z', der))
    assert len(dates) >= 2, 'fixture validity not encoded as UTC time'
    end = dates[1]
    der[end.start():end.start()+2] = b'20'
    encoded = base64.encodebytes(bytes(der)).decode().strip()
    destination.write_text('-----BEGIN CERTIFICATE-----\n' + encoded +
                           '\n-----END CERTIFICATE-----\n')


def altered_crl(source, destination, expired):
    body = ''.join(line for line in source.read_text().splitlines()
                   if not line.startswith('-----'))
    der = bytearray(base64.b64decode(body))
    if expired:
        dates = list(re.finditer(rb'\d{12}Z', der))
        assert len(dates) >= 2, 'fixture CRL validity not encoded as UTC time'
        der[dates[1].start():dates[1].start()+2] = b'20'
    else:
        der[-1] ^= 1
    encoded = base64.encodebytes(bytes(der)).decode().strip()
    destination.write_text('-----BEGIN X509 CRL-----\n' + encoded +
                           '\n-----END X509 CRL-----\n')


def identity(root, username, port, client):
    return [client, 'pub', '--host', '127.0.0.1', '--port', str(port),
            '--ca', root / 'ca.crt', '--cert', root / 'client.crt',
            '--key', root / 'client.key', '--username', username,
            '--password-file', root.parent / 'password',
            '--topic', 'p100/value', '--message', username, '--qos', '1']


def attempt(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=10)


def wait_success(command):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        result = attempt(command)
        if result.returncode == 0:
            return
        time.sleep(.1)
    raise AssertionError('new TLS generation did not become available')


def switch(source, target, names):
    for name in names:
        shutil.copyfile(source / name, target / ('active-' + name))


def rotate(broker, log_path, accepted):
    previous = log_path.stat().st_size
    broker.send_signal(signal.SIGUSR1)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        events = log_path.read_bytes()[previous:].decode(errors='replace')
        if 'TLS rotation committed' in events:
            assert accepted, 'invalid TLS candidate was committed'
            return
        if 'TLS rotation rejected' in events:
            assert not accepted, 'valid TLS candidate was rejected'
            return
        assert broker.poll() is None, 'broker exited during TLS rotation'
        time.sleep(.02)
    raise AssertionError('TLS rotation signal was not processed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('broker', 'client', 'admin'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        'c27', ROOT.parent / 'xmqr-client/validation/C27-integration.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix='xmqr-p100-') as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        first, second = root / 'first', root / 'second'
        first.mkdir(); second.mkdir()
        fixture.certificates(first)
        fixture.certificates(second)
        crl(first, 'client.crl')
        crl(second, 'client.crl')
        crl(second, 'revoked.crl', revoked=True)
        expired_ca(second / 'ca.crt', second / 'expired-ca.crt')
        expired_ca(first / 'server.crt', first / 'expired-server.crt')
        altered_crl(second / 'client.crl', second / 'expired.crl', True)
        altered_crl(second / 'client.crl', second / 'bad-signature.crl', False)
        password = secrets.token_urlsafe(24)
        (root / 'password').write_text(password)
        (root / 'password').chmod(0o600)
        fingerprint = lambda directory: hashlib.sha256(
            ssl.PEM_cert_to_DER_cert((directory / 'client.crt').read_text())).hexdigest()
        digest = hash_fixture(args.admin, password)
        (root / 'users.toml').write_text(
            ''.join(f"[[users]]\nusername='{name}'\npassword_hash='{digest}'\n"
                    f"cert_sha256='sha256:{fingerprint(directory)}'\n"
                    for name, directory in [('old', first), ('new', second)]))
        (root / 'acl.toml').write_text(
            ''.join(f"[[rules]]\nusername='{name}'\npublish=['p100/value']\n"
                    "subscribe=['p100/#']\n" for name in ('old', 'new')))
        switch(first, root, ('server.crt', 'server.key', 'ca.crt', 'client.crl'))
        ports = [free_port(), free_port()]
        assert ports[0] != ports[1]
        (root / 'broker.toml').write_text(
            'version=1\n[broker]\nmode="secure-mtls"\n'
            f'bind="127.0.0.1:{ports[0]}"\n'
            f'additional_binds=["127.0.0.1:{ports[1]}"]\nstate_dir="state"\n'
            '[tls]\nserver_cert="active-server.crt"\nserver_key="active-server.key"\n'
            'client_ca="active-ca.crt"\nclient_crl="active-client.crl"\n'
            '[security]\nusers_file="users.toml"\nacl_file="acl.toml"\n')
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('MQTT_')}
        environment['MQTT_CONFIG'] = str(root / 'broker.toml')
        environment['RUST_LOG'] = 'info'
        old = identity(first, 'old', ports[0], args.client)
        new = identity(second, 'new', ports[1], args.client)
        with (root / 'broker.log').open('wb') as log:
            broker = subprocess.Popen([args.broker], env=environment, stdout=log, stderr=log)
            try:
                try:
                    for port in ports:
                        wait_port(broker, port)
                except AssertionError as error:
                    lines = (root / 'broker.log').read_text(errors='replace').splitlines()
                    last = lines[-1].replace(str(root), '<temporary>') if lines else 'no broker diagnostic'
                    raise AssertionError(f'{error}: {last}') from error
                assert attempt(old).returncode == 0, 'old identity failed at startup'
                assert attempt(new).returncode != 0, 'new CA accepted before rotation'
                subscriber = subprocess.Popen(
                    [args.client, 'sub', '--host', '127.0.0.1', '--port', str(ports[0]),
                     '--ca', first / 'ca.crt', '--cert', first / 'client.crt',
                     '--key', first / 'client.key', '--username', 'old',
                     '--password-file', root / 'password', '--topic', 'p100/#',
                     '--count', '1', '--output', 'jsonl', '--client-id', 'p100-old-sub'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    wait_subscription(subscriber)
                    for invalid in ('expired-server.crt', 'malformed-server.crt'):
                        if invalid == 'malformed-server.crt':
                            (root / 'active-server.crt').write_text('invalid-pem')
                        else:
                            shutil.copyfile(first / invalid, root / 'active-server.crt')
                        rotate(broker, root / 'broker.log', False)
                        assert attempt(old).returncode == 0, f'{invalid} replaced old generation'
                    shutil.copyfile(first / 'server.crt', root / 'active-server.crt')
                    (root / 'active-server.key').write_text('invalid-key')
                    rotate(broker, root / 'broker.log', False)
                    assert attempt(old).returncode == 0, 'bad key replaced old generation'
                    shutil.copyfile(first / 'server.key', root / 'active-server.key')
                    shutil.copyfile(second / 'client.crl', root / 'active-client.crl')
                    rotate(broker, root / 'broker.log', False)
                    assert attempt(old).returncode == 0, 'CRL from another CA replaced old generation'
                    switch(second, root, ('server.crt', 'server.key', 'ca.crt', 'client.crl'))
                    rotate(broker, root / 'broker.log', True)
                    wait_success(new)
                    assert attempt(old).returncode != 0, 'old CA trusted after rotation'
                    out, err = subscriber.communicate(timeout=10)
                    assert subscriber.returncode == 0, err
                    assert 'p100/value' in out, 'pre-rotation connection did not survive'
                    print('PASS: invalid key rollback, cert/CA/CRL rotation on both endpoints, active session survives')
                finally:
                    if subscriber.poll() is None:
                        subscriber.kill(); subscriber.communicate(timeout=3)
                shutil.copyfile(second / 'expired-ca.crt', root / 'active-ca.crt')
                rotate(broker, root / 'broker.log', False)
                assert attempt(new).returncode == 0, 'expired CA replaced valid generation'
                shutil.copyfile(second / 'ca.crt', root / 'active-ca.crt')
                for invalid in ('expired.crl', 'bad-signature.crl'):
                    shutil.copyfile(second / invalid, root / 'active-client.crl')
                    rotate(broker, root / 'broker.log', False)
                    assert attempt(new).returncode == 0, f'{invalid} replaced valid generation'
                shutil.copyfile(second / 'revoked.crl', root / 'active-client.crl')
                rotate(broker, root / 'broker.log', True)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and attempt(new).returncode == 0:
                    time.sleep(.1)
                assert attempt(new).returncode != 0, 'revoked client accepted'
                shutil.copyfile(second / 'client.crl', root / 'active-client.crl')
                rotate(broker, root / 'broker.log', True)
                wait_success(new)
                print('PASS: expired CA rejected, CRL revocation and rollback')
            finally:
                if broker.poll() is None:
                    broker.terminate()
                    assert broker.wait(timeout=12) == 0


if __name__ == '__main__':
    main()
