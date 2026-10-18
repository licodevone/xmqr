#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Luis E. S. Pinheiro
"""P228B read-only audit of existing 0.43.0 publication and downloaded assets.

This never publishes, changes tags, uploads assets, installs software or extracts
arbitrary TARs onto the workstation. Explicit owned input/output paths are required.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_phase3_notices import expected_collection, verify_payload, deb_payload

SOURCE = 'db472bc64558bf0e376a902b7780a259247c5149'
TAG = '89df8f91755e3dbe231a281e1ece9d9881e96b0b'
EVIDENCE = 'phase6-evidence-39164217059.tar.gz'
NOTICES = 'xmqr-broker-0.43.0-original-notices.tar.gz'
MANIFEST = 'xmqr-broker-0.43.0-release-manifest.json'
PRINCIPALS = {'xmqr-broker_0.43.0-1_amd64.deb',
              'xmqr-broker-0.43.0-linux-amd64.tar.gz',
              'xmqr-admin-0.43.0-linux-amd64.tar.gz', MANIFEST}
ORIGINAL = PRINCIPALS | {name + '.sha256' for name in PRINCIPALS}
EXPECTED = ORIGINAL | {EVIDENCE, NOTICES, 'third-party-licenses.md', 'SHA256SUMS'}


def require(value, reason):
    if not value:
        raise AssertionError(reason)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checksum_entry(line):
    match = re.fullmatch(r'([0-9a-f]{64})  ([^/\\]+)', line)
    require(match is not None, 'checksum_syntax')
    return match[2], match[1]


def safe_tar(path):
    require(path.stat().st_size <= 64 * 1024 * 1024, 'archive_compressed_limit')
    result, names, total = {}, set(), 0
    with tarfile.open(path, 'r:gz') as archive:
        for count, member in enumerate(archive, 1):
            require(count <= 20000 and '\\' not in member.name and '\0' not in member.name,
                    'archive_entry_limit')
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts and name.as_posix() not in names,
                    'archive_path')
            names.add(name.as_posix())
            if member.isdir():
                continue
            require(member.isfile() and not member.issym() and not member.islnk()
                    and 0 <= member.size <= 4 * 1024 * 1024, 'archive_regular_file')
            total += member.size
            require(total <= 64 * 1024 * 1024, 'archive_content_limit')
            stream = archive.extractfile(member)
            require(stream is not None, 'archive_read')
            value = stream.read(4 * 1024 * 1024 + 1)
            require(len(value) == member.size, 'archive_file_length')
            result[name.as_posix()] = value
    return result


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], cwd=ROOT))


def verify(args, report):
    release = api('repos/licodevone/xmqr/releases/tags/v0.43.0')
    require(release['id'] == 416718751 and not release['draft'] and release['prerelease'],
            'release_identity')
    tag = api('repos/licodevone/xmqr/git/tags/' + TAG)
    ref = api('repos/licodevone/xmqr/git/ref/tags/v0.43.0')
    require(ref['object']['sha'] == TAG and ref['object']['type'] == 'tag'
            and tag['object']['sha'] == SOURCE and tag['object']['type'] == 'commit', 'tag_provenance')
    require({path.name for path in args.download_dir.iterdir()} == EXPECTED, 'download_asset_set')
    assets = release['assets']
    require(len(assets) == 12 and {item['name'] for item in assets} == EXPECTED, 'release_asset_set')
    results, hashes = [], {}
    for item in sorted(assets, key=lambda value: value['name']):
        name = item['name']
        path = args.download_dir / name
        require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 100_000_000,
                'download_regular_size')
        checksum = sha(path)
        require(path.stat().st_size == item['size'] and item['digest'] == 'sha256:' + checksum,
                'api_asset_hash_size')
        if name in ORIGINAL:
            old = args.local_dir / name
            require(old.stat().st_size == path.stat().st_size and sha(old) == checksum,
                    'original_export_mismatch')
        hashes[name] = checksum
        results.append(dict(file=name, size=item['size'], sha256=checksum))
    for name in PRINCIPALS:
        filename, checksum = checksum_entry((args.download_dir / (name + '.sha256')).read_text().strip())
        require(filename == name and checksum == hashes[name], 'sidecar_mismatch')
    sums = [checksum_entry(line) for line in (args.download_dir / 'SHA256SUMS').read_text().splitlines()]
    require(len(sums) == 11 and {name for name, _ in sums} == EXPECTED - {'SHA256SUMS'}, 'sum_set')
    require(all(hashes[name] == checksum for name, checksum in sums), 'sum_hash')
    manifest = json.loads((args.download_dir / MANIFEST).read_bytes())
    require(manifest['source_revision'] == SOURCE and manifest['version'] == '0.43.0'
            and manifest['experimental'], 'manifest_source')
    for item in manifest['artifacts']:
        require(hashes[item['file']] == item['sha256']
                and (args.download_dir / item['file']).stat().st_size == item['size'], 'manifest_artifact')
    inventory = subprocess.check_output(['git', 'show', SOURCE + ':docs/third-party-licenses.md'], cwd=ROOT)
    published_inventory = (args.download_dir / 'third-party-licenses.md').read_bytes()
    require(published_inventory == (ROOT / 'docs/third-party-licenses.md').read_bytes()
            and published_inventory.replace(b'\r\n', b'\n') == inventory.replace(b'\r\n', b'\n'),
            'inventory_source_bytes')
    inventory_result = dict(comparison='own inventory Markdown: raw equals Windows checkout; CRLF-to-LF only versus Git blob',
                            source_git_blob_sha256=hashlib.sha256(inventory).hexdigest(),
                            published_raw_sha256=hashlib.sha256(published_inventory).hexdigest())
    evidence = safe_tar(args.download_dir / EVIDENCE)
    jsons = []
    with zipfile.ZipFile(args.local_dir / 'xmqr-broker-0.43.0-phase6-evidence.zip') as original:
        require(len(evidence) == 13 and set(evidence) == set(original.namelist()), 'evidence13_set')
        for name, value in sorted(evidence.items()):
            require(value == original.read(name), 'evidence_json_original_bytes')
            json.loads(value)
            jsons.append(dict(file=name, sha256=hashlib.sha256(value).hexdigest()))
    require(hashlib.sha256(evidence['phase6.json']).hexdigest()
            == 'fe2757b81cda6f77a98713e9944bcae2500c7eaaab5bbf4074de34b3ff4f1ec5', 'phase6_sha')
    phase6 = json.loads(evidence['phase6.json'])
    require(phase6['status'] == 'PASS' and len(phase6['scenarios']) == 69
            and all(item['status'] == 'PASS' for item in phase6['scenarios'])
            and phase6['source_unchanged'] and phase6['binaries_unchanged']
            and phase6['legacy_binaries_unchanged'], 'phase6_69')
    source_list = json.loads(evidence['source-checkouts.json'])['sources']
    require(all(item['clean'] for item in source_list), 'source_clean')
    for repository, revision in [('xmqr', SOURCE), ('xmqr-client', '501cde2ffbae6985f033ed8be60d9ad6dd8c18c4'),
                                 ('xmqr-admin', '4483a356196db93f99340bc7aa3b3cabfc4af810')]:
        require(any(item['repository'] == repository and item['revision'] == revision
                    for item in source_list), 'source_revision')
    raw_notices = safe_tar(args.download_dir / NOTICES)
    prefix = 'usr/share/doc/xmqr-broker/'
    require(all(name.startswith(prefix) for name in raw_notices), 'notices_prefix')
    content = {name[len(prefix):]: value for name, value in raw_notices.items()}
    expected, originals = expected_collection(args.source_notices)
    notice_result = verify_payload(content, expected, originals, (ROOT / 'LICENSE').read_bytes(), True)
    require(notice_result['packages'] == 166 and notice_result['original_texts'] == 323, 'notice_counts')
    packaged = deb_payload(args.download_dir / 'xmqr-broker_0.43.0-1_amd64.deb', 'Ubuntu-26.04', 'xmqr-broker')
    require(all(packaged.get(name) == value for name, value in content.items()), 'notices_vs_deb_bytes')
    report.update(status='PASS', authorship='audit of existing publication; no remote writes by this agent',
                  release_url=release['html_url'], release_id=release['id'], published_at=release['published_at'],
                  tag_object=TAG, source_revision=SOURCE, assets=results, evidence_json=jsons,
                  phase6_scenarios=69, notices=notice_result, inventory=inventory_result,
                  source_checkouts=source_list)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-dir', type=Path, required=True)
    parser.add_argument('--download-dir', type=Path, required=True)
    parser.add_argument('--source-notices', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    require(not args.report.exists(), 'report_exists')
    report = dict(status='RUNNING')
    try:
        verify(args, report)
    except Exception as error:
        report.update(status='FAIL', error_type=type(error).__name__, reason=str(error))
    with args.report.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(dict(status=report['status'], assets=len(report.get('assets', [])),
                         evidence_json=len(report.get('evidence_json', [])), reason=report.get('reason'))))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
