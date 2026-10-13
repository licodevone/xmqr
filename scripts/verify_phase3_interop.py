#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91: C43 regression plus MQTT3.1.1 mTLS restart/ACL matrix, owned Docker only."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import time
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('c43', ROOT.parent / 'xmqr-client/scripts/verify_mosquitto_phase2.py')
c43 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c43)
invoke, fixture = c43.invoke, c43.fixture


def events(output, kind):
    if kind == 'xmqr':
        return [dict(topic=item['topic'], qos=item['qos'], retain=item['retain'],
                     payload=bytes(item['payload_bytes']))
                for line in output.splitlines() if line.startswith(b'{')
                for item in [json.loads(line)] if item.get('event') == 'publish']
    result = []
    for line in output.decode().splitlines():
        if line.startswith('DATA|'):
            _, topic, qos, retained, value = line.split('|', 4)
            result.append(dict(topic=topic, qos=int(qos), retain=bool(int(retained)), payload=bytes.fromhex(value)))
    return result


def validate_logical(output, kind, expected, qos, retained=False):
    received = events(output, kind)
    if any(item['topic'] != 'phase2/value' or item['qos'] != qos or item['retain'] != retained
           or item['payload'] not in expected for item in received):
        raise AssertionError('unexpected external topic/QoS/retain/sequence bytes')
    if set(item['payload'] for item in received) != set(expected):
        raise AssertionError('missing logical external publication after recovery')
    if qos == 2 and len(received) != len(expected):
        raise AssertionError('QoS2 duplicate application publication')
    return len(received) - len(expected)


