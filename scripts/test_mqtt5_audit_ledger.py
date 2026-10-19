#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic negative accounting tests, not protocol conformance tests."""
import copy
from pathlib import Path
import tempfile
import unittest

import mqtt5_audit_ledger as ledger


def fixtures():
    role = dict(applicability='APPLICABLE', status='SUPPORTED_BY_INSPECTION',
                rationale='Synthetic inspected condition', code=['src/example.rs'], tests=[], evidence=[])
    row = dict(id='MQTT-1.5.5-1', summary='Synthetic summary', strength='MUST',
               broker=copy.deepcopy(role), client=copy.deepcopy(role))
    parts = [dict(schema_version=1, part=name, broker_commit='a' * 40, client_commit='b' * 40,
                  requirements=[], unnumbered=[dict(section='1.5', review='Synthetic rule reviewed',
                  limitations='No protocol run', code=[], tests=[])], findings=[]) for name in ledger.PARTS]
    parts[0]['requirements'] = [row]
    catalog = dict(unique_ids=1, requirements=[dict(id='MQTT-1.5.5-1')])
    return catalog, parts


class AuditLedgerContracts(unittest.TestCase):
    def test_complete_accounting_never_claims_compliance(self):
        catalog, parts = fixtures()
        result = ledger.validate(catalog, parts, check_paths=False)
        self.assertEqual(result['accounting'], 'COMPLETE_NUMBERED_REVIEW')
        self.assertEqual(result['compliance'], 'NOT_DEMONSTRATED')
        self.assertEqual(result['role_classifications'], 2)

    def test_missing_duplicate_and_unknown_ids_fail(self):
        for mode in ('missing', 'duplicate', 'unknown'):
            catalog, parts = fixtures()
            if mode == 'missing':
                parts[0]['requirements'] = []
            elif mode == 'duplicate':
                parts[1]['requirements'] = copy.deepcopy(parts[0]['requirements'])
            else:
                parts[0]['requirements'][0]['id'] = 'MQTT-9.9-1'
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                ledger.validate(catalog, parts, check_paths=False)

    def test_no_unreviewed_or_dynamic_pass_by_inspection(self):
        for status in ('UNREVIEWED', 'PASS', 'CERTIFIED'):
            catalog, parts = fixtures()
            parts[0]['requirements'][0]['client']['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                ledger.validate(catalog, parts, check_paths=False)

    def test_na_requires_matching_applicability(self):
        catalog, parts = fixtures()
        parts[0]['requirements'][0]['client']['status'] = 'NOT_APPLICABLE'
        with self.assertRaises(ValueError):
            ledger.validate(catalog, parts, check_paths=False)

    def test_missing_rationale_or_inspected_code_fail(self):
        for field, value in [('rationale', ''), ('code', [])]:
            catalog, parts = fixtures()
            parts[0]['requirements'][0]['client'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                ledger.validate(catalog, parts, check_paths=False)

    def test_source_drift_and_boolean_schema_fail(self):
        for field, value in [('broker_commit', 'c' * 40), ('schema_version', True)]:
            catalog, parts = fixtures()
            parts[1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                ledger.validate(catalog, parts, check_paths=False)

    def test_unnumbered_review_and_findings_must_be_explicit(self):
        catalog, parts = fixtures()
        parts[0]['unnumbered'] = []
        with self.assertRaises(ValueError):
            ledger.validate(catalog, parts, check_paths=False)

    def test_reference_cannot_escape_repository_or_be_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'xmqr'
            root.mkdir()
            for reference in ('/etc/passwd', '../../outside.txt', 'missing.rs'):
                with self.subTest(reference=reference), self.assertRaises(ValueError):
                    ledger.file_reference(reference, root)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.json'
            path.write_text('{"status":"PASS","status":"UNREVIEWED"}')
            with self.assertRaises(ValueError):
                ledger.load(path)

    def test_unknown_fields_cannot_smuggle_a_certificate(self):
        for location in ('partition', 'requirement', 'role', 'unnumbered'):
            catalog, parts = fixtures()
            target = {'partition': parts[0], 'requirement': parts[0]['requirements'][0],
                      'role': parts[0]['requirements'][0]['client'],
                      'unnumbered': parts[0]['unnumbered'][0]}[location]
            target['certified'] = True
            with self.subTest(location=location), self.assertRaises(ValueError):
                ledger.validate(catalog, parts, check_paths=False)

    def test_boolean_catalog_count_fails(self):
        catalog, parts = fixtures()
        catalog['unique_ids'] = True
        with self.assertRaises(ValueError):
            ledger.validate(catalog, parts, check_paths=False)

    def test_list_fields_are_not_dictionary_shaped(self):
        catalog, parts = fixtures()
        parts[0]['findings'] = {}
        with self.assertRaises(ValueError):
            ledger.validate(catalog, parts, check_paths=False)

    def test_finding_cannot_cite_a_nonexistent_numbered_requirement(self):
        catalog, parts = fixtures()
        parts[0]['findings'] = [dict(id='example', severity='medium', summary='Synthetic gap',
                                    status='EVIDENCE_GAP', next_action='Review source',
                                    clauses=['MQTT-4.13.1-2'], code=[])]
        with self.assertRaises(ValueError):
            ledger.validate(catalog, parts, check_paths=False)


if __name__ == '__main__':
    unittest.main()
