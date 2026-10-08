# SPDX-License-Identifier: MIT
"""P44 bounded byte fixtures; isolated Linux state and public test credentials."""
import argparse
import importlib.util
import os
from pathlib import Path
import queue
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('fixtures', Path(__file__).parent / 'verify_interop.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
BROKER = HASH = NEW_HASH = None


def bundle(removed=False, grants=True, disabled=False):
    users = '' if removed else f"""[[users]]
username='fixture-device'
password_hash='{HASH}'
disabled={str(disabled).lower()}
groups=['devices']
"""
    return ("version=1\n" + ('users=[]\n' if removed else '') +
            "[[roles]]\nname='writer'\npublish=" + ("['sensor/value','status/device']" if grants else '[]') +
            "\nsubscribe=" + ("['sensor/#','status/#']" if grants else '[]') +
            "\n[[groups]]\nname='devices'\nroles=['writer']\n" + users)


class Broker(f.Broker):
    def __init__(self, root):
        super().__init__(root)
        self.policy = self.root / 'private.toml'
        self.logs = []
        self.events = queue.Queue()
        self.write(bundle())

    def write(self, text):
        temporary = self.policy.with_suffix('.new')
        with open(temporary, 'w') as file:
            os.chmod(temporary, 0o600)
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, self.policy)

    def start(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('MQTT_')}
        env.update(MQTT_MODE='acl-lab', MQTT_BIND=f'127.0.0.1:{self.port}',
                   MQTT_STATE_DIR=str(self.state), MQTT_SECURITY_BUNDLE=str(self.policy), RUST_LOG='info')
        self.events = queue.Queue()
        self.process = subprocess.Popen([BROKER], env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True)
        def read():
            for line in self.process.stdout:
                line = re.sub(r'\[[0-9;]*m', '', line)
                self.logs.append(line)
                self.events.put(line)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        until = time.monotonic() + f.TIMEOUT
        while time.monotonic() < until:
            if self.process.poll() is not None:
                raise AssertionError('fixture broker failed startup')
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=.1):
                    return
            except OSError:
                time.sleep(.02)
        raise AssertionError('fixture readiness timeout')

    def stop(self, graceful=False):
        if self.process:
            if self.process.poll() is None:
                self.process.send_signal(signal.SIGTERM if graceful else signal.SIGKILL)
            self.process.wait(timeout=f.TIMEOUT)
            self.reader.join(timeout=f.TIMEOUT)
            self.process.stdout.close()
            self.process = None

    def reload(self, text, valid=True):
        self.write(text)
        self.process.send_signal(signal.SIGHUP)
        wanted = 'security reload committed' if valid else 'security reload rejected'
        until = time.monotonic() + f.TIMEOUT
        while time.monotonic() < until:
            if wanted in self.events.get(timeout=max(.01, until-time.monotonic())):
                return
        raise AssertionError('reload deadline')


class Client(f.WireClient):
    def __init__(self, broker, cid, clean=True, username='fixture-device', password=b'fixture-pass', will=False):
        self.socket = socket.create_connection(('127.0.0.1', broker.port), timeout=f.TIMEOUT)
        flags = 0xc0 | (2 if clean else 0) | (0x2c if will else 0)
        body = f.text('MQTT') + bytes([4, flags]) + struct.pack('!H', 30) + f.text(cid)
        if will:
            body += f.text('status/device') + f.text('fixture-will-payload')
        body += f.text(username) + struct.pack('!H', len(password)) + password
        self.send(0x10, body)
        self.connack = self.receive()


def publish(client, topic='sensor/value', payload=b'fixture-payload', qos=1, retain=True, identifier=7):
    packet_id = identifier.to_bytes(2, 'big')
    client.send(0x30 | (qos << 1) | int(retain), f.text(topic) + (packet_id if qos else b'') + payload)
    if qos:
        assert client.receive() == (0x40 if qos == 1 else 0x50, packet_id)


