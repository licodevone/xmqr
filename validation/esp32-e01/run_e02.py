#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P102: bounded physical ESP32 TLS rotation campaign on an isolated broker."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
import uuid

import serial
from run_initial import verified_backups, command
from sync_wifi import REPO, private_file, read_bounded

IMAGE = 'xmqr-broker:e02-p102'
OPENSSL = Path('C:/Program Files/Git/usr/bin/openssl.exe')
STAGES = (
    'INVALID_KEY_ROLLBACK', 'CERT_ROTATION', 'FOREIGN_CA_REJECTION',
    'CA_ROLLBACK', 'CRL_REVOCATION', 'CRL_ROLLBACK',
)


def save_report(root, report):
    name = f'e02-result-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}.json'
    with (root / name).open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)


def openssl(*args, cwd):
    result = subprocess.run([str(OPENSSL), *map(str, args)], cwd=cwd,
                            capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError('private OpenSSL fixture generation failed')


def docker(*args, timeout=30):
    return command(['docker', *map(str, args)], timeout=timeout)


def prepare(root, case, address):
    root = root.resolve(strict=True)
    certs = (root / 'certs').resolve(strict=True)
    active = case / 'active'
    active.mkdir()
    for name in ('server.crt', 'server.key', 'ca.crt', 'users.toml', 'acl.toml'):
        shutil.copyfile(private_file(certs, name), active / name)
    openssl('req', '-newkey', 'rsa:2048', '-nodes', '-sha256', '-subj', '/CN=XMQR E02 server',
            '-keyout', case / 'next.key', '-out', case / 'next.csr', cwd=case)
    openssl('x509', '-req', '-in', case / 'next.csr', '-CA', certs / 'ca.crt',
            '-CAkey', certs / 'ca.key', '-set_serial', '12345001', '-days', '2',
            '-sha256', '-extfile', certs / 'server.ext', '-out', case / 'next.crt', cwd=case)
    openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256', '-days', '2',
            '-subj', '/CN=XMQR E02 foreign CA', '-keyout', case / 'foreign-ca.key',
            '-out', case / 'foreign-ca.crt', cwd=case)
    openssl('x509', '-req', '-in', case / 'next.csr', '-CA', case / 'foreign-ca.crt',
            '-CAkey', case / 'foreign-ca.key', '-set_serial', '12345002', '-days', '2',
            '-sha256', '-extfile', certs / 'server.ext', '-out', case / 'foreign.crt', cwd=case)
    ca = case / 'ca'
    ca.mkdir()
    (ca / 'newcerts').mkdir()
    (ca / 'index').write_text('')
    (ca / 'serial').write_text('04\n')
    (ca / 'ca.cnf').write_text('[ca]\ndefault_ca=local\n[local]\n'
        f'database={(ca / "index").as_posix()}\nnew_certs_dir={(ca / "newcerts").as_posix()}\n'
        f'certificate={(certs / "ca.crt").as_posix()}\nprivate_key={(certs / "ca.key").as_posix()}\n'
        f'serial={(ca / "serial").as_posix()}\ndefault_md=sha256\ndefault_crl_days=1\n'
        'crl_extensions=crl_ext\n[crl_ext]\nauthorityKeyIdentifier=keyid:always\n')
    openssl('ca', '-config', ca / 'ca.cnf', '-gencrl', '-out', case / 'clean.crl',
            '-batch', cwd=ca)
    openssl('ca', '-config', ca / 'ca.cnf', '-revoke', certs / 'board.crt', '-batch', cwd=ca)
    openssl('ca', '-config', ca / 'ca.cnf', '-gencrl', '-out', case / 'revoked.crl',
            '-batch', cwd=ca)
    shutil.copyfile(case / 'clean.crl', active / 'client.crl')
    # Confirm SAN for the exact IP that the board dials; do not print PEM.
    cert = ssl._ssl._test_decode_cert(str(case / 'next.crt'))
    if ('IP Address', address) not in cert['subjectAltName']:
        raise ValueError('E02 server certificate has no board target IP SAN')
    return active


