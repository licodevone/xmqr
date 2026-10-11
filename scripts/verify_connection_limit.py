#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P54: real TCP admission, MQTT connection and permit release, isolated state."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--broker', required=True)
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix='xmqr-p54-') as temporary:
    root = Path(temporary)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    config = root / 'broker.toml'
    config.write_text(f'version=1\n[broker]\nmode="open-lab"\nbind="127.0.0.1:{port}"\nstate_dir="state"\n[limits]\nmax_connections=1\n')
    environment = {k: v for k, v in os.environ.items() if not k.startswith('MQTT_')}
    environment['MQTT_CONFIG'] = str(config)
    with (root / 'log').open('wb') as log:
        process = subprocess.Popen([args.broker], env=environment, stdout=log, stderr=log)
        clients = []
        try:
            def connect():
                connection = socket.create_connection(('127.0.0.1', port), timeout=1)
                clients.append(connection)
                # MQTT3.1.1 CONNECT, clean session, keepalive60, client id p54.
                connection.sendall(b'\x10\x0f\x00\x04MQTT\x04\x02\x00\x3c\x00\x03p54')
                assert connection.recv(4) == b'\x20\x02\x00\x00'
                return connection
            deadline = time.monotonic() + 10
            while True:
                try:
                    first = connect()
                    break
                except (OSError, AssertionError):
                    assert process.poll() is None
                    assert time.monotonic() < deadline
                    time.sleep(0.05)
            with socket.create_connection(('127.0.0.1', port), timeout=1) as second:
                try:
                    assert second.recv(1) == b''
                except ConnectionResetError:
                    pass
            first.sendall(b'\xe0\x00')
            first.close()
            deadline = time.monotonic() + 3
            while True:
                try:
                    third = connect()
                    third.sendall(b'\xe0\x00')
                    break
                except (OSError, AssertionError):
                    assert time.monotonic() < deadline
                    time.sleep(0.05)
            print('PASS: limit1 rejects second connection and releases admission slot')
        finally:
            for connection in clients:
                connection.close()
            process.terminate()
            assert process.wait(timeout=20) == 0
