#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P234: servidores sintéticos WS/WSS isolados, sem broker instalado."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import time

from verify_phase6_vbi import frame, text
from verify_wss_mtls import certificates


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def exact(stream, length):
    result = bytearray()
    while len(result) < length:
        part = stream.recv(length - len(result))
        if not part:
            raise EOFError('peer closed')
        result.extend(part)
    return bytes(result)


def receive_frame(stream):
    first, second = exact(stream, 2)
    assert not first & 0x70, 'unexpected RSV bits'
    assert second & 0x80, 'client frame must be masked'
    length = second & 127
    if length == 126:
        length = int.from_bytes(exact(stream, 2), 'big')
    elif length == 127:
        length = int.from_bytes(exact(stream, 8), 'big')
    assert length <= 4096, 'synthetic peer frame limit'
    mask = exact(stream, 4)
    body = exact(stream, length)
    return first & 15, bytes(value ^ mask[index % 4]
                             for index, value in enumerate(body))


def send_frame(stream, opcode, body, *, final=True):
    assert len(body) < 126
    stream.sendall(bytes([(0x80 if final else 0) | opcode, len(body)]) + body)


def handshake(stream):
    request = bytearray()
    while not request.endswith(b'\r\n\r\n'):
        request.extend(exact(stream, 1))
        assert len(request) <= 4096
    assert request.startswith(b'GET /mqtt HTTP/1.1\r\n')
    request = bytes(request)
    headers = dict(line.split(b':', 1) for line in request.lower().split(b'\r\n')[1:]
                   if b':' in line)
    assert headers[b'sec-websocket-protocol'].strip() == b'mqtt'
    # O valor da chave diferencia maiúsculas; o nome do campo HTTP não.
    key = next(line.split(b':', 1)[1].strip() for line in request.split(b'\r\n')
               if line.lower().startswith(b'sec-websocket-key:'))
    accept = base64.b64encode(hashlib.sha1(
        key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
    stream.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n'
                   b'Connection: Upgrade\r\nSec-WebSocket-Protocol: mqtt\r\n'
                   b'Sec-WebSocket-Accept: ' + accept + b'\r\n\r\n')


class Packets:
    def __init__(self, stream):
        self.stream = stream
        self.pending = bytearray()

    def next(self):
        while True:
            if len(self.pending) >= 2:
                length, multiplier, index = 0, 1, 1
                while index < len(self.pending):
                    value = self.pending[index]
                    length += (value & 127) * multiplier
                    index += 1
                    if not value & 128:
                        if len(self.pending) >= index + length:
                            result = self.pending[0], bytes(self.pending[index:index + length])
                            del self.pending[:index + length]
                            return result
                        break
                    multiplier *= 128
                    assert index <= 4
            opcode, body = receive_frame(self.stream)
            if opcode == 9:
                send_frame(self.stream, 10, body)
                continue
            assert opcode in (0, 2), 'MQTT client emitted non-binary data'
            self.pending.extend(body)


def case(binary, root, version, secure, mode):
    with socket.socket() as listener, tempfile.TemporaryFile(dir=root) as output, \
            tempfile.TemporaryFile(dir=root) as errors:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(5)
        url = f'{"wss" if secure else "ws"}://127.0.0.1:{listener.getsockname()[1]}/mqtt'
        arguments = [str(binary), 'sub', '--ws-url', url, '--protocol-version', version,
                     '--topic', 'p234/topic', '--client-id', 'p234-private', '--count', '1',
                     '--qos', '0', '--output', 'jsonl', '--timeout-seconds', '3',
                     '--total-timeout-seconds', '8']
        if secure:
            arguments += ['--username', 'synthetic-device', '--password-file', str(root / 'password'),
                          '--ca', str(root / 'ca.crt'), '--cert', str(root / 'client.crt'),
                          '--key', str(root / 'client.key')]
        else:
            arguments += ['--open-lab']
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(('MQTT_', 'XMQR_'))}
        process = subprocess.Popen(arguments, stdout=output, stderr=errors, env=environment)
        try:
            stream, _ = listener.accept()
            stream.settimeout(2.5)
            if secure:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(root / 'server.crt', root / 'server.key')
                context.load_verify_locations(root / 'ca.crt')
                context.verify_mode = ssl.CERT_REQUIRED
                stream = context.wrap_socket(stream, server_side=True)
            with stream:
                handshake(stream)
                packets = Packets(stream)
                assert packets.next()[0] == 0x10, 'missing binary CONNECT'
                connack = frame(0x20, b'\0\0\0' if version == '5' else b'\0\0')
                if mode == 'text-connack':
                    send_frame(stream, 1, connack)
                else:
                    send_frame(stream, 2, connack[:2], final=False)
                    send_frame(stream, 0, connack[2:])
                    header, subscribe = packets.next()
                    assert header == 0x82, 'missing binary SUBSCRIBE'
                    suback = frame(0x90, subscribe[:2] + (b'\0' if version == '5' else b'') + b'\0')
                    publish = frame(0x30, text(b'p234/topic') +
                                    (b'\0' if version == '5' else b'') + b'ws-binary-control')
                    if mode == 'binary':
                        send_frame(stream, 2, suback + publish)
                        header, body = packets.next()
                        if header == 0xa2:
                            send_frame(stream, 2, frame(0xb0, body[:2] +
                                       (b'\0\0' if version == '5' else b'')))
                            header, _ = packets.next()
                        assert header == 0xe0, 'missing normal MQTT DISCONNECT'
                    else:
                        send_frame(stream, 2, suback)
                        send_frame(stream, 1, publish)
                if mode != 'binary':
                    started = time.monotonic()
                    try:
                        opcode, close = receive_frame(stream)
                        assert opcode == 8, 'text frame produced an MQTT flow instead of closure'
                        send_frame(stream, 8, close)
                    except (EOFError, ConnectionResetError):
                        pass
                    assert time.monotonic() - started < 2.5, 'closure waited for command timeout'
            code = process.wait(timeout=4)
            output.seek(0)
            observed = output.read()
            if mode == 'binary':
                rows = [json.loads(line) for line in observed.splitlines() if line.strip()]
                assert code == 0 and len(rows) == 1, 'controle binário não produziu uma publicação'
                assert rows[0]['topic'] == 'p234/topic'
                assert bytes(rows[0]['payload_bytes']) == b'ws-binary-control'
            else:
                assert code > 0 and not observed.strip(), 'texto produziu sucesso ou entrega à aplicação'
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--client-source-commit', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and a new exclusive report are required')
    if not re.fullmatch('[0-9a-f]{40}', args.client_source_commit):
        parser.error('explicit full client commit required')
    binary = args.client.resolve(strict=True)
    before = digest(binary)
    report = dict(schema_version=1, audit='P234', binary_sha256=before,
                  client_source_commit=args.client_source_commit, scenarios=[],
                  fixture_sha256=digest(Path(__file__)),
                  certificate_helper_sha256=digest(Path(__file__).with_name('verify_wss_mtls.py')))
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='xmqr-p234-', dir='/var/tmp') as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        certificates(root)
        (root / 'password').write_text('synthetic-private-only\n')
        for path in root.glob('*.key'):
            path.chmod(0o600)
        (root / 'password').chmod(0o600)
        for version in ('3.1.1', '5'):
            for secure in (False, True):
                for mode in ('binary', 'text-connack', 'text-publish'):
                    row = dict(protocol=version, transport='wss-mtls' if secure else 'ws', mode=mode)
                    try:
                        case(binary, root, version, secure, mode)
                        row['status'] = 'PASS'
                    except Exception as error:
                        row.update(status='FAIL', error_type=type(error).__name__, reason=str(error)[:200])
                    report['scenarios'].append(row)
    report['binary_unchanged'] = digest(binary) == before
    report['counts'] = {status: sum(row['status'] == status for row in report['scenarios'])
                        for status in ('PASS', 'FAIL')}
    report['status'] = 'PASS' if report['counts']['FAIL'] == 0 and report['binary_unchanged'] else 'FAIL'
    report['elapsed_seconds'] = round(time.monotonic() - began, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as destination:
        json.dump(report, destination, indent=2)
        destination.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'counts', 'elapsed_seconds')}))
    return int(report['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