def rotate(name, accepted):
    before = subprocess.run(['docker', 'logs', name], capture_output=True, timeout=10)
    if before.returncode:
        raise ValueError('broker log unavailable')
    previous = before.stderr.count(b'TLS rotation committed') + before.stderr.count(b'TLS rotation rejected')
    docker('kill', '--signal=USR1', name)
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        output = subprocess.run(['docker', 'logs', name], capture_output=True, timeout=10)
        if output.returncode:
            raise ValueError('broker exited during rotation')
        data = output.stderr
        count = data.count(b'TLS rotation committed') + data.count(b'TLS rotation rejected')
        if count > previous:
            marker = b'TLS rotation committed' if accepted else b'TLS rotation rejected'
            if marker not in data[len(before.stderr):]:
                raise ValueError('unexpected TLS generation result')
            return
        time.sleep(.1)
    raise ValueError('broker did not acknowledge TLS rotation')


def action(stage, case, active, name):
    if stage == 'INVALID_KEY_ROLLBACK':
        (active / 'server.key').write_text('invalid-key')
        rotate(name, False)
        shutil.copyfile(case / 'original.key', active / 'server.key')
    elif stage == 'CERT_ROTATION':
        for source, target in (('next.crt', 'server.crt'), ('next.key', 'server.key')):
            shutil.copyfile(case / source, active / target)
        rotate(name, True)
    elif stage == 'FOREIGN_CA_REJECTION':
        shutil.copyfile(case / 'foreign.crt', active / 'server.crt')
        rotate(name, True)
    elif stage == 'CA_ROLLBACK':
        shutil.copyfile(case / 'next.crt', active / 'server.crt')
        rotate(name, True)
    elif stage == 'CRL_REVOCATION':
        shutil.copyfile(case / 'revoked.crl', active / 'client.crl')
        rotate(name, True)
    elif stage == 'CRL_ROLLBACK':
        shutil.copyfile(case / 'clean.crl', active / 'client.crl')
        rotate(name, True)
    else:
        raise ValueError('unexpected E02 stage')


def flash(root, port, case):
    outputs = [p for p in (root / 'target/xtensa-esp32-espidf/release/build').glob('esp-idf-sys-*/out')
               if (p / 'build/bootloader/bootloader.bin').is_file()]
    if len(outputs) != 1:
        raise ValueError('ambiguous SDK bootloader')
    firmware = root / 'target/xtensa-esp32-espidf/release/xmqr-esp32-e01'
    if not firmware.is_file():
        raise ValueError('E02 firmware binary missing')
    app = case / 'e02-app.bin'
    command([sys.executable, '-m', 'esptool', '--chip', 'esp32', 'elf2image',
             '--flash_mode', 'dio', '--flash_freq', '40m', '--flash_size', '4MB',
             '--elf-sha256-offset', '0xb0', '--output', str(app), str(firmware)])
    if app.stat().st_size > 1048576:
        raise ValueError('E02 app exceeds factory partition')
    sdk = outputs[0] / 'build'
    command([sys.executable, '-m', 'esptool', '--chip', 'esp32', '--port', port,
             '--baud', '115200', 'write_flash', '--flash_mode', 'dio',
             '--flash_freq', '40m', '--flash_size', '4MB',
             '0x1000', str(sdk / 'bootloader/bootloader.bin'),
             '0x8000', str(sdk / 'partition_table/partition-table.bin'),
             '0x10000', str(app)], timeout=240)
    return app.stat().st_size


