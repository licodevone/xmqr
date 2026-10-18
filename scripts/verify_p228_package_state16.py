#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P228B: real package 042->043->backup15 rollback, owned Ubuntu26 container only."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import tomllib
import unittest
import zlib

RUNTIME_CHECKPOINT = 'ba6ef50204dec2c6385b272e595260b9def1e794'
OLD_DEB_SHA = '914d38e4fcd16b2d52a6a3e3e56710cc1371248976b9436c8b7570c04dc0e354'
STATE_FILES = ('state.snapshot', 'state.wal')
TOPIC = b'p228/state'
PAYLOAD = b'owned-p228-fixture'
SNAPSHOT_LIMIT = 2 * 1024 * 1024  # Bounded reader fixture, not a raised broker limit.


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def git_revision(value):
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise argparse.ArgumentTypeError('source must be an explicit lowercase Git SHA40')
    return value


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(*command, uid=None, gid=None, env=None, expected=0, timeout=240):
    options = {} if uid is None else dict(user=uid, group=gid)
    result = subprocess.run(list(map(str, command)), capture_output=True,
                            timeout=timeout, env=env, **options)
    if result.returncode != expected:
        raise RuntimeError(f'{Path(command[0]).name}: exit {result.returncode}')
    return result.stdout.decode().strip()


def state_hashes(directory):
    return {name: digest(directory / name) for name in STATE_FILES}


def snapshot_document(data):
    # Binary reader follows MQSNAP01/A21, independently of the broker encoder.
    require(26 <= len(data) <= SNAPSHOT_LIMIT, 'snapshot_size')
    magic, version, _, entries = struct.unpack_from('<8sHQI', data)
    require(magic == b'MQSNAP01' and version == 1 and entries <= 128, 'snapshot_header')
    end = len(data) - 4
    require(zlib.crc32(data[:end]) == int.from_bytes(data[end:], 'little'), 'snapshot_crc')
    cursor, values = 22, {}
    for _ in range(entries):
        require(cursor + 6 <= end, 'snapshot_entry_header')
        key_size, value_size = struct.unpack_from('<HI', data, cursor)
        cursor += 6
        require(1 <= key_size <= 1024 and value_size <= 1_048_576
                and cursor + key_size + value_size <= end, 'snapshot_entry_size')
        key = data[cursor:cursor + key_size]
        cursor += key_size
        require(key not in values, 'snapshot_duplicate_key')
        values[key] = data[cursor:cursor + value_size]
        cursor += value_size
    require(cursor == end and b'mqtt311.state.v1' in values, 'snapshot_entries')
    document = tomllib.loads(values[b'mqtt311.state.v1'].decode())
    require(isinstance(document.get('state'), dict), 'snapshot_state')
    return document


def document(directory):
    path = directory / 'state.snapshot'
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= SNAPSHOT_LIMIT,
            'snapshot_file')
    return snapshot_document(path.read_bytes())


def seeded_v15(directory):
    image = document(directory)
    require(image['version'] == 15, 'real_seeded_document15')
    state = image['state']
    message = state['retained'][TOPIC.decode()]
    require(message['topic'] == TOPIC.decode() and message['payload'] == PAYLOAD.hex()
            and message['qos'] == 1 and message['retain'], 'real_retained_document15')
    session = state['sessions']['p228-persistent']
    require(session['persistent'] and session['subscriptions'][TOPIC.decode()] == 1
            and len(session['offline']) == 1 and not session['outbound'],
            'real_persistent_offline_document15')
    queued = session['offline'][0]
    require(queued['topic'] == TOPIC.decode() and queued['payload'] == PAYLOAD.hex()
            and queued['qos'] == 1, 'real_offline_payload_document15')


def backup_manifest(directory):
    manifest = tomllib.loads((directory / 'manifest.toml').read_text())
    require(manifest['format_version'] == 1 and manifest['state_format_version'] == 1,
            'backup_format')
    require([entry['name'] for entry in manifest['files']] == list(STATE_FILES), 'backup_paths')
    require(sorted(path.name for path in directory.iterdir())
            == sorted((*STATE_FILES, 'manifest.toml')), 'backup_extra_files')
    require(directory.stat().st_mode & 0o777 == 0o700, 'backup_private_directory')
    for entry in manifest['files']:
        path = directory / entry['name']
        require(path.is_file() and not path.is_symlink(), 'backup_regular_file')
        require(path.stat().st_size == entry['length'] and digest(path) == entry['sha256'],
                'backup_hash')
    for name in (*STATE_FILES, 'manifest.toml'):
        require((directory / name).stat().st_mode & 0o777 == 0o600, 'backup_private_file')


