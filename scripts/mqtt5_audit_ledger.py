#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate audit accounting; neither inspect protocol semantics nor certify MQTT."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

from mqtt5_normative_inventory import unique_object

ROOT = Path(__file__).resolve().parents[1]
PARTS = ('connect-auth', 'publish-subscribe', 'session-flows', 'framing-transport')
STRENGTHS = {'MUST', 'MUST_NOT', 'SHOULD', 'MAY', 'MIXED'}
APPLICABILITY = {'APPLICABLE', 'CONDITIONAL', 'NOT_APPLICABLE'}
STATUSES = {'SUPPORTED_BY_INSPECTION', 'EVIDENCE_GAP', 'DEVIATION', 'NOT_APPLICABLE'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label}: nonempty string required')


def string_list(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f'{label}: list of nonempty strings required')


def object_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label}: exact object fields required')


def file_reference(reference, root):
    if re.match(r'^[a-zA-Z]:|^[/\\]', reference):
        raise ValueError('file references must be repository-relative')
    relative = re.split(r':\d|#', reference, maxsplit=1)[0]
    path = (root / relative).resolve()
    allowed = [root.resolve(), (root.parent / 'xmqr-client').resolve(),
               (root.parent / 'xmqr-admin').resolve()]
    if not any(path.is_relative_to(base) for base in allowed) or not path.is_file():
        raise ValueError(f'missing or out-of-scope reference: {reference}')


def validate(catalog, parts, *, root=ROOT, check_paths=True):
    if type(catalog['unique_ids']) is not int or catalog['unique_ids'] < 1:
        raise ValueError('catalog unique_ids must be a positive integer')
    expected = [row['id'] for row in catalog['requirements']]
    if len(set(expected)) != len(expected) or catalog['unique_ids'] != len(expected):
        raise ValueError('catalog has duplicate or inconsistent IDs')
    if len(parts) != len(PARTS) or {p['part'] for p in parts} != set(PARTS):
        raise ValueError('exactly four distinct audit partitions required')
    seen, findings = set(), set()
    sources = set()
    counts = {role: Counter() for role in ('broker', 'client')}
    unnumbered = 0
    for part in parts:
        object_keys(part, ('schema_version', 'part', 'broker_commit', 'client_commit',
                          'requirements', 'unnumbered', 'findings'), 'partition')
        if type(part['schema_version']) is not int or part['schema_version'] != 1:
            raise ValueError('unsupported ledger schema')
        pins = (part['broker_commit'], part['client_commit'])
        if any(not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{40}', pin) for pin in pins):
            raise ValueError('full lowercase source SHA required')
        sources.add(pins)
        for field in ('requirements', 'unnumbered', 'findings'):
            if not isinstance(part[field], list):
                raise ValueError(f'{field}: list required')
        for row in part['requirements']:
            object_keys(row, ('id', 'summary', 'strength', 'broker', 'client'), 'requirement')
            identifier = row['id']
            if identifier in seen or identifier not in expected:
                raise ValueError(f'duplicate or unknown ID: {identifier}')
            seen.add(identifier)
            nonempty(row['summary'], identifier)
            if row['strength'] not in STRENGTHS:
                raise ValueError(f'{identifier}: invalid normative strength')
            for role in counts:
                entry = row[role]
                object_keys(entry, ('applicability', 'status', 'rationale', 'code', 'tests', 'evidence'), role)
                if entry['applicability'] not in APPLICABILITY or entry['status'] not in STATUSES:
                    raise ValueError(f'{identifier}/{role}: invalid or unreviewed classification')
                if (entry['applicability'] == 'NOT_APPLICABLE') != (entry['status'] == 'NOT_APPLICABLE'):
                    raise ValueError(f'{identifier}/{role}: unjustified N/A mismatch')
                nonempty(entry['rationale'], f'{identifier}/{role}')
                for field in ('code', 'tests', 'evidence'):
                    string_list(entry[field], f'{identifier}/{role}/{field}')
                if entry['status'] in {'SUPPORTED_BY_INSPECTION', 'DEVIATION'} and not entry['code']:
                    raise ValueError(f'{identifier}/{role}: inspected source reference required')
                if check_paths:
                    for reference in entry['code'] + entry['tests']:
                        file_reference(reference, root)
                counts[role][entry['status']] += 1
        if not isinstance(part['unnumbered'], list) or not part['unnumbered']:
            raise ValueError('unnumbered section review required per partition')
        for entry in part['unnumbered']:
            object_keys(entry, ('section', 'review', 'limitations', 'code', 'tests'), 'unnumbered')
            for field in ('section', 'review', 'limitations'):
                nonempty(entry[field], f'unnumbered/{field}')
            for field in ('code', 'tests'):
                string_list(entry[field], f'unnumbered/{field}')
                if check_paths:
                    for reference in entry[field]:
                        file_reference(reference, root)
            unnumbered += 1
        for finding in part['findings']:
            object_keys(finding, ('id', 'severity', 'summary', 'status', 'next_action',
                                  'clauses', 'code'), 'finding')
            identifier = finding['id']
            if identifier in findings:
                raise ValueError(f'duplicate finding ID: {identifier}')
            findings.add(identifier)
            for field in ('id', 'severity', 'summary', 'status', 'next_action'):
                nonempty(finding[field], f'finding/{field}')
            for field in ('clauses', 'code'):
                string_list(finding[field], f'finding/{field}')
            for clause in finding['clauses']:
                if clause.startswith('MQTT-') and clause not in expected:
                    raise ValueError(f'unknown numbered normative reference: {clause}')
            if check_paths:
                for reference in finding['code']:
                    file_reference(reference, root)
    if len(sources) != 1:
        raise ValueError('audit partitions refer to different code snapshots')
    if seen != set(expected):
        raise ValueError(f'missing numbered IDs: {sorted(set(expected) - seen)}')
    broker, client = sources.pop()
    return {
        'accounting': 'COMPLETE_NUMBERED_REVIEW',
        'compliance': 'NOT_DEMONSTRATED',
        'meaning': 'Classified source review, not execution coverage or certification',
        'broker_commit': broker, 'client_commit': client,
        'unique_numbered_ids': len(seen), 'role_classifications': 2 * len(seen),
        'unnumbered_reviews': unnumbered, 'findings': len(findings),
        'roles': {role: dict(sorted(values.items())) for role, values in counts.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        folder = args.root / 'docs/conformance'
        catalog = load(folder / 'mqtt5-normative-audit.json')
        paths = [folder / f'mqtt5-audit-{part}.json' for part in PARTS]
        result = validate(catalog, [load(path) for path in paths], root=args.root)
        result['ledger_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