def exercise(args):
    root = args.private_dir.resolve(strict=True)
    if root.is_relative_to(REPO) or not args.flash or args.serial_port != 'COM4':
        raise ValueError('E02 requires private lab, explicit flash and COM4')
    backup_hash = verified_backups(args.backup_dir.resolve(strict=True))
    info = subprocess.run([sys.executable, '-m', 'esptool', '--chip', 'esp32',
                           '--port', 'COM4', 'flash_id'], capture_output=True, timeout=20)
    if info.returncode or b'ESP32-D0WD-V3' not in info.stdout or b'4MB' not in info.stdout:
        raise ValueError('board identity/flash size precheck failed')
    config = json.loads(read_bounded(private_file(root, 'firmware-config.json')))
    url = urlsplit(config['mqtt_url'])
    if (url.scheme != 'mqtts' or url.hostname != '192.168.0.100'
            or url.username or not 1024 <= url.port <= 65535):
        raise ValueError('unexpected private broker target')
    with socket.socket() as probe:
        probe.bind((url.hostname, url.port))
    docker('image', 'inspect', IMAGE)
    report = {'schema': 1, 'prompt': 'P102', 'result': 'FAIL_PRECHECK',
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'port': 'COM4', 'backup_sha256': backup_hash,
              'flashed': False, 'markers': [], 'rotations': 0}
    token = secrets.token_hex(5)
    name, volume = f'xmqr-e02-p102-{token}', f'xmqr-e02-p102-{token}-state'
    volume_created = container_created = False
    try:
        with tempfile.TemporaryDirectory(prefix='e02-private-', dir=root) as temporary:
            report['stage'] = 'PREPARE_TLS'
            case = Path(temporary).resolve(strict=True)
            if case.parent != root:
                raise ValueError('E02 private case escaped selected directory')
            active = prepare(root, case, url.hostname)
            shutil.copyfile(active / 'server.key', case / 'original.key')
            report['stage'] = 'CREATE_VOLUME'
            docker('volume', 'create', volume); volume_created = True
            report['stage'] = 'PREPARE_VOLUME'
            docker('run', '--rm', '--user', '0:0', '--network', 'none',
                   '--mount', f'type=volume,source={volume},target=/var/lib/xmqr',
                   '--entrypoint', '/bin/sh', IMAGE, '-c', 'chown 10001:10001 /var/lib/xmqr')
            report['stage'] = 'CREATE_BROKER'
            docker('create', '--name', name, '--read-only', '--cap-drop', 'ALL',
                   '--security-opt', 'no-new-privileges', '--pids-limit', '64',
                   '--memory', '256m', '--publish', f'{url.hostname}:{url.port}:8883',
                   '--mount', f'type=bind,source={active},target=/run/e02,readonly',
                   '--mount', f'type=volume,source={volume},target=/var/lib/xmqr',
                   '--env', 'MQTT_SERVER_CERT=/run/e02/server.crt',
                   '--env', 'MQTT_SERVER_KEY=/run/e02/server.key',
                   '--env', 'MQTT_CLIENT_CA=/run/e02/ca.crt',
                   '--env', 'MQTT_CLIENT_CRL=/run/e02/client.crl',
                   '--env', 'MQTT_USERS_FILE=/run/e02/users.toml',
                   '--env', 'MQTT_ACL_FILE=/run/e02/acl.toml',
                   '--env', 'RUST_LOG=info', IMAGE)
            container_created = True
            report['stage'] = 'START_BROKER'
            docker('start', name)
            report['stage'] = 'READY_BROKER'
            context = ssl.create_default_context(cafile=str(active / 'ca.crt'))
            context.load_cert_chain(str(root / 'certs/board.crt'), str(root / 'certs/board.key'))
            deadline = time.monotonic() + 18
            while time.monotonic() < deadline:
                try:
                    with socket.create_connection((url.hostname, url.port), timeout=.5) as tcp:
                        with context.wrap_socket(tcp, server_hostname=url.hostname):
                            break
                except (OSError, ssl.SSLError):
                    time.sleep(.2)
            else:
                raise ValueError('isolated E02 broker mTLS precheck failed')
            report['result'] = 'FAIL_PHYSICAL'
            report['stage'] = 'FLASH'
            report['app_bytes'] = flash(root, args.serial_port, case)
            report['flashed'] = True
            print('E02_FLASH_VERIFIED', flush=True)
            expected = ['E02_BOOT fixture=0.1.0', 'E02_BASELINE_PASS']
            for stage in STAGES:
                expected.extend((f'E02_{stage}_READY', f'E02_{stage}_PASS'))
            expected.extend(('E02_PHYSICAL_PASS', 'E02_STOP'))
            index = 0
            report['stage'] = 'SERIAL_CAMPAIGN'
            deadline = time.monotonic() + 210
            total = 0
            with serial.Serial(args.serial_port, 115200, timeout=.2) as uart:
                uart.dtr = False; uart.rts = True; time.sleep(.1); uart.rts = False
                while time.monotonic() < deadline and index < len(expected):
                    raw = uart.readline()
                    total += len(raw)
                    if total > 65536 or len(raw) > 512:
                        raise ValueError('E02 UART budget exceeded')
                    try:
                        line = raw.decode('ascii').strip()
                    except UnicodeDecodeError:
                        continue
                    if line.startswith('E02_FAIL stage='):
                        raise ValueError(line if re.fullmatch(r'E02_FAIL stage=[A-Z0-9_]{1,40}', line)
                                         else 'E02 firmware failed')
                    if line == expected[index]:
                        report['markers'].append(line)
                        print(line, flush=True)
                        index += 1
                        if line.endswith('_READY'):
                            stage = line.removeprefix('E02_').removesuffix('_READY')
                            action(stage, case, active, name)
                            report['rotations'] += 1
            if index != len(expected):
                raise ValueError('E02 physical milestone sequence incomplete')
            report['result'] = 'PASS_PHYSICAL_CAMPAIGN'
            report['stage'] = 'COMPLETE'
            return report
    finally:
        if container_created:
            output = subprocess.run(['docker', 'logs', name], capture_output=True, timeout=10)
            if output.returncode == 0:
                tail = output.stderr.lower().splitlines()[-3:]
                joined = b' '.join(tail)
                if tail:
                    report['broker_error_redacted'] = re.sub(
                        rb'/run/e02/\S+', b'<tls-file>', tail[-1])[:300].decode(errors='replace')
                report['broker_error_class'] = next((label for label, token in (
                    ('CRL_ISSUER_SIGNATURE', b'issuer or signature'),
                    ('CRL_VALIDITY', b'crl validity period'),
                    ('CRL_PEM', b'crl pem'),
                    ('CRL_OTHER', b'crl'), ('CERTIFICATE', b'certificate'),
                    ('PERMISSION', b'permission denied'), ('STATE', b'state'),
                    ('ADDRESS', b'address'), ('OTHER', b'error:')) if token in joined), 'UNKNOWN')
            try: docker('stop', '--time', '10', name, timeout=25)
            except Exception: report['result'] = 'FAIL_CLEANUP'
            try: docker('rm', '-f', name)
            except Exception: pass  # --rm may have removed it already.
        if volume_created:
            try: docker('volume', 'rm', volume)
            except Exception: report['result'] = 'FAIL_CLEANUP'
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        save_report(root, report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-dir', type=Path, required=True)
    parser.add_argument('--backup-dir', type=Path, required=True)
    parser.add_argument('--serial-port', default='COM4')
    parser.add_argument('--flash', action='store_true')
    args = parser.parse_args()
    try:
        result = exercise(args)
        print('P102_RESULT ' + result['result'], flush=True)
        sys.exit(0 if result['result'] == 'PASS_PHYSICAL_CAMPAIGN' else 1)
    except Exception as error:
        message = str(error)
        if not re.fullmatch(r'E02_FAIL stage=[A-Z0-9_]{1,40}', message):
            message = 'P102_RUN_FAILED (private details suppressed)'
        print(message, file=sys.stderr, flush=True)
        sys.exit(1)