class Campaign(c43.Campaign):
    def __init__(self, args, images):
        super().__init__(args, images)
        self.stage = 'c43_regression'
        self.context = {}
        self.last_subscriber = None
        self.startup_failure = None
        self.anchor = None

    def client_args(self, kind, command, qos, **kwargs):
        writer = kwargs.pop('writer', False)
        image, entry, options = super().client_args(kind, command, qos, **kwargs)
        if writer:
            field = '--username' if kind == 'xmqr' else '-u'
            options[options.index(field) + 1] = 'fixture-writer'
            options[options.index('--cert') + 1] = '/run/certs/writer.crt'
            options[options.index('--key') + 1] = '/run/certs/writer.key'
        if kind == 'xmqr' and command == 'sub':
            options += ['--reconnect-attempts', '6']
        if self.anchor and kind == 'mosquitto' and command == 'sub':
            options[options.index('-W') + 1] = '40'
        return image, entry, options

    def state(self, name):
        return json.loads(invoke('inspect', name).stdout)[0]['State']

    def start_server(self, kind, secrets, wrong_name=False):
        self.stage = 'start_' + kind + ('_wrong_san' if wrong_name else '')
        try:
            if self.anchor:
                name = self.prefix + '-' + kind
                self.containers.append(name)
                options = ['run', '-d', '--name', name, '--network', 'container:' + self.anchor,
                           '--user', '10001:10001', '--read-only', '--cap-drop=ALL',
                           '--security-opt', 'no-new-privileges', '-v', secrets + ':/run/test']
                if kind == 'xmqr':
                    options += ['-e', 'MQTT_BIND=127.0.0.1:8883', '-e', 'MQTT_STATE_DIR=/run/test/state',
                                '-e', 'MQTT_SERVER_CERT=/run/test/server.crt', '-e', 'MQTT_SERVER_KEY=/run/test/server.key',
                                '-e', 'MQTT_CLIENT_CA=/run/test/ca.crt', '-e', 'MQTT_SECURITY_BUNDLE=/run/test/security.toml',
                                '-e', 'RUST_LOG=info']
                    image, cli = self.images['broker']['id'], []
                else:
                    options += ['--entrypoint', 'mosquitto']
                    image, cli = self.images['mosquitto']['id'], ['-c', '/run/test/mosquitto.conf']
                invoke(*options, image, *cli)
                fixture.wait(lambda: (b'listener started' if kind == 'xmqr' else b'mosquitto version 2.0.22 running')
                             in fixture.logs(name))
                return name
            return super().start_server(kind, secrets, wrong_name)
        except AssertionError:
            name = self.prefix + '-' + kind + ('-wrong-san' if wrong_name else '')
            state = self.state(name)
            output = fixture.logs(name).lower()
            self.startup_failure = dict(status=state['Status'], exit_code=state['ExitCode'],
                                        configuration_error=b'configuration' in output or b'config' in output,
                                        certificate_error=b'certificate' in output,
                                        duplicate_fingerprint=b'one certificate cannot belong to multiple users' in output,
                                        permission_error=b'permission' in output, state_error=b'state' in output)
            raise

    def seed_extended(self, root):
        volume = self.prefix + '-expanded-fixtures'
        invoke('volume', 'create', volume)
        self.volumes.append(volume)
        fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert((root / 'client.crt').read_text())).hexdigest()
        def openssl(*options):
            subprocess.run([self.args.openssl, *options], cwd=root, check=True, capture_output=True, timeout=30)
        openssl('req', '-new', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'writer.key',
                '-out', 'writer.csr', '-subj', '/CN=p91-fixture-writer')
        (root / 'writer.ext').write_text('basicConstraints=critical,CA:FALSE\n'
                                        'keyUsage=critical,digitalSignature,keyEncipherment\n'
                                        'extendedKeyUsage=clientAuth\nsubjectAltName=DNS:writer.fixture\n')
        openssl('x509', '-req', '-in', 'writer.csr', '-CA', 'ca.crt', '-CAkey', 'ca.key',
                '-set_serial', '5', '-days', '1', '-extfile', 'writer.ext', '-out', 'writer.crt')
        writer_fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert((root / 'writer.crt').read_text())).hexdigest()
        password_hash = self.args.hash_file.read_text(encoding='utf-8-sig').strip()
        if not password_hash.startswith('$argon2id$v=19$m=19456,t=2,p=1$'):
            raise ValueError('public test Argon2 fixture required')
        policy = ("version=1\n[[users]]\nusername='fixture-device'\n"
                  f"password_hash='{password_hash}'\ncert_sha256='sha256:{fingerprint}'\n"
                  "publish=['phase2/value','phase2/will']\nsubscribe=['phase2/#','phase2/value','phase2/will']\n"
                  "[[users]]\nusername='fixture-writer'\n"
                  f"password_hash='{password_hash}'\ncert_sha256='sha256:{writer_fingerprint}'\n"
                  "publish=['other/value']\nsubscribe=[]\n")
        config = ('listener 8883 127.0.0.1\nallow_anonymous false\nrequire_certificate true\n'
                  'cafile /run/test/ca.crt\ncertfile /run/test/server.crt\nkeyfile /run/test/server.key\n'
                  'password_file /run/test/password.db\nacl_file /run/test/acl\n'
                  'persistence true\npersistence_location /run/test/mosquitto-state/\n'
                  'autosave_interval 1\nlog_dest stdout\nlog_type all\n')
        files = {name: (root / name).read_bytes() for name in
                 ['ca.crt', 'server.crt', 'server.key', 'client.crt', 'client.key', 'other.crt', 'writer.crt', 'writer.key']}
        files.update({'security.toml': policy.encode(), 'mosquitto.conf': config.encode(),
                      'acl': (b'user fixture-device\ntopic write phase2/value\ntopic write phase2/will\ntopic read phase2/#\n'
                              b'user fixture-writer\ntopic write other/value\n'),
                      'password': b'fixture-pass', 'payload.bin': c43.PAYLOAD})
        fixture.seed(self.images['broker']['id'], volume, files)
        invoke('run', '--rm', '--network', 'none', '--user', '10001:10001', '--entrypoint', 'sh',
               '-v', volume + ':/run/test', self.images['mosquitto']['id'], '-c',
               'mkdir /run/test/state /run/test/mosquitto-state && '
               'mosquitto_passwd -b -c /run/test/password.db fixture-device fixture-pass && '
               'mosquitto_passwd -b /run/test/password.db fixture-writer fixture-pass')
        return volume

    def write_payload(self, volume, value):
        fixture.seed(self.images['broker']['id'], volume, {'payload.bin': value})

    def restart(self, server, kind, crash):
        namespace = invoke('exec', server, 'readlink', '/proc/1/ns/net').stdout.strip()
        before = fixture.logs(server).count(b'listener started' if kind == 'xmqr' else b'mosquitto version 2.0.22 running')
        if crash:
            invoke('kill', '--signal', 'KILL', server)
            if self.state(server)['ExitCode'] != 137:
                raise AssertionError('test broker SIGKILL exit mismatch')
        else:
            invoke('stop', '--time', '20', server)
            if self.state(server)['ExitCode'] != 0:
                raise AssertionError('test broker SIGTERM failed')
        invoke('start', server)
        fixture.wait(lambda: fixture.logs(server).count(
            b'listener started' if kind == 'xmqr' else b'mosquitto version 2.0.22 running') > before)
        if (invoke('exec', server, 'readlink', '/proc/1/ns/net').stdout.strip() != namespace
                or invoke('exec', self.anchor, 'readlink', '/proc/1/ns/net').stdout.strip() != namespace):
            raise AssertionError('test network namespace changed across broker restart')

    def expanded(self, root):
        volume = self.seed_extended(root)
        self.anchor = self.prefix + '-namespace'
        self.containers.append(self.anchor)
        invoke('run', '-d', '--name', self.anchor, '--network', 'none', '--user', '10001:10001',
               '--read-only', '--cap-drop=ALL', '--security-opt', 'no-new-privileges',
               '--entrypoint', 'sh', self.images['broker']['id'], '-c', 'while :; do sleep 30; done')
        for server_kind in ('xmqr', 'mosquitto'):
            if self.args.server_filter != 'both' and server_kind != self.args.server_filter:
                continue
            server = self.start_server(server_kind, volume)
            for pub_kind, sub_kind in [('xmqr', 'mosquitto'), ('mosquitto', 'xmqr')]:
                for qos in (1, 2):
                    self.context = dict(server=server_kind, publisher=pub_kind, subscriber=sub_kind, qos=qos)
                    self.stage = 'subscriber_start_before_sigterm'
                    # Detached subscriber survives broker SIGTERM. Distinct public
                    # sequence payloads detect loss; QoS1 duplicates are permitted.
                    subscriber = self.job(server, volume, sub_kind, 'sub', qos, count=50,
                                          persistent='p91-' + uuid.uuid4().hex[:10], detached=True)
                    self.last_subscriber = subscriber
                    values = [f'p91-{number}'.encode() + b'\0\xff' for number in (0, 1)]
                    self.stage = 'first_publish_before_sigterm'
                    self.write_payload(volume, values[0])
                    if self.job(server, volume, pub_kind, 'pub', qos).returncode:
                        raise AssertionError('initial restart publication failed')
                    fixture.wait(lambda: any(item['payload'] == values[0] for item in events(fixture.logs(subscriber), sub_kind)))
                    self.restart(server, server_kind, crash=False)
                    self.stage = 'publish_after_sigterm'
                    # Persistent recipient may be offline: durable broker queues it.
                    self.write_payload(volume, values[1])
                    if self.job(server, volume, pub_kind, 'pub', qos).returncode:
                        raise AssertionError('post-restart publication failed')
                    fixture.wait(lambda: any(item['payload'] == values[1] for item in events(fixture.logs(subscriber), sub_kind)))
                    duplicates = validate_logical(fixture.logs(subscriber), sub_kind, values, qos)
                    invoke('stop', '--time', '8', subscriber)
                    if self.state(subscriber)['ExitCode'] != 0:
                        raise AssertionError('live subscriber cancellation failed')
                    self.results.append(dict(server=server_kind, publisher=pub_kind, subscriber=sub_kind,
                                             qos=qos, scenario='live_persistent_reconnect_sigterm',
                                             logical_messages=2, qos1_duplicate_events=duplicates, status='PASS'))
                    self.stage = 'retained_crash_replay'
                    # Retained ACK then process SIGKILL: replay bytes are checked
                    # through the other implementation after real restart.
                    self.write_payload(volume, c43.PAYLOAD)
                    if self.job(server, volume, pub_kind, 'pub', qos, retain=True).returncode:
                        raise AssertionError('pre-crash retained publication failed')
                    if server_kind == 'mosquitto':
                        # Mosquitto fsync contract differs from XMQR. Wait one
                        # explicit persistence autosave, not pretend PUBACK=fsync.
                        fixture.wait(lambda: b'Saving in-memory database' in fixture.logs(server))
                        time.sleep(1.2)
                    self.restart(server, server_kind, crash=True)
                    replay = self.job(server, volume, sub_kind, 'sub', qos)
                    if replay.returncode:
                        raise AssertionError('post-crash retained replay failed')
                    (c43.validate_xmqr if sub_kind == 'xmqr' else c43.validate_mosquitto)(replay.stdout, qos, True)
                    self.results.append(dict(server=server_kind, publisher=pub_kind, subscriber=sub_kind,
                                             qos=qos, scenario='retained_process_crash_replay', status='PASS',
                                             mosquitto_autosave_wait=server_kind == 'mosquitto'))
                    self.write_payload(volume, b'')
                    if self.job(server, volume, pub_kind, 'pub', 1, retain=True).returncode:
                        raise AssertionError('test retained cleanup failed')
                    self.write_payload(volume, c43.PAYLOAD)
                # Protocol timeout must not be message-idle timeout. This is an
                # accepted-candidate gate; old 0.8.1 is explicitly not accepted.
                if self.args.label == 'candidate':
                    self.stage = 'idle_exceeds_protocol_deadline'
                    subscriber = self.job(server, volume, sub_kind, 'sub', 1, detached=True)
                    time.sleep(4.3)  # exceeds --timeout-seconds3, bounded actual wait
                    if self.state(subscriber)['Status'] != 'running':
                        raise AssertionError('idle subscriber incorrectly expired protocol timeout')
                    if self.job(server, volume, pub_kind, 'pub', 1).returncode:
                        raise AssertionError('idle resume publication failed')
                    (c43.validate_xmqr if sub_kind == 'xmqr' else c43.validate_mosquitto)(self.finished(subscriber), 1)
                    self.results.append(dict(server=server_kind, subscriber=sub_kind,
                                             scenario='idle_exceeds_protocol_deadline_then_receives', status='PASS'))
            # Observe both ACL-denied sends independently; Mosquitto may ACK a
            # denied MQTT3 publication, so exit status is not an authorization oracle.
            for denied_kind, observer_kind in [('xmqr', 'mosquitto'), ('mosquitto', 'xmqr')]:
                self.stage = 'publish_acl_negative'
                observer = self.job(server, volume, observer_kind, 'sub', 1, topic='phase2/#', count=50, detached=True)
                self.job(server, volume, denied_kind, 'pub', 1, topic='phase2/denied')
                if self.job(server, volume, denied_kind, 'pub', 1).returncode:
                    raise AssertionError('authorized ACL barrier publication failed')
                fixture.wait(lambda: len(events(fixture.logs(observer), observer_kind)) >= 1)
                received = events(fixture.logs(observer), observer_kind)
                if (len(received) != 1 or received[0]['payload'] != c43.PAYLOAD
                        or received[0]['topic'] != 'phase2/value'):
                    raise AssertionError('denied publication reached independent observer')
                invoke('stop', '--time', '8', observer)
                self.results.append(dict(server=server_kind, publisher=denied_kind, subscriber=observer_kind,
                                         scenario='publish_acl_denied_observed_then_authorized_barrier', status='PASS'))
            for subscriber_kind, writer_kind in [('xmqr', 'mosquitto'), ('mosquitto', 'xmqr')]:
                self.stage = 'subscribe_acl_negative'
                image, entry, options = self.client_args(subscriber_kind, 'sub', 1, topic='other/#', count=50)
                name = self.prefix + '-denied-sub-' + uuid.uuid4().hex[:8]
                self.containers.append(name)
                invoke('run', '-d', '-t', '--name', name, '--network', 'container:' + server,
                       '--user', '10001:10001', '--read-only', '--cap-drop=ALL',
                       '--security-opt', 'no-new-privileges', '-v', volume + ':/run/certs:ro',
                       *entry, image, *options)
                fixture.wait(lambda: self.state(name)['Status'] == 'exited'
                             or (b'received SUBACK' if subscriber_kind == 'mosquitto' else b'Assinatura ativa')
                             in fixture.logs(name))
                writer = self.job(server, volume, writer_kind, 'pub', 1, topic='other/value', writer=True)
                if writer.returncode:
                    raise AssertionError('independent ACL writer was not authorized')
                time.sleep(1)
                if events(fixture.logs(name), subscriber_kind):
                    raise AssertionError('unauthorized subscription delivered independent writer payload')
                behavior = 'immediate_refusal' if self.state(name)['Status'] == 'exited' else 'delivery_filter'
                if behavior == 'delivery_filter':
                    invoke('stop', '--time', '8', name)
                self.results.append(dict(server=server_kind, subscriber=subscriber_kind, publisher=writer_kind,
                                         scenario='subscribe_acl_denied_independent_authorized_writer',
                                         observed_policy=behavior, status='PASS'))
            invoke('stop', '--time', '20', server)
            if self.state(server)['ExitCode'] != 0:
                raise AssertionError('expanded test broker shutdown failed')

    def close(self):
        removed_containers = removed_volumes = 0
        for container in reversed(self.containers):
            if invoke('rm', '-f', '-v', container, check=False).returncode == 0:
                removed_containers += 1
        for volume in reversed(self.volumes):
            if invoke('volume', 'rm', volume, check=False).returncode == 0:
                removed_volumes += 1
        result = dict(containers_owned=len(self.containers), containers_removed=removed_containers,
                      volumes_owned=len(self.volumes), volumes_removed=removed_volumes)
        result['status'] = 'PASS' if (removed_containers == len(self.containers)
                                     and removed_volumes == len(self.volumes)) else 'FAIL'
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker-image', required=True)
    parser.add_argument('--client-image', required=True)
    parser.add_argument('--mosquitto-image', default='eclipse-mosquitto:2.0.22')
    parser.add_argument('--hash-file', type=Path, required=True)
    parser.add_argument('--openssl', default='openssl')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--label', choices=['baseline', 'candidate'], required=True)
    parser.add_argument('--only', choices=['all', 'expanded'], default='all')
    parser.add_argument('--server-filter', choices=['both', 'xmqr', 'mosquitto'], default='both')
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink():
        parser.error('report exists; choose another output')
    if args.label == 'candidate' and (args.only != 'all' or args.server_filter != 'both'):
        parser.error('candidate acceptance requires complete C43 regression and expansion')
    images = {name: c43.metadata(ref) for name, ref in [('broker', args.broker_image),
              ('client', args.client_image), ('mosquitto', args.mosquitto_image)]}
    if b'mosquitto version 2.0.22' not in invoke('run', '--rm', '--network', 'none', '--entrypoint',
                                               'mosquitto', images['mosquitto']['id'], '-h').stdout:
        parser.error('Mosquitto2.0.22 required')
    certspec = importlib.util.spec_from_file_location('c27', ROOT.parent / 'xmqr-client/validation/C27-integration.py')
    certs = importlib.util.module_from_spec(certspec)
    certspec.loader.exec_module(certs)
    certs.openssl = lambda root, *options: subprocess.run([args.openssl, *options], cwd=root,
                                                         check=True, capture_output=True, timeout=30)
    campaign = Campaign(args, images)
    report = dict(schema_version=1, status='RUNNING', label=args.label, selection=args.only,
                  server_selection=args.server_filter, images=images,
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scenarios=campaign.results,
                  dependency_sha256={str(path.relative_to(ROOT.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in (ROOT.parent / 'xmqr-client/scripts/verify_mosquitto_phase2.py',
                                                  ROOT / 'scripts/verify_docker.py',
                                                  ROOT.parent / 'xmqr-client/validation/C27-integration.py')},
                  network='owned loopback namespaces, no published host ports',
                  limitations=['not exhaustive MQTT3.1.1 conformance', 'not physical power-loss',
                               'no certificate rotation, MQTT5 or new ESP32 acceptance',
                               'Mosquitto persistence requires explicit autosave before process crash'])
    began = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix=campaign.prefix) as temporary:
            root = Path(temporary)
            certs.certificates(root)
            if args.only == 'all':
                campaign.execute(root)
            report['c43_regression_scenarios'] = len(campaign.results)
            # C43 servers remain as stopped containers. Distinct prefix prevents
            # collisions while retaining cleanup ownership of every resource.
            campaign.prefix += '-expanded'
            campaign.expanded(root)
        report['status'] = 'PASS'
    except Exception as failure:
        report['status'] = 'FAIL'
        report['error_type'] = type(failure).__name__
        report['error'] = str(failure) if isinstance(failure, AssertionError) else 'owned Docker test operation failed'
        report['failure_context'] = dict(stage=campaign.stage, **campaign.context)
        if campaign.startup_failure:
            report['startup_failure'] = campaign.startup_failure
        if campaign.last_subscriber:
            state = campaign.state(campaign.last_subscriber)
            report['last_subscriber'] = dict(status=state['Status'], exit_code=state['ExitCode'])
            output = fixture.logs(campaign.last_subscriber).lower()
            report['last_subscriber'].update(connection_lost=b'connection was lost' in output,
                                             timed_out=b'timed out' in output, tls_error=b'tls' in output,
                                             protocol_error=b'protocol error' in output,
                                             logical_events=len(events(fixture.logs(campaign.last_subscriber),
                                                                       campaign.context.get('subscriber', 'xmqr'))))
    finally:
        report['cleanup'] = campaign.close()
        if report['cleanup']['status'] != 'PASS':
            report['status'] = 'FAIL'
        report['observed_seconds'] = round(time.monotonic() - began, 3)
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print('PHASE3_INTEROP_' + report['status'], len(campaign.results), flush=True)
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
