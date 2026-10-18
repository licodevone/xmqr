#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P63: test-owned Docker network, secrets/state volumes and mTLS pub/sub."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import ssl
import subprocess
import tarfile
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def docker(*args, **kwargs):
    return subprocess.run(['docker', *map(str, args)], check=True,
                          capture_output=True, timeout=90, **kwargs)


def wait(predicate):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.1)
    raise AssertionError('container readiness timeout')


def logs(container):
    result = docker('logs', container)
    return result.stdout + result.stderr


def assert_message(output, retained=False):
    messages = [json.loads(line) for line in output.splitlines()]
    assert len(messages) == 1
    message = messages[0]
    assert message['event'] == 'publish' and message['topic'] == 'sensor/value'
    assert message['qos'] == 1 and message['retain'] == retained
    assert bytes(message['payload_bytes']) == b'docker-fixture'


def seed(image, volume, files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for name, value in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(value)
            entry.mode = 0o600
            entry.uid = entry.gid = 10001
            archive.addfile(entry, io.BytesIO(value))
    docker('run', '--rm', '-i', '--user', '0', '--entrypoint', 'sh',
           '-v', volume+':/secrets', image, '-c',
           'tar -xf - -C /secrets && chown 10001:10001 /secrets && chmod 700 /secrets',
           input=buffer.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker-image', required=True)
    parser.add_argument('--client-image', required=True)
    parser.add_argument('--hash-file', type=Path, required=True, help='public test fixture hash, never production')
    parser.add_argument('--openssl', default='openssl')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--remote-wss', action='store_true',
                        help='also verify P214/C117 across the disposable Docker network')
    args = parser.parse_args()
    if args.report.exists():
        parser.error('report exists; choose another output')
    croot = ROOT.parent/'xmqr-client'
    spec = importlib.util.spec_from_file_location('c27', croot/'validation/C27-integration.py')
    c27 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c27)
    def fixture_openssl(root, *options):
        return subprocess.run([args.openssl, *options], cwd=root, check=True,
                              capture_output=True, timeout=30)
    c27.openssl = fixture_openssl
    name = 'xmqr-p63-'+uuid.uuid4().hex[:10]
    volumes = [name+'-state', name+'-broker-secret', name+'-client-secret']
    containers = []
    report = {'broker_image': args.broker_image, 'client_image': args.client_image,
              'scenarios': [], 'image_metadata': {}}
    try:
        for label, image in [('broker', args.broker_image), ('client', args.client_image)]:
            data = json.loads(docker('image', 'inspect', image).stdout)[0]
            assert data['Config']['User'] == '10001:10001'
            assert data['Architecture'] == 'amd64' and data['Os'] == 'linux'
            report['image_metadata'][label] = {'id': data['Id'], 'labels': data['Config']['Labels'], 'user': data['Config']['User']}
        docker('network', 'create', name)
        for volume in volumes:
            docker('volume', 'create', volume)
        with tempfile.TemporaryDirectory(prefix=name) as temporary:
            root = Path(temporary)
            c27.certificates(root)
            c27.openssl(root, 'req', '-new', '-key', 'server.key', '-out', 'docker.csr', '-subj', '/CN=broker')
            (root/'docker.ext').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:broker\n')
            c27.openssl(root, 'x509', '-req', '-in', 'docker.csr', '-CA', 'ca.crt', '-CAkey', 'ca.key', '-set_serial', '42', '-days', '1', '-extfile', 'docker.ext', '-out', 'docker.crt')
            fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert((root/'client.crt').read_text())).hexdigest()
            password_hash = args.hash_file.read_text(encoding='utf-8-sig').strip()
            assert password_hash.startswith('$argon2id$')
            bundle = f"version=1\n[[users]]\nusername='fixture-device'\npassword_hash='{password_hash}'\ncert_sha256='sha256:{fingerprint}'\npublish=['sensor/value']\nsubscribe=['sensor/#']\n"
            seed(args.broker_image, volumes[1], {'server.crt': (root/'docker.crt').read_bytes(), 'server.key': (root/'server.key').read_bytes(), 'ca.crt': (root/'ca.crt').read_bytes(), 'security.toml': bundle.encode()})
            remote_profile = ("version=1\n[connection]\n"
                              "ws_url='wss://broker:8443/mqtt'\n"
                              "username='fixture-device'\nca='/run/certs/ca.crt'\n"
                              "cert='/run/certs/client.crt'\nkey='/run/certs/client.key'\n"
                              "password_file='/run/certs/password'\n")
            seed(args.broker_image, volumes[2], {**{f:(root/f).read_bytes() for f in ['ca.crt','client.crt','client.key','other.crt']}, 'password':b'fixture-pass', 'wrong-password':b'wrong-fixture', 'remote-profile.toml':remote_profile.encode()})
            broker_name=name+'-broker';containers.append(broker_name)
            remote_environment = ['-e', 'MQTT_WSS_BIND=0.0.0.0:8443',
                                  '-e', 'MQTT_WSS_REMOTE_ENABLED=true'] if args.remote_wss else []
            docker('run','-d','--name',broker_name,'--network',name,'--network-alias','broker','--network-alias','other-broker','--read-only','--cap-drop=ALL','--security-opt','no-new-privileges',
                   '-v',volumes[0]+':/var/lib/xmqr','-v',volumes[1]+':/run/secrets:ro',
                   '-e','MQTT_SERVER_CERT=/run/secrets/server.crt','-e','MQTT_SERVER_KEY=/run/secrets/server.key','-e','MQTT_CLIENT_CA=/run/secrets/ca.crt','-e','MQTT_SECURITY_BUNDLE=/run/secrets/security.toml','-e','RUST_LOG=info',*remote_environment,args.broker_image)
            wait(lambda: b'secure MQTT listener started' in logs(broker_name))
            common=['--host','broker','--port','8883','--username','fixture-device','--ca','/run/certs/ca.crt','--cert','/run/certs/client.crt','--key','/run/certs/client.key','--password-file','/run/certs/password','--output','jsonl','--qos','1','--timeout-seconds','3']

            def client(cli, container=None, check=True):
                command=['docker','run','--network',name,'--read-only','--cap-drop=ALL','--security-opt','no-new-privileges','-v',volumes[2]+':/run/certs:ro']
                command+=['--name',container] if container else ['--rm']
                result = subprocess.run(command+[args.client_image,*cli],check=False,capture_output=True,timeout=25)
                if check and result.returncode:
                    raise AssertionError(result.stderr.decode(errors='replace'))
                return result

            subscriber=name+'-subscriber';containers.append(subscriber)
            docker('run','-d','--name',subscriber,'--network',name,'--read-only','--cap-drop=ALL','--security-opt','no-new-privileges','-v',volumes[2]+':/run/certs:ro',args.client_image,'sub',*common,'--topic','sensor/#','--count','1')
            wait(lambda: b'Assinatura ativa' in docker('logs',subscriber).stderr)
            published=client(['pub',*common,'--topic','sensor/value','--message','docker-fixture','--retain','true'])
            assert b'publish_complete' in published.stdout
            wait(lambda: json.loads(docker('inspect',subscriber).stdout)[0]['State']['Status']=='exited')
            assert_message(docker('logs',subscriber).stdout)
            assert json.loads(docker('inspect',subscriber).stdout)[0]['State']['ExitCode']==0
            report['scenarios'].append('mTLS QoS1 pub/sub read-only/caps-none PASS')
            starts = logs(broker_name).count(b'secure MQTT listener started')
            docker('stop','--time','20',broker_name)
            assert json.loads(docker('inspect',broker_name).stdout)[0]['State']['ExitCode']==0
            assert b'durable broker shutdown complete' in logs(broker_name)
            docker('start',broker_name)
            wait(lambda: logs(broker_name).count(b'secure MQTT listener started') > starts)
            retained=client(['sub',*common,'--topic','sensor/#','--count','1'])
            assert_message(retained.stdout, retained=True)
            report['scenarios'].append('SIGTERM durable/restart/retained volume PASS')
            for field, wrong in [('--ca','/run/certs/other.crt'),('--password-file','/run/certs/wrong-password')]:
                negative=common.copy();negative[negative.index(field)+1]=wrong
                result=client(['pub',*negative,'--topic','sensor/value','--message','negative-fixture'],check=False)
                assert result.returncode!=0 and b'publish_complete' not in result.stdout
            report['scenarios'].append('wrong CA and wrong password refused PASS')
            if args.remote_wss:
                remote_url = 'wss://broker:8443/mqtt'
                remote_common = common[4:]
                for version in ('3.1.1', '5'):
                    flags = ['--protocol-version', version, '--allow-remote-wss',
                             '--ws-url', remote_url]
                    payload = 'remote-wss-' + version
                    published = client(['pub', *remote_common, *flags, '--topic',
                                        'sensor/value', '--message', payload,
                                        '--retain', 'true'])
                    assert b'publish_complete' in published.stdout
                    received = client(['sub', *remote_common, *flags, '--topic',
                                       'sensor/#', '--count', '1'])
                    message = json.loads(received.stdout.strip())
                    assert bytes(message['payload_bytes']) == payload.encode(), message
                    without_opt_in = client(['pub', *remote_common,
                                             '--ws-url', remote_url, '--topic',
                                             'sensor/value', '--message', 'blocked'], check=False)
                    assert without_opt_in.returncode != 0
                for field, wrong in [('--ca', '/run/certs/other.crt'),
                                     ('--password-file', '/run/certs/wrong-password')]:
                    negative = remote_common.copy()
                    negative[negative.index(field)+1] = wrong
                    denied = client(['pub', *negative, '--allow-remote-wss',
                                     '--ws-url', remote_url, '--topic', 'sensor/value',
                                     '--message', 'blocked', '--protocol-version', '5'],
                                    check=False)
                    assert denied.returncode != 0 and b'publish_complete' not in denied.stdout
                for url, topic in [(remote_url, 'sensor/denied'),
                                   ('wss://other-broker:8443/mqtt', 'sensor/value')]:
                    denied = client(['pub', *remote_common, '--allow-remote-wss',
                                     '--ws-url', url, '--topic', topic,
                                     '--message', 'blocked', '--protocol-version', '5'],
                                    check=False)
                    assert denied.returncode != 0 and b'publish_complete' not in denied.stdout
                profile_args = ['--profile', '/run/certs/remote-profile.toml',
                                '--allow-remote-wss', '--output', 'jsonl', '--qos', '1',
                                '--timeout-seconds', '3', '--protocol-version', '5']
                published = client(['pub', *profile_args, '--topic', 'sensor/value',
                                    '--message', 'remote-profile', '--retain', 'true'])
                assert b'publish_complete' in published.stdout
                received = client(['sub', *profile_args, '--topic', 'sensor/#', '--count', '1'])
                assert bytes(json.loads(received.stdout.strip())['payload_bytes']) == b'remote-profile'
                report['scenarios'].append('remote WSS mTLS MQTT 3.1.1/5 pub/sub and profile, opt-in, CA/SAN/password/ACL negatives PASS')
            report['status']='PASS'
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,indent=2)+'\n')
            print('DOCKER_MTLS_PUB_SUB_RESTART_NEGATIVES_PASS' +
                  (' P214_C117_REMOTE_WSS_PASS' if args.remote_wss else ''))
    finally:
        for container in reversed(containers):
            subprocess.run(['docker','rm','-f',container],capture_output=True,timeout=30)
        for volume in reversed(volumes):
            subprocess.run(['docker','volume','rm',volume],capture_output=True,timeout=30)
        subprocess.run(['docker','network','rm',name],capture_output=True,timeout=30)


if __name__=='__main__':
    main()