def field(value):
    return len(value).to_bytes(2, 'big') + value


def send(peer, header, body):
    require(len(body) < 128, 'fixture_short_packet_bound')
    peer.sendall(bytes([header, len(body)]) + body)


def exact(peer, count):
    output = bytearray()
    while len(output) < count:
        chunk = peer.recv(count - len(output))
        require(bool(chunk), 'mqtt_eof')
        output.extend(chunk)
    return bytes(output)


def packet(peer):
    header = exact(peer, 1)[0]
    length, multiplier = 0, 1
    for _ in range(4):
        digit = exact(peer, 1)[0]
        length += (digit & 127) * multiplier
        require(length <= 65_536, 'mqtt_packet_bound')
        if digit < 128:
            return header, exact(peer, length)
        multiplier *= 128
    raise AssertionError('mqtt_remaining_length')


def connect(port, identity, clean=True):
    peer = socket.create_connection(('127.0.0.1', port), timeout=5)
    peer.settimeout(5)
    try:
        send(peer, 0x10, b'\0\x04MQTT\x04' + bytes([2 if clean else 0])
             + b'\0\x1e' + field(identity))
        header, body = packet(peer)
        require(header == 0x20 and body in (b'\0\0', b'\x01\0'), 'connack')
        return peer, body[0] == 1
    except BaseException:
        peer.close()
        raise


def disconnect(peer):
    try:
        peer.sendall(b'\xe0\0')
        peer.shutdown(socket.SHUT_WR)
        try:
            require(peer.recv(1) == b'', 'disconnect_server_eof')
        except ConnectionResetError:
            pass
    finally:
        peer.close()


def subscribe(peer):
    send(peer, 0x82, b'\0\x01' + field(TOPIC) + b'\x01')
    require(packet(peer) == (0x90, b'\0\x01\x01'), 'suback')


def publication(peer, retained):
    header, body = packet(peer)
    require(header >> 4 == 3 and (header >> 1) & 3 == 1, 'delivery_qos')
    require(bool(header & 1) == retained, 'delivery_retained')
    topic_size = int.from_bytes(body[:2], 'big')
    require(body[2:2 + topic_size] == TOPIC, 'delivery_topic')
    require(body[4 + topic_size:] == PAYLOAD, 'delivery_payload')
    packet_id = body[2 + topic_size:4 + topic_size]
    require(len(packet_id) == 2 and packet_id != b'\0\0', 'delivery_id')
    send(peer, 0x40, packet_id)


def environment(state, port):
    value = {key: item for key, item in os.environ.items() if not key.startswith('MQTT_')}
    value.update(MQTT_MODE='open-lab', MQTT_STATE_DIR=str(state),
                 MQTT_BIND=f'127.0.0.1:{port}', RUST_LOG='info', TMPDIR='/var/tmp')
    return value


@contextmanager
def broker(binary, state, uid, gid, logs):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    with logs.open('xb') as stream:
        os.chmod(logs, 0o600)
        process = subprocess.Popen([str(binary)], stdout=stream, stderr=stream,
                                   user=uid, group=gid, env=environment(state, port))
        try:
            deadline = time.monotonic() + 10
            while True:
                require(process.poll() is None, 'broker_startup_exit')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1):
                        break
                except OSError:
                    require(time.monotonic() < deadline, 'broker_startup_timeout')
                    time.sleep(.02)
            yield port
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    require(process.wait(timeout=20) == 0, 'broker_shutdown_exit')
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
        stream.flush()
    require(b'durable broker shutdown complete' in logs.read_bytes(), 'broker_durable_shutdown')


def seed(port):
    peer, resumed = connect(port, b'p228-persistent', clean=False)
    require(not resumed, 'new_session')
    subscribe(peer)
    disconnect(peer)
    peer, _ = connect(port, b'p228-publisher')
    send(peer, 0x33, field(TOPIC) + b'\0\x07' + PAYLOAD)
    require(packet(peer) == (0x40, b'\0\x07'), 'publish_ack')
    disconnect(peer)


def consume(port):
    peer, resumed = connect(port, b'p228-persistent', clean=False)
    require(resumed, 'persistent_resume')
    publication(peer, False)
    disconnect(peer)
    peer, _ = connect(port, b'p228-retained-observer')
    subscribe(peer)
    publication(peer, True)
    disconnect(peer)


def file_status(path):
    return digest(path), path.stat().st_mode & 0o777


