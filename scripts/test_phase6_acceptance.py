#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic contracts for the finite phase6 coordinator."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from verify_phase6_acceptance import classify, execute, fixtures, verify_versions


class AcceptanceContracts(unittest.TestCase):
    def test_zero_exit_needs_success_marker(self):
        self.assertEqual(classify(0, "nothing happened", "PASS"), ("FAIL", "success_marker_missing"))

    def test_nonzero_exit_cannot_become_success(self):
        self.assertEqual(classify(1, "P227_TEST_PASS", "PASS"), ("FAIL", "nonzero_exit"))

    def test_specific_marker_is_not_a_substring(self):
        self.assertEqual(classify(0, "NOT_P227_PASS", "P227_PASS"), ("FAIL", "success_marker_missing"))

    def test_current_named_markers_pass(self):
        self.assertEqual(classify(0, "P190_PUBLISH_FLAGS_PASS\n", "PASS"), ("PASS", None))
        self.assertEqual(classify(0, "PASS: valid\n", "PASS"), ("PASS", None))

    def test_timeout_is_not_success(self):
        self.assertEqual(classify(0, "PASS", "PASS", timed_out=True), ("FAIL", "timeout"))

    def test_negative_markers_cannot_be_success(self):
        for marker in ("NOT_PASS", "FAIL", "P227_CASE_FAIL", "BLOCKED"):
            self.assertEqual(classify(0, marker + "\nP227_CASE_PASS", "PASS"),
                             ("FAIL", "negative_marker_present"))

    def test_manifest_binary_versions_match(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for repo, version in (("xmqr", "0.42.0"), ("xmqr-client", "0.36.0"), ("xmqr-admin", "0.10.0")):
                (base / repo).mkdir()
                (base / repo / "Cargo.toml").write_text('[package]\nversion="' + version + '"\n')
            info = {role: {"version": "binary " + version} for role, version in
                    (("broker", "0.42.0"), ("admin", "0.42.0"), ("client", "0.36.0"),
                     ("client_release", "0.36.0"), ("independent_admin", "0.10.0"))}
            verify_versions(base / "xmqr", info)
            info["broker"]["version"] = "mqtt-broker 0.41.0"
            with self.assertRaisesRegex(RuntimeError, "manifest_binary_version_mismatch:broker"):
                verify_versions(base / "xmqr", info)

    def test_registry_is_unique_and_excludes_obsolete_shared_refusal(self):
        rows = fixtures(Path(__file__).resolve().parents[1])
        self.assertEqual(len(rows), len({row["file"] for row in rows}))
        self.assertNotIn("verify_mqtt5_shared_unavailable.py", {row["file"] for row in rows})
        self.assertEqual({row["phase"] for row in rows}, {"6A", "6B", "6C", "6D"})
        self.assertTrue(all(row["timeout_seconds"] <= 240 for row in rows))

    def test_explicit_candidate_label_is_present_for_required_harnesses(self):
        rows = {row["file"]: row for row in fixtures(Path(__file__).resolve().parents[1])}
        for name in ("verify_phase6_vbi.py", "verify_phase6_alias_reason.py"):
            args = rows[name]["arguments"]
            self.assertIn("--label", args)
            self.assertEqual(args[args.index("--label") + 1], "candidate")

    @unittest.skipUnless(os.name == "posix", "private process groups require Linux/WSL")
    def test_failure_does_not_disclose_output(self):
        with tempfile.TemporaryDirectory() as directory:
            row = execute([sys.executable, "-c", "import sys; print('private-fixture-token'); sys.exit(1)"],
                          "PASS", 3, Path(directory), dict(os.environ))
        self.assertEqual(row["status"], "FAIL")
        self.assertNotIn("private-fixture-token", json.dumps(row))
        self.assertEqual(len(row["stdout_sha256"]), 64)

    @unittest.skipUnless(os.name == "posix", "private process groups require Linux/WSL")
    def test_timeout_stops_only_private_child(self):
        with tempfile.TemporaryDirectory() as directory:
            row = execute([sys.executable, "-c", "import time; time.sleep(3)"],
                          "PASS", .05, Path(directory), dict(os.environ))
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["reason"], "timeout")


if __name__ == "__main__":
    unittest.main()
