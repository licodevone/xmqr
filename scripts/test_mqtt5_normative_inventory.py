#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent synthetic contracts for the P231 inventory, not MQTT wire tests."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

import mqtt5_normative_inventory as inventory


def document(body, charset="utf-8"):
    text = (
        f'<html><head><meta charset="{charset}"><title>MQTT Version 5.0</title>'
        f'</head><body><p>07 March 2019</p>{body}</body></html>'
    )
    return text.encode(charset)


class NormativeInventoryTests(unittest.TestCase):
    def test_committed_catalog_is_internally_consistent_not_a_verdict(self):
        path = Path(__file__).resolve().parents[1] / 'docs/conformance/mqtt5-normative-audit.json'
        catalog = inventory.json.loads(path.read_text(encoding='utf-8'),
                                       object_pairs_hook=inventory.unique_object)
        rows = catalog['requirements']
        ids = [row['id'] for row in rows]
        self.assertEqual(ids, sorted(set(ids), key=inventory.numeric_key))
        self.assertEqual(len(ids), catalog['unique_ids'])
        self.assertEqual(sum(row['occurrences'] for row in rows), catalog['reference_occurrences'])
        self.assertEqual(dict(inventory.Counter(row['section'].split('.')[0] for row in rows)),
                         catalog['unique_ids_by_chapter'])
        self.assertEqual(catalog['source']['url'], inventory.SOURCE_URL)
        self.assertRegex(catalog['source']['sha256'], r'^[0-9a-f]{64}$')
        self.assertEqual(catalog['audit_status'], 'NOT_AUDITED')
        for row in rows:
            self.assertEqual(row['section'], row['id'].split('-')[1])
            self.assertEqual((row['broker'], row['client']), ('UNREVIEWED', 'UNREVIEWED'))

    def test_inline_markup_and_line_breaks(self):
        catalog = inventory.build_catalog(document(
            '<p>[MQTT-<span>1.5.5</span>-1]</p><p>[MQTT-3.\n1.2-10]</p>'
        ))
        self.assertEqual([r["id"] for r in catalog["requirements"]],
                         ["MQTT-1.5.5-1", "MQTT-3.1.2-10"])

    def test_references_are_deduplicated_not_counted_as_obligations(self):
        catalog = inventory.build_catalog(document(
            '<p>[MQTT-3.1.2-10]</p><p>Appendix B [MQTT-3.1.2-10]</p>'
        ))
        self.assertEqual(catalog["unique_ids"], 1)
        self.assertEqual(catalog["reference_occurrences"], 2)
        self.assertEqual(catalog["requirements"][0]["occurrences"], 2)

    def test_numeric_order(self):
        catalog = inventory.build_catalog(document(
            '[MQTT-3.10.1-1] [MQTT-3.2.1-10] [MQTT-3.2.1-2]'
        ))
        self.assertEqual([r["id"] for r in catalog["requirements"]],
                         ["MQTT-3.2.1-2", "MQTT-3.2.1-10", "MQTT-3.10.1-1"])

    def test_no_template_unbracketed_comment_or_script_ids(self):
        text = inventory.visible_text(
            '[MQTT-x.x.x-y] MQTT-3.1.1-1 '
            '<!-- [MQTT-8.1.1-1] --><script>[MQTT-9.1.1-1]</script>'
            '<style>[MQTT-7.1.1-1]</style>[MQTT-1.5.5-1]'
        )
        self.assertEqual(dict(inventory.extract_ids(text)), {"MQTT-1.5.5-1": 1})

    def test_declared_windows1252_and_exact_raw_hash(self):
        raw = document('<p>· [MQTT-1.5.5-1]</p>', 'windows-1252')
        catalog = inventory.build_catalog(raw)
        self.assertEqual(catalog["source"]["charset"], 'windows-1252')
        self.assertEqual(catalog["source"]["bytes"], len(raw))
        self.assertEqual(catalog["source"]["sha256"], inventory.hashlib.sha256(raw).hexdigest())

    def test_missing_unknown_and_invalid_charset_fail(self):
        for raw in [b'<html></html>', b'<meta charset=unknown>',
                    b'<meta charset=utf-8>\xff']:
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                inventory.decode_source(raw)

    def test_empty_and_oversize_input_fail(self):
        for raw in [b'', b'x' * (inventory.MAX_SOURCE_BYTES + 1)]:
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                inventory.decode_source(raw)

    def test_charset_must_be_real_head_metadata_not_comment_or_body(self):
        for raw in [
            b'<html><head><!-- charset=utf-8 --></head><body>text</body></html>',
            b'<html><head></head><body>charset=utf-8</body></html>',
        ]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                inventory.decode_source(raw)

    def test_conflicting_charset_declarations_fail(self):
        with self.assertRaises(ValueError):
            inventory.decode_source(
                b'<html><head><meta charset=utf-8><meta charset=windows-1252></head></html>'
            )

    def test_wrong_document_and_no_ids_fail(self):
        for raw in [document('no numbered requirements'),
                    document('[MQTT-1.5.5-1]').replace(b'07 March 2019', b'01 April 2000')]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                inventory.build_catalog(raw)

    def test_separate_roles_and_no_inferred_pass(self):
        catalog = inventory.build_catalog(document('[MQTT-1.5.5-1]'))
        self.assertEqual(catalog["audit_status"], "NOT_AUDITED")
        row = catalog["requirements"][0]
        self.assertEqual((row["broker"], row["client"]), ("UNREVIEWED", "UNREVIEWED"))

    def test_catalog_drift_cannot_silently_claim_compliance(self):
        expected = inventory.build_catalog(document('[MQTT-1.5.5-1]'))
        inventory.check_catalog(copy.deepcopy(expected), expected)
        for field, value in [('unique_ids', 2), ('audit_status', 'PASS')]:
            actual = copy.deepcopy(expected)
            actual[field] = value
            with self.assertRaises(ValueError):
                inventory.check_catalog(actual, expected)
        actual = copy.deepcopy(expected)
        actual['requirements'][0]['broker'] = 'PASS'
        with self.assertRaises(ValueError):
            inventory.check_catalog(actual, expected)

    def test_integer_metadata_is_not_boolean(self):
        expected = inventory.build_catalog(document('[MQTT-1.5.5-1]'))
        actual = copy.deepcopy(expected)
        actual['schema_version'] = True
        with self.assertRaises(ValueError):
            inventory.check_catalog(actual, expected)

    def test_cli_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.html'
            catalog = Path(folder) / 'catalog.json'
            raw = document('[MQTT-1.5.5-1]')
            source.write_bytes(raw)
            text = inventory.json.dumps(inventory.build_catalog(raw))
            text = text.replace('"audit_status": "NOT_AUDITED"',
                                '"audit_status": "PASS", "audit_status": "NOT_AUDITED"')
            catalog.write_text(text, encoding='utf-8')
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(inventory.main(['--source', str(source), '--check', str(catalog)]), 1)

    def test_cli_generate_check_drift_and_exclusive_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.html'
            catalog = Path(folder) / 'catalog.json'
            source.write_bytes(document('[MQTT-1.5.5-1]'))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(inventory.main(['--source', str(source), '--output', str(catalog)]), 0)
                original = catalog.read_bytes()
                self.assertEqual(inventory.main(['--source', str(source), '--output', str(catalog)]), 1)
                self.assertEqual(catalog.read_bytes(), original)
                self.assertEqual(inventory.main(['--source', str(source), '--check', str(catalog)]), 0)
                source.write_bytes(document('[MQTT-1.5.5-2]'))
                self.assertEqual(inventory.main(['--source', str(source), '--check', str(catalog)]), 1)


if __name__ == '__main__':
    unittest.main()