def check_unit():
    run('systemd-analyze', 'verify', '/usr/lib/systemd/system/xmqr-broker.service')
    require(not Path('/etc/systemd/system/multi-user.target.wants/xmqr-broker.service').exists(),
            'no_service_autoenable')
    require(Path('/var/lib/xmqr').stat().st_mode & 0o777 == 0o700, 'state_directory_mode')


def lifecycle(args, report):
    import pwd
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines()
                   if '=' in line)
    require(Path('/.dockerenv').exists() and os.getuid() == 0, 'disposable_root_container')
    require(os.environ.get('XMQR_DISPOSABLE_PACKAGE_TEST') == '1', 'explicit_disposable_opt_in')
    require(release.get('ID', '').strip('"') == 'ubuntu'
            and release.get('VERSION_ID', '').strip('"') == '26.04', 'ubuntu26')
    require(run('dpkg', '--print-architecture') == 'amd64', 'native_amd64')
    require(digest(args.old_deb) == OLD_DEB_SHA, 'pinned_baseline_package')
    for package, version in ((args.old_deb, '0.42.0-1'), (args.new_deb, '0.43.0-1')):
        require(package.is_file() and not package.is_symlink(), 'package_file')
        require(run('dpkg-deb', '-f', package, 'Package') == 'xmqr-broker', 'package_name')
        require(run('dpkg-deb', '-f', package, 'Version') == version, 'package_version')
        require(run('dpkg-deb', '-f', package, 'Architecture') == 'amd64', 'package_arch')
    query = subprocess.run(['dpkg-query', '-W', '-f=${Status}', 'xmqr-broker'], capture_output=True)
    require(b'install ok installed' not in query.stdout, 'fresh_container_no_existing_package')
    Path('/etc/dpkg/dpkg.cfg.d/zz-xmqr-p228-docs').write_text(
        'path-include=/usr/share/doc/xmqr-broker\npath-include=/usr/share/doc/xmqr-broker/*\n')
    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
    run('apt-get', 'install', '-y', args.old_deb)
    require(run('/usr/bin/mqtt-broker', '--version') == 'mqtt-broker 0.42.0', 'installed042')
    require(run('/usr/bin/mqtt-admin', '--version') == 'mqtt-admin 0.42.0', 'installed_admin042')
    check_unit()
    account = pwd.getpwnam('xmqr')
    uid, gid = account.pw_uid, account.pw_gid
    with tempfile.TemporaryDirectory(prefix='xmqr-p228-owned-', dir='/var/tmp') as temporary:
        base = Path(temporary)
        os.chown(base, uid, gid)
        baseline = base / 'baseline-package'
        run('dpkg-deb', '--extract', args.old_deb, baseline)
        old_broker = baseline / 'usr/bin/mqtt-broker'
        old_admin = baseline / 'usr/bin/mqtt-admin'
        require(digest(old_broker) == digest('/usr/bin/mqtt-broker'), 'baseline_elf_identity')
        conffile = Path('/etc/xmqr/broker.env')
        with conffile.open('a') as stream:
            stream.write('\n# owned P228 operator edit\n')
        secret = Path('/etc/xmqr/p228/password')
        secret.parent.mkdir(mode=0o700)
        secret.write_bytes(b'owned-fixture-not-a-real-secret')
        secret.chmod(0o600)
        sentinel = Path('/var/lib/xmqr/p228-operator-data')
        sentinel.write_bytes(b'owned-operator-marker')
        sentinel.chmod(0o600)
        preserved = {str(path): file_status(path) for path in (conffile, secret, sentinel)}
        state = Path('/var/lib/xmqr/p228-live')
        state.mkdir(mode=0o700)
        os.chown(state, uid, gid)
        with broker('/usr/bin/mqtt-broker', state, uid, gid, base / 'old.log') as port:
            seed(port)
        seeded_v15(state)
        profile15 = base / 'original-profile15'
        profile15.write_bytes((state / '.mqtt-broker-profile').read_bytes())
        profile15.chmod(0o600)
        require(profile15.read_bytes() == b'open-lab\n', 'original_profile15')
        backup = base / 'backup15'
        run(old_admin, 'state', 'backup', '--state-dir', state, '--destination', backup,
            uid=uid, gid=gid)
        backup_manifest(backup)
        seeded_v15(backup)
        backup_hashes = state_hashes(backup)
        state15_hashes = state_hashes(state)
        report['stages'].append('install042_real_mqtt_retained_offline_private_backup15')
        run('apt-get', 'install', '-y', '-o', 'Dpkg::Options::=--force-confold', args.new_deb)
        require(run('/usr/bin/mqtt-broker', '--version') == 'mqtt-broker 0.43.0', 'installed043')
        require(run('/usr/bin/mqtt-admin', '--version') == 'mqtt-admin 0.43.0', 'installed_admin043')
        require(digest('/usr/bin/mqtt-broker') == args.new_broker_sha
                and digest('/usr/bin/mqtt-admin') == args.new_admin_sha, 'candidate_native_elf_identity')
        check_unit()
        require(state_hashes(state) == state15_hashes, 'package_upgrade_does_not_open_state')
        require(all(file_status(Path(path)) == value for path, value in preserved.items()),
                'upgrade_preserves_operator_files')
        with broker('/usr/bin/mqtt-broker', state, uid, gid, base / 'new.log') as port:
            consume(port)
        migrated = document(state)
        require(migrated['version'] == 16 and migrated['state']['expiry_clock_unix_ms'] > 0,
                'runtime_migrates_to_v16')
        state16_hashes = state_hashes(state)
        report['stages'].append('upgrade043_native_elf_units_no_autostart_migrates_and_replays')
        rejected = base / 'negative-v16-copy'
        shutil.copytree(state, rejected, symlinks=False)
        for path in [rejected, *rejected.iterdir()]:
            require(not path.is_symlink(), 'owned_copy_no_symlink')
            os.chown(path, uid, gid)
        before = state_hashes(rejected)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            negative_port = probe.getsockname()[1]
        result = subprocess.run([str(old_broker)], user=uid, group=gid,
                                env=environment(rejected, negative_port), capture_output=True, timeout=10)
        combined = result.stdout + result.stderr
        classification = ('version' if b'UnsupportedVersion(16)' in combined
                          or b'unsupported version 16' in combined else
                          'schema' if b'Malformed' in combined
                          or b'MQTT durable document is malformed' in combined else 'unknown')
        report['old_reader_negative'] = dict(
            returncode=result.returncode, classification=classification,
            stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
        require(state_hashes(rejected) == before and state_hashes(state) == state16_hashes,
                'old_reader_does_not_mutate_snapshot_wal')
        require(result.returncode != 0 and classification in ('schema', 'version'),
                'old_reader_refuses_v16')
        report['stages'].append('042_refuses_private_v16_copy_without_snapshot_wal_mutation')
        run('apt-get', 'install', '-y', '--allow-downgrades', '-o',
            'Dpkg::Options::=--force-confold', args.old_deb)
        require(run('/usr/bin/mqtt-broker', '--version') == 'mqtt-broker 0.42.0', 'rollback042')
        check_unit()
        require(state_hashes(state) == state16_hashes, 'package_rollback_preserves_v16')
        restored = Path('/var/lib/xmqr/p228-restored15')
        require(not restored.exists(), 'restore_new_destination')
        run('/usr/bin/mqtt-admin', 'state', 'restore', '--backup', backup, '--state-dir', restored,
            uid=uid, gid=gid)
        require(document(restored)['version'] == 15, 'restored_real_backup15')
        forbidden = subprocess.run(['/usr/bin/mqtt-admin', 'state', 'restore', '--backup', str(backup),
                                    '--state-dir', str(restored)], user=uid, group=gid, capture_output=True)
        require(forbidden.returncode != 0, 'restore_existing_destination_refused')
        require(not (restored / '.mqtt-broker-profile').exists(), 'restore_does_not_invent_profile')
        restored_hashes = state_hashes(restored)
        profile_guard = subprocess.run(['/usr/bin/mqtt-broker'], user=uid, group=gid,
                                       env=environment(restored, negative_port),
                                       capture_output=True, timeout=10)
        require(profile_guard.returncode != 0 and
                b'unmarked MQTT_STATE_DIR with existing state is treated as secure-mtls'
                in profile_guard.stderr + profile_guard.stdout, 'restored_profile_guard')
        require(state_hashes(restored) == restored_hashes, 'profile_guard_preserves_snapshot_wal')
        restored_profile = restored / '.mqtt-broker-profile'
        with restored_profile.open('xb') as stream:
            stream.write(profile15.read_bytes())
        restored_profile.chmod(0o600)
        os.chown(restored_profile, uid, gid)
        require(restored_profile.read_bytes() == profile15.read_bytes(), 'exact_original_profile_restored')
        report['rollback_profile'] = dict(
            unmarked_guard='PASS', source_profile_sha256=digest(profile15),
            restoration='exact original marker separately preserved; not included by state backup/restore')
        with broker('/usr/bin/mqtt-broker', restored, uid, gid, base / 'rollback.log') as port:
            consume(port)
        require(document(restored)['version'] == 15 and state_hashes(backup) == backup_hashes,
                'rollback_executes_only_restored15_and_preserves_backup')
        require(all(file_status(Path(path)) == value for path, value in preserved.items()),
                'rollback_preserves_operator_files')
        report['stages'].append('rollback042_new_destination_backup15_replays_offline_retained')
        run('apt-get', 'remove', '-y', 'xmqr-broker')
        require(not Path('/usr/bin/mqtt-broker').exists() and not Path('/usr/bin/mqtt-admin').exists(),
                'remove_binaries')
        require(all(file_status(Path(path)) == value for path, value in preserved.items()),
                'remove_preserves_operator_files')
        run('apt-get', 'purge', '-y', 'xmqr-broker')
        require(not conffile.exists(), 'purge_removes_package_conffile')
        require(file_status(secret) == preserved[str(secret)]
                and file_status(sentinel) == preserved[str(sentinel)], 'purge_preserves_private_files')
        require(state_hashes(state) == state16_hashes, 'purge_preserves_migrated_state')
        run('getent', 'passwd', 'xmqr')
        report['stages'].append('remove_purge_preserves_v16_secret_marker_account')
        report.update(old_deb_sha256=digest(args.old_deb), new_deb_sha256=digest(args.new_deb),
                      native_broker_sha256=args.new_broker_sha, native_admin_sha256=args.new_admin_sha,
                      backup15_sha256=backup_hashes, migrated16_sha256=state16_hashes)


class ReaderTests(unittest.TestCase):
    @staticmethod
    def snapshot():
        key, value = b'mqtt311.state.v1', b'version=15\n[state]\n'
        data = struct.pack('<8sHQI', b'MQSNAP01', 1, 4, 1)
        data += struct.pack('<HI', len(key), len(value)) + key + value
        return data + zlib.crc32(data).to_bytes(4, 'little')

    def test_real_reader_shape(self):
        self.assertEqual(snapshot_document(self.snapshot()), {'version': 15, 'state': {}})

    def test_crc_and_truncation_fail_closed(self):
        valid = self.snapshot()
        for invalid in (valid[:-1], valid[:25], valid[:-4] + b'\0\0\0\0'):
            with self.subTest(length=len(invalid)), self.assertRaises(AssertionError):
                snapshot_document(invalid)

    def test_oversized_entry_fails_before_decode(self):
        value = bytearray(self.snapshot()[:-4])
        struct.pack_into('<I', value, 24, 1_048_577)
        value += zlib.crc32(value).to_bytes(4, 'little')
        with self.assertRaisesRegex(AssertionError, 'snapshot_entry_size'):
            snapshot_document(value)

    def test_explicit_git_revision_syntax(self):
        self.assertEqual(git_revision(RUNTIME_CHECKPOINT), RUNTIME_CHECKPOINT)

    def test_git_revision_rejects_noncanonical_source(self):
        for value in ('', 'HEAD', 'a' * 39, 'a' * 41, 'A' * 40, 'g' * 40):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                git_revision(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--old-deb', type=Path)
    parser.add_argument('--new-deb', type=Path)
    parser.add_argument('--new-broker-sha')
    parser.add_argument('--new-admin-sha')
    parser.add_argument('--source', type=git_revision,
                        help='explicit artifact Git SHA40; caller must verify CI head_sha/package provenance')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReaderTests))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    if not all((args.old_deb, args.new_deb, args.new_broker_sha, args.new_admin_sha, args.source, args.report)):
        parser.error('explicit packages, source, expected native ELF hashes and new report are required')
    if args.report.exists():
        parser.error('report exists; choose a new owned path')
    started = time.monotonic()
    report = dict(status='RUNNING', source_revision=args.source, platform='Ubuntu26.04/amd64',
                  runtime_checkpoint=RUNTIME_CHECKPOINT,
                  source_provenance='caller-declared SHA40; verify CI head_sha and package/ELF hashes externally',
                  scope='owned container; loopback MQTT311, process shutdown, no TLS/power-loss certification',
                  stages=[])
    try:
        lifecycle(args, report)
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error_type=type(error).__name__, reason=str(error))
    report['elapsed_seconds'] = round(time.monotonic() - started, 4)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(report), flush=True)
    if report['status'] != 'PASS':
        raise SystemExit(1)
    print('P228_PACKAGE_STATE16_ROLLBACK_PASS', flush=True)


if __name__ == '__main__':
    main()
