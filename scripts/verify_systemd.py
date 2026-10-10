#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Root-only isolated systemd units with real secure-mtls broker/client.

Never install packages or touch existing XMQR units/configuration/state.
"""
import argparse
import grp
import hashlib
import importlib.util
import os
from pathlib import Path
import pwd
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import uuid

sys.dont_write_bytecode = True


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=30)


def wait_for(predicate):
    end = time.monotonic() + 12
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.1)
    raise AssertionError('systemd test readiness deadline')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--hash-fixture', type=Path, required=True)
    parser.add_argument('--test-user', required=True, help='existing unprivileged Linux account')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('requires root on an active systemd host')
    repo = Path(__file__).resolve().parents[1]
    client_repo = repo.parent / 'xmqr-client'
    broker = repo / 'target/release/mqtt-broker'
    client = args.client.resolve()
    assert broker.is_file() and client.is_file()
    spec = importlib.util.spec_from_file_location('c27', client_repo / 'validation/C27-integration.py')
    c27 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c27)
    name = 'xmqr-test-' + uuid.uuid4().hex[:10]
    broker_unit = name + '-broker.service'
    sub_template = name + '-sub@.service'
    pub_template = name + '-pub@.service'
    sub_unit = sub_template.replace('@.', '@sub.')
    pub_unit = pub_template.replace('@.', '@pub.')
    unit_paths = []
    account = pwd.getpwnam(args.test_user)
    assert account.pw_uid != 0
    group = grp.getgrgid(account.pw_gid).gr_name
    state = Path('/var/lib') / name
    try:
        with tempfile.TemporaryDirectory(prefix=name + '-', dir='/run') as temp:
            root = Path(temp)
            root.chmod(0o755)
            c27.certificates(root)
            secret = 'fixture-pass'  # Public test fixture, never production credentials.
            password_hash = command(str(args.hash_fixture.resolve())).strip()
            der = ssl.PEM_cert_to_DER_cert((root / 'client.crt').read_text())
            fingerprint = hashlib.sha256(der).hexdigest()
            bundle = root / 'security.toml'
            bundle.write_text(f"version=1\n[[users]]\nusername='fixture-device'\npassword_hash='{password_hash}'\ncert_sha256='sha256:{fingerprint}'\npublish=['sensor/value']\nsubscribe=['sensor/#']\n")
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            environment = root / 'broker.env'
            environment.write_text(f'MQTT_MODE=secure-mtls\nMQTT_BIND=127.0.0.1:{port}\nMQTT_STATE_DIR={state}\nMQTT_SERVER_CERT={root}/server.crt\nMQTT_SERVER_KEY={root}/server.key\nMQTT_CLIENT_CA={root}/ca.crt\nMQTT_SECURITY_BUNDLE={bundle}\nRUST_LOG=info\n')
            configs = root / 'clients'
            configs.mkdir(mode=0o755)
            for instance in ('sub', 'pub'):
                directory = configs / instance
                directory.mkdir(mode=0o755)
                for file in ('ca.crt', 'client.crt', 'client.key'):
                    shutil.copyfile(root / file, directory / file)
                (directory / 'password').write_text(secret)
                (directory / 'payload.bin').write_bytes(b'systemd-fixture')
                (configs / (instance + '.conf')).write_text(f'HOST=127.0.0.1\nPORT={port}\nTOPIC={"sensor/#" if instance == "sub" else "sensor/value"}\nUSERNAME=fixture-device\nCLIENT_ID={name[-10:]}-{instance}\nQOS=1\n')
                for file in directory.iterdir():
                    file.chmod(0o600)
                    os.chown(file, account.pw_uid, account.pw_gid)
            for file in (bundle, root / 'server.key'):
                file.chmod(0o600)
                os.chown(file, account.pw_uid, account.pw_gid)
            for file in (root / 'server.crt', root / 'ca.crt'):
                file.chmod(0o644)
            templates = [
                (repo / 'packaging/systemd/xmqr-broker.service', broker_unit),
                (client_repo / 'packaging/systemd/xmqr-client-sub@.service', sub_template),
                (client_repo / 'packaging/systemd/xmqr-client-pub@.service', pub_template),
            ]
            for source, target in templates:
                text = source.read_text().replace('User=xmqr-client', 'User=' + account.pw_name).replace('Group=xmqr-client', 'Group=' + group).replace('User=xmqr', 'User=' + account.pw_name).replace('Group=xmqr', 'Group=' + group)
                text = text.replace('/usr/bin/mqtt-broker', str(broker)).replace('/usr/bin/mqtt-client', str(client))
                text = text.replace('EnvironmentFile=/etc/xmqr/broker.env', f'EnvironmentFile={environment}')
                text = text.replace('/etc/xmqr-client', str(configs)).replace('StateDirectory=xmqr', 'StateDirectory=' + name)
                path = Path('/run/systemd/system') / target
                assert not path.exists()
                path.write_text(text)
                path.chmod(0o644)
                unit_paths.append(path)
            command('systemd-analyze', 'verify', *map(str, unit_paths))
            command('systemctl', 'daemon-reload')
            command('systemctl', 'start', broker_unit)
            wait_for(lambda: 'secure MQTT listener started' in command('journalctl', '-u', broker_unit, '--no-pager', '-o', 'cat'))
            command('systemctl', 'start', sub_unit)
            wait_for(lambda: 'Assinatura ativa' in command('journalctl', '-u', sub_unit, '--no-pager', '-o', 'cat'))
            command('systemctl', 'start', pub_unit)
            wait_for(lambda: 'publish_complete' in command('journalctl', '-u', pub_unit, '--no-pager', '-o', 'cat'))
            wait_for(lambda: '"event":"publish"' in command('journalctl', '-u', sub_unit, '--no-pager', '-o', 'cat'))
            command('systemctl', 'reload', broker_unit)
            time.sleep(.5)
            assert command('systemctl', 'is-active', broker_unit).strip() == 'active'
            command('systemctl', 'restart', broker_unit)
            command('systemctl', 'stop', sub_unit, broker_unit)
            assert 'durable broker shutdown complete' in command('journalctl', '-u', broker_unit, '--no-pager', '-o', 'cat')
            assert (state / 'state.snapshot').exists()
            assert command('systemctl', 'show', sub_unit, '--property=ExecMainStatus', '--value').strip() == '0'
            print('SYSTEMD_MTLS_START_PUB_SUB_RELOAD_RESTART_STOP_PASS')
    finally:
        for unit in (sub_unit, pub_unit, broker_unit):
            subprocess.run(['systemctl', 'stop', unit], capture_output=True, timeout=25)
            subprocess.run(['systemctl', 'reset-failed', unit], capture_output=True, timeout=10)
        for path in unit_paths:
            path.unlink(missing_ok=True)
        command('systemctl', 'daemon-reload')
        if state.exists():
            assert state.parent == Path('/var/lib') and state.name == name
            shutil.rmtree(state)


if __name__ == '__main__':
    main()
