#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P107 isolated Linux process check for the read-only Unix admin channel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time


def private(path, contents):
    path.write_text(contents, encoding='utf-8')
    path.chmod(0o600)


def request(path, token, operation='status', request_id='0123456789abcdef0123456789abcdef', **fields):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(3)
        connection.connect(str(path))
        message = dict(version=1, request_id=request_id,
                       operation=operation, token=token)
        message.update(fields)
        connection.sendall(json.dumps(message).encode() + b'\n')
        answer = bytearray()
        while True:
            block = connection.recv(1024)
            if not block:
                break
            answer.extend(block)
            if len(answer) > 16_384:
                raise AssertionError('response exceeds limit')
    return json.loads(answer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='xmqr-p107-') as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        state = root / 'state'
        state.mkdir(mode=0o700)
        policy = root / 'bundle.toml'
        private(policy, 'version=1\nusers=[]\n')
        viewer = root / 'view.token'
        operator = root / 'operator.token'
        private(viewer, 'a' * 64 + '\n')
        private(operator, 'b' * 64 + '\n')
        endpoint = root / 'admin.sock'
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        environment = {key: value for key, value in os.environ.items() if not key.startswith('MQTT_')}
        environment.update(MQTT_MODE='acl-lab', MQTT_BIND=f'127.0.0.1:{port}',
                           MQTT_STATE_DIR=str(state), MQTT_SECURITY_BUNDLE=str(policy),
                           MQTT_ADMIN_SOCKET=str(endpoint),
                           MQTT_ADMIN_VIEW_TOKEN_FILE=str(viewer),
                           MQTT_ADMIN_OPERATOR_TOKEN_FILE=str(operator), RUST_LOG='info')
        broker = subprocess.Popen([str(args.broker.resolve())], env=environment,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 8
            while not endpoint.exists():
                if broker.poll() is not None or time.monotonic() > deadline:
                    raise AssertionError('broker did not start admin socket')
                time.sleep(.02)
            assert endpoint.stat().st_mode & 0o777 == 0o600
            assert request(endpoint, 'a' * 64)['role'] == 'viewer'
            assert request(endpoint, 'b' * 64)['role'] == 'operator'
            assert request(endpoint, 'c' * 64)['error'] == 'unauthorized'
            digest = hashlib.sha256(policy.read_bytes()).hexdigest()
            mutation = dict(expected_generation=1, bundle_sha256=digest)
            target = 'fedcba9876543210fedcba9876543210'
            assert request(endpoint, 'a' * 64, 'reload', request_id=target, **mutation)['error'] == 'forbidden'
            applied = request(endpoint, 'b' * 64, 'reload', request_id=target, **mutation)
            assert applied['applied_generation'] == 2 and applied['replayed'] is False
            assert request(endpoint, 'b' * 64, 'reload', request_id=target, **mutation)['replayed'] is True
            receipt = request(endpoint, 'a' * 64, 'receipt', target_request_id=target)
            assert receipt['outcome'] == 'committed' and receipt['actor_uid'] == os.getuid()
            assert request(endpoint, 'b' * 64, 'reload', request_id=target,
                           expected_generation=1, bundle_sha256='0' * 64)['error'] == 'request_conflict'
            assert request(endpoint, 'b' * 64, 'reload', request_id='0' * 32,
                           **mutation)['error'] == 'stale_generation'
            with socket.socket(socket.AF_UNIX) as connection:
                connection.settimeout(3)
                connection.connect(str(endpoint))
                connection.sendall(b'x' * 20_000 + b'\n')
                try:
                    assert connection.recv(1) == b''
                except ConnectionResetError:
                    pass  # Linux may reset a socket closed with unread oversize bytes.
            broker.terminate()
            output, _ = broker.communicate(timeout=8)
            assert broker.returncode == 0
            assert not endpoint.exists()
            for secret in ('a' * 64, 'b' * 64, str(policy)):
                assert secret.encode() not in output
            restarted = subprocess.Popen([str(args.broker.resolve())], env=environment,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 8
                while not endpoint.exists():
                    if restarted.poll() is not None or time.monotonic() > deadline:
                        raise AssertionError('broker restart failed')
                    time.sleep(.02)
                assert request(endpoint, 'b' * 64, 'reload', request_id=target, **mutation)['replayed'] is True
                assert request(endpoint, 'a' * 64, 'receipt', target_request_id=target)['applied_generation'] == 2
            finally:
                restarted.terminate()
                restarted.communicate(timeout=8)
                assert not endpoint.exists()
            environment.pop('MQTT_SECURITY_BUNDLE')
            environment['MQTT_USERS_FILE'] = str(policy)
            environment['MQTT_ACL_FILE'] = str(policy)
            refused = subprocess.run([str(args.broker.resolve())], env=environment,
                                     capture_output=True, timeout=5)
            assert refused.returncode != 0
            assert not endpoint.exists()
            print('ADMIN_CHANNEL_RELOAD_PASS')
        finally:
            if broker.poll() is None:
                broker.kill()
                broker.communicate(timeout=5)


if __name__ == '__main__':
    main()
