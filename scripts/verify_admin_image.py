#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P78: admin image on disposable state only, never an installed broker."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, capture_output=True, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker-image', required=True)
    parser.add_argument('--admin-image', required=True)
    parser.add_argument('--client-image', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('report exists; choose a fresh output')
    name = 'xmqr-p78-admin-' + uuid.uuid4().hex[:10]
    volume = name + '-state'
    started = False
    created = False
    try:
        info = json.loads(docker('image', 'inspect', args.admin_image).stdout)[0]
        assert info['Config']['User'] == '10001:10001'
        assert info['Config']['Entrypoint'] == ['/usr/local/bin/mqtt-admin']
        docker('run', '--rm', '--network', 'none', '--read-only', '--cap-drop=ALL',
               '--entrypoint', 'sh', args.admin_image, '-c',
               'test ! -e /usr/local/bin/mqtt-broker')
        docker('volume', 'create', volume)
        created = True
        docker('run', '--rm', '--user', '0', '--entrypoint', 'sh',
               '-v', volume + ':/work', args.admin_image, '-c',
               'mkdir /work/state && chown -R 10001:10001 /work && chmod 700 /work /work/state')
        docker('run', '-d', '--name', name, '--read-only', '--cap-drop=ALL',
               '--security-opt', 'no-new-privileges', '-v', volume + ':/work',
               '-e', 'MQTT_MODE=open-lab', '-e', 'MQTT_BIND=127.0.0.1:1883',
               '-e', 'MQTT_STATE_DIR=/work/state', '-e', 'RUST_LOG=info', args.broker_image)
        started = True
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = docker('logs', name)
            if b'listener started' in result.stdout + result.stderr:
                break
            time.sleep(.1)
        else:
            raise AssertionError('test broker did not become ready')
        docker('run', '--rm', '--network', 'container:' + name, '--read-only',
               '--cap-drop=ALL', '--security-opt', 'no-new-privileges', args.client_image,
               'pub', '--open-lab', '--host', '127.0.0.1', '--port', '1883',
               '--topic', 'backup/value', '--qos', '1', '--message', 'admin-fixture', '--retain', 'true')

        def admin(*options, check=True):
            return docker('run', '--rm', '--network', 'none', '--read-only',
                          '--cap-drop=ALL', '--security-opt', 'no-new-privileges',
                          '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m,mode=1777',
                          '-v', volume + ':/work', args.admin_image, *options, check=check)

        assert admin('state', 'backup', '--state-dir', '/work/state',
                     '--destination', '/work/forbidden', check=False).returncode != 0
        docker('stop', '--time', '20', name)
        assert json.loads(docker('inspect', name).stdout)[0]['State']['ExitCode'] == 0
        admin('state', 'backup', '--state-dir', '/work/state', '--destination', '/work/backup')
        admin('state', 'verify', '--backup', '/work/backup')
        admin('state', 'restore', '--backup', '/work/backup', '--state-dir', '/work/restored')
        assert admin('state', 'restore', '--backup', '/work/backup',
                     '--state-dir', '/work/restored', check=False).returncode != 0
        report = {'status': 'PASS', 'admin_image': args.admin_image,
                  'scenarios': ['dedicated non-root admin image without broker binary',
                                'backup refuses active broker lock',
                                'offline backup/verify/restore',
                                'restore refuses an existing destination'],
                  'network': 'test-only loopback namespace; no published ports',
                  'state': 'test-owned disposable volume'}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print('ADMIN_IMAGE_BACKUP_LOCK_RESTORE_PASS')
    finally:
        if started:
            docker('rm', '-f', name, check=False)
        if created:
            docker('volume', 'rm', volume, check=False)


if __name__ == '__main__':
    main()
