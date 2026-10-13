#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91 baseline-only C43 Will/crash reproduction, unchanged Mosquitto -W8."""
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

sys.dont_write_bytecode = True
import verify_phase3_interop as extended

c43, fixture, invoke = extended.c43, extended.fixture, extended.invoke


def seed_c43(campaign, root):
    volume = campaign.prefix + '-fixtures'
    invoke('volume', 'create', volume)
    campaign.volumes.append(volume)
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert((root / 'client.crt').read_text())).hexdigest()
    password_hash = campaign.args.hash_file.read_text(encoding='utf-8-sig').strip()
    if not password_hash.startswith('$argon2id$v=19$m=19456,t=2,p=1$'):
        raise ValueError('public C43 fixture hash required')
    bundle = ("version=1\n[[users]]\nusername='fixture-device'\n"
              f"password_hash='{password_hash}'\ncert_sha256='sha256:{fingerprint}'\n"
              "publish=['phase2/value','phase2/will']\nsubscribe=['phase2/#','phase2/value','phase2/will']\n")
    config = ('listener 8883 127.0.0.1\nallow_anonymous false\nrequire_certificate true\n'
              'cafile /run/test/ca.crt\ncertfile /run/test/server.crt\nkeyfile /run/test/server.key\n'
              'password_file /run/test/password.db\nacl_file /run/test/acl\n'
              'persistence false\nlog_dest stdout\nlog_type all\n')
    files = {name: (root / name).read_bytes() for name in
             ('ca.crt', 'server.crt', 'server.key', 'client.crt', 'client.key', 'other.crt',
              'wrong-name.crt', 'wrong-name.key')}
    files.update({'security.toml': bundle.encode(), 'mosquitto.conf': config.encode(),
                  'acl': b'user fixture-device\ntopic write phase2/value\ntopic write phase2/will\ntopic read phase2/#\n',
                  'password': b'fixture-pass', 'wrong-password': b'wrong-fixture', 'payload.bin': c43.PAYLOAD})
    fixture.seed(campaign.images['broker']['id'], volume, files)
    invoke('run', '--rm', '--network', 'none', '--user', '10001:10001', '--entrypoint', 'sh',
           '-v', volume + ':/run/test', campaign.images['mosquitto']['id'], '-c',
           'mkdir /run/test/state /run/test/state2 && mosquitto_passwd -b -c /run/test/password.db fixture-device fixture-pass')
    return volume


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker-image', required=True)
    parser.add_argument('--client-image', required=True)
    parser.add_argument('--mosquitto-image', default='eclipse-mosquitto:2.0.22')
    parser.add_argument('--hash-file', type=Path, required=True)
    parser.add_argument('--openssl', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--server-filter', choices=('both', 'xmqr', 'mosquitto'), default='xmqr')
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink() or not 1 <= args.repetitions <= 3:
        parser.error('new report and 1..3 repetitions required')
    images = {name: c43.metadata(ref) for name, ref in
              [('broker', args.broker_image), ('client', args.client_image), ('mosquitto', args.mosquitto_image)]}
    spec = importlib.util.spec_from_file_location('c27', extended.ROOT.parent / 'xmqr-client/validation/C27-integration.py')
    certs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(certs)
    certs.openssl = lambda root, *options: subprocess.run([args.openssl, *options], cwd=root,
                                                         check=True, capture_output=True, timeout=30)
    campaign = extended.Campaign(args, images)
    report = dict(schema_version=1, label='baseline-diagnostic', status='RUNNING', images=images,
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scenarios=[],
                  repetitions=args.repetitions, server_selection=args.server_filter,
                  mosquitto_lifetime_seconds=8, limitations=['isolated Will subset, not B08 acceptance'])
    began = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix=campaign.prefix) as temporary:
            root = Path(temporary)
            certs.certificates(root)
            volume = seed_c43(campaign, root)
            for server_kind in ('xmqr', 'mosquitto'):
                if args.server_filter != 'both' and args.server_filter != server_kind:
                    continue
                server = campaign.start_server(server_kind, volume)
                for repetition in range(1, args.repetitions + 1):
                    for publisher, subscriber in [('xmqr', 'mosquitto'), ('mosquitto', 'xmqr')]:
                        trace = dict(server=server_kind, publisher=publisher, subscriber=subscriber,
                                     repetition=repetition, status='RUNNING', timeline={})
                        report['scenarios'].append(trace)
                        start = time.monotonic()
                        recipient = None
                        try:
                            recipient = campaign.job(server, volume, subscriber, 'sub', 1, detached=True)
                            trace['timeline']['recipient_ready_seconds'] = round(time.monotonic() - start, 3)
                            source = campaign.job(server, volume, publisher, 'sub', 1, topic='phase2/#',
                                                  will=True, detached=True)
                            trace['timeline']['will_source_ready_seconds'] = round(time.monotonic() - start, 3)
                            invoke('kill', '--signal', 'KILL', source)
                            trace['timeline']['will_source_killed_seconds'] = round(time.monotonic() - start, 3)
                            output = campaign.finished(recipient)
                            (c43.validate_xmqr if subscriber == 'xmqr' else c43.validate_mosquitto)(
                                output, 1, payload=b'phase2-will')
                            trace['status'] = 'PASS'
                        except Exception as failure:
                            trace.update(status='FAIL', error_type=type(failure).__name__,
                                         error=str(failure) if isinstance(failure, AssertionError)
                                         else 'bounded Will diagnostic operation failed')
                            raise
                        finally:
                            trace['timeline']['finished_seconds'] = round(time.monotonic() - start, 3)
                            if recipient:
                                state = campaign.state(recipient)
                                output = fixture.logs(recipient).lower()
                                trace.update(subscriber_status=state['Status'], subscriber_exit_code=state['ExitCode'],
                                             subscriber_started_utc=state['StartedAt'],
                                             subscriber_finished_utc=state['FinishedAt'],
                                             timed_out=b'timed out' in output,
                                             connection_lost=b'connection was lost' in output,
                                             certificate_error=b'certificate' in output,
                                             received_suback=b'received suback' in output,
                                             logical_events=len(extended.events(fixture.logs(recipient), subscriber)))
                invoke('stop', '--time', '20', server)
                if campaign.state(server)['ExitCode'] != 0:
                    raise AssertionError('Will diagnostic broker graceful stop failed')
        report['status'] = 'PASS'
    except Exception as failure:
        report.update(status='FAIL', error_type=type(failure).__name__,
                      error=str(failure) if isinstance(failure, AssertionError) else 'bounded diagnostic failed')
    finally:
        report['cleanup'] = campaign.close()
        if report['cleanup']['status'] != 'PASS':
            report['status'] = 'FAIL'
        report.update(observed_seconds=round(time.monotonic() - began, 3),
                      completed_utc=datetime.now(timezone.utc).isoformat())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print('PHASE3_WILL_' + report['status'], flush=True)
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