def publication(client):
    header, body = client.receive()
    assert header >> 4 == 3
    length = int.from_bytes(body[:2], 'big')
    topic, offset = body[2:2+length].decode(), 2+length
    if (header >> 1) & 3:
        client.send(0x40, body[offset:offset+2])
        offset += 2
    return topic, body[offset:], bool(header & 1)


class DynamicSecurity(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='xmqr-p44-')
        self.broker = Broker(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.broker.stop)
        self.broker.start()

    def client(self, cid, **kwargs):
        client = Client(self.broker, cid, **kwargs)
        self.addCleanup(client.close)
        return client

    def closed(self, client):
        self.assertEqual(client.socket.recv(1), b'')

    def silent(self, client):
        client.socket.settimeout(.2)
        with self.assertRaises(socket.timeout):
            client.receive()
        client.socket.settimeout(f.TIMEOUT)

    def test_invalid_auth_and_acl(self):
        for arguments in ({'password': b'wrong'}, {'username': 'unknown'}):
            self.assertEqual(self.client('denied', **arguments).connack, (0x20, b'\0\5'))
        source = self.client('source')
        self.assertEqual(source.subscribe([('#', 1)]), (0x90, b'\0\1\x80'))
        source.send(0x30, f.text('forbidden') + b'fixture-payload')
        self.closed(source)

    def test_invalid_reload_preserves_live_connection_and_generation(self):
        source = self.client('source')
        self.broker.reload('version=2\nusers=[]\n', valid=False)
        source.ping()
        publish(source)
        self.broker.reload(bundle())
        self.closed(source)
        self.assertTrue(any('generation=2' in line for line in self.broker.logs))

    def test_revocation_disconnects_and_filters_retained_offline(self):
        observer = self.client('observer', clean=False)
        self.assertEqual(observer.subscribe([('sensor/#', 1)]), (0x90, b'\0\1\1'))
        source = self.client('source')
        publish(source)
        self.assertEqual(publication(observer)[:2], ('sensor/value', b'fixture-payload'))
        self.broker.reload(bundle(grants=False))
        self.closed(source)
        self.closed(observer)
        resumed = self.client('observer', clean=False)
        self.assertEqual(resumed.connack, (0x20, b'\1\0'))
        self.assertEqual(resumed.subscribe([('sensor/#', 1)]), (0x90, b'\0\1\x80'))
        self.silent(resumed)
        self.broker.reload(bundle(disabled=True))
        self.closed(resumed)
        self.assertEqual(self.client('disabled').connack, (0x20, b'\0\5'))

    def test_password_rotation_requires_reauthentication(self):
        source = self.client('source')
        self.broker.reload(bundle().replace(HASH, NEW_HASH))
        self.closed(source)
        self.assertEqual(self.client('old-password').connack, (0x20, b'\0\5'))
        replacement = self.client('new-password', password=b'fixture-new-pass')
        self.assertEqual(replacement.connack, (0x20, b'\0\0'))
        publish(replacement)

    def test_revoked_offline_queue_is_removed(self):
        observer = self.client('observer', clean=False)
        observer.subscribe([('sensor/#', 1)])
        observer.send(0xe0)
        self.closed(observer)
        source = self.client('source')
        publish(source, retain=False)
        self.broker.reload(bundle(grants=False))
        self.closed(source)
        resumed = self.client('observer', clean=False)
        self.assertEqual(resumed.connack, (0x20, b'\1\0'))
        self.silent(resumed)
        self.broker.reload(bundle())
        again = self.client('observer', clean=False)
        self.silent(again)

    def test_revoked_will_is_discarded_durably(self):
        source = self.client('source', will=True)
        self.broker.reload(bundle(grants=False))
        self.closed(source)
        self.broker.stop(graceful=True)
        self.broker.start()
        self.broker.reload(bundle())
        observer = self.client('observer')
        observer.subscribe([('status/#', 1)])
        self.silent(observer)

    def test_allowed_will_offline_retained_exactly_once(self):
        observer = self.client('observer', clean=False)
        observer.subscribe([('status/#', 1)])
        source = self.client('source', will=True)
        self.broker.reload(bundle())
        self.closed(source)
        self.closed(observer)
        resumed = self.client('observer', clean=False)
        self.assertEqual(publication(resumed)[:2], ('status/device', b'fixture-will-payload'))
        self.silent(resumed)
        late = self.client('late')
        late.subscribe([('status/#', 1)])
        self.assertEqual(publication(late), ('status/device', b'fixture-will-payload', True))
        self.broker.reload(bundle())
        self.broker.stop(graceful=True)
        self.broker.start()
        again = self.client('observer', clean=False)
        self.silent(again)

    def test_qos2_ownership_survives_removal_restart_and_reactivation(self):
        source = self.client('source', clean=False)
        publish(source, qos=2)
        self.broker.reload(bundle(removed=True))
        self.closed(source)
        self.assertEqual(self.client('source', clean=False).connack, (0x20, b'\0\5'))
        self.broker.stop()
        self.broker.start()
        self.broker.reload(bundle())
        observer = self.client('observer')
        observer.subscribe([('sensor/#', 1)])
        resumed = self.client('source', clean=False)
        self.assertEqual(resumed.connack, (0x20, b'\1\0'))
        resumed.send(0x62, b'\0\7')
        self.assertEqual(resumed.receive(), (0x70, b'\0\7'))
        self.assertEqual(publication(observer)[:2], ('sensor/value', b'fixture-payload'))
        resumed.send(0x62, b'\0\7')
        self.assertEqual(resumed.receive(), (0x70, b'\0\7'))
        self.silent(observer)

    def test_startup_rejects_modes_conflicts_permissions_and_schema(self):
        self.broker.stop()
        for mode, legacy, content, permissions in [
            ('open-lab', False, bundle(), 0o600),
            ('password-lab', False, bundle(), 0o600),
            ('acl-lab', True, bundle(), 0o600),
            ('acl-lab', False, bundle(), 0o644),
            ('acl-lab', False, 'version=2\nusers=[]\n', 0o600),
        ]:
            self.broker.write(content)
            os.chmod(self.broker.policy, permissions)
            env = {k: v for k, v in os.environ.items() if not k.startswith('MQTT_')}
            env.update(MQTT_MODE=mode, MQTT_SECURITY_BUNDLE=str(self.broker.policy),
                       MQTT_BIND=f'127.0.0.1:{self.broker.port}', MQTT_STATE_DIR=str(self.broker.state))
            if legacy:
                env['MQTT_USERS_FILE'] = str(self.broker.policy)
            result = subprocess.run([BROKER], env=env, capture_output=True, timeout=f.TIMEOUT)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(HASH.encode(), result.stdout + result.stderr)

        self.broker.policy.unlink()
        os.mkfifo(self.broker.policy, 0o600)
        env = {k: v for k, v in os.environ.items() if not k.startswith('MQTT_')}
        env.update(MQTT_MODE='acl-lab', MQTT_SECURITY_BUNDLE=str(self.broker.policy),
                   MQTT_BIND=f'127.0.0.1:{self.broker.port}', MQTT_STATE_DIR=str(self.broker.state))
        result = subprocess.run([BROKER], env=env, capture_output=True, timeout=f.TIMEOUT)
        self.assertNotEqual(result.returncode, 0)

    def tearDown(self):
        self.broker.stop(graceful=True)
        audit = ''.join(self.broker.logs)
        for secret in ('fixture-device', 'fixture-pass', 'fixture-new-pass', HASH, NEW_HASH, 'fixture-payload', 'status/device', str(self.broker.policy)):
            self.assertNotIn(secret, audit)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker', required=True)
    parser.add_argument('--hash-fixture', required=True)
    arguments = parser.parse_args()
    BROKER = str(Path(arguments.broker).resolve())
    HASH = subprocess.check_output([arguments.hash_fixture], text=True, timeout=5).strip()
    NEW_HASH = subprocess.check_output([arguments.hash_fixture, 'rotated'], text=True, timeout=5).strip()
    unittest.main(argv=[sys.argv[0]], verbosity=2)
