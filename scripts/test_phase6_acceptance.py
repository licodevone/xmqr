#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic contracts for the finite phase6 coordinator."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from verify_phase6_acceptance import classify, execute, failure_diagnostic, fixtures, inspect_legacy, legacy_inputs, verify_versions


class AcceptanceContracts(unittest.TestCase):
    def test_zero_exit_needs_success_marker(self):
        self.assertEqual(classify(0, "nothing happened", "PASS"), ("FAIL", "success_marker_missing"))

    def test_nonzero_exit_cannot_become_success(self):
        self.assertEqual(classify(1, "P227_TEST_PASS", "PASS"), ("FAIL", "nonzero_exit"))

    def test_specific_marker_is_not_a_substring(self):
        self.assertEqual(classify(0, "NOT_P227_PASS", "P227_PASS"), ("FAIL", "negative_marker_present"))
        self.assertEqual(classify(0, "OTHER_P227_PASS", "P227_PASS"), ("FAIL", "success_marker_missing"))

    def test_current_named_markers_pass(self):
        self.assertEqual(classify(0, "P190_PUBLISH_FLAGS_PASS\n", "P190_PUBLISH_FLAGS_PASS"), ("PASS", None))
        self.assertEqual(classify(0, "PASS: valid\n", "PASS: valid"), ("PASS", None))
        self.assertEqual(classify(0, "UNRELATED_PASS\n", "P190_PUBLISH_FLAGS_PASS"),
                         ("FAIL", "success_marker_missing"))

    def test_timeout_is_not_success(self):
        self.assertEqual(classify(0, "PASS", "PASS", timed_out=True), ("FAIL", "timeout"))

    def test_negative_markers_cannot_be_success(self):
        for marker in ("NOT_PASS", "NOT_P227_PASS", "NOT_P190_PUBLISH_FLAGS_PASS",
                       "FAIL", "FAILED", "P227_CASE_FAIL", "BLOCKED", "SKIPPED"):
            self.assertEqual(classify(0, marker + "\nP227_CASE_PASS", "PASS"),
                             ("FAIL", "negative_marker_present"))

    def test_failure_diagnostic_has_no_private_message_or_path(self):
        result = failure_diagnostic(b'  File "/private-fixture-token.py", line 42, in main\nValueError: private-fixture-token\n')
        self.assertEqual(result, {"diagnostic_exception_type": "ValueError", "diagnostic_line": 42})
        self.assertNotIn("private-fixture-token", json.dumps(result))

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
        self.assertTrue(all(row["expected_marker"] and row["expected_marker"] != "PASS" for row in rows))

    def test_multiline_markers_require_every_line_in_order(self):
        self.assertEqual(classify(0, "FIRST_PASS\n", ["FIRST_PASS", "LAST_PASS"]),
                         ("FAIL", "success_marker_missing"))
        self.assertEqual(classify(0, "LAST_PASS\nFIRST_PASS\n", ["FIRST_PASS", "LAST_PASS"]),
                         ("FAIL", "success_marker_missing"))
        self.assertEqual(classify(0, "FIRST_PASS\nLAST_PASS\n", ["FIRST_PASS", "LAST_PASS"]),
                         ("PASS", None))

    def test_real_migrations_require_explicit_separate_inputs(self):
        rows = {row["file"]: row for row in fixtures(Path(__file__).resolve().parents[1])}
        self.assertNotIn("../../xmqr-admin/scripts/verify_core_028_state_v15.py", rows)
        for filename, role, flag in (
            ("../../xmqr-admin/scripts/verify_core_v16_expiry.py", "legacy_broker", "--legacy-broker"),
            ("../../xmqr-client/scripts/verify_c129_v1_migration.py", "legacy_client", "--legacy-client"),
        ):
            row = rows[filename]
            self.assertEqual(row["phase"], "6B")
            self.assertEqual(legacy_inputs(row, {}), [role])
            self.assertEqual(legacy_inputs(row, {role: Path("explicit-legacy")}), [])
            self.assertEqual(row["arguments"][row["arguments"].index(flag) + 1], "{" + role + "}")
        for row in rows.values():
            if row["phase"] != "6B":
                self.assertEqual(legacy_inputs(row, {}), [])

    def test_missing_legacy_is_not_silently_replaced_by_current(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                inspect_legacy(Path(directory) / "missing")

    @unittest.skipUnless(os.name == "posix", "executable script fixture requires Linux/WSL")
    def test_legacy_version_is_identified_not_matched_to_current_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy"
            path.write_text("#!/bin/sh\nprintf 'legacy 0.1.0\\n'\n")
            path.chmod(0o700)
            resolved, info = inspect_legacy(path)
            self.assertEqual(resolved, path.resolve())
            self.assertEqual(info["version"], "legacy 0.1.0")
            self.assertEqual(len(info["sha256"]), 64)

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

    @unittest.skipUnless(os.name == "posix", "private process groups require Linux/WSL")
    def test_negative_stderr_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            row = execute([sys.executable, "-c", "import sys; print('PASS'); print('BLOCKED',file=sys.stderr)"],
                          "PASS", 3, Path(directory), dict(os.environ))
        self.assertEqual(row["reason"], "negative_marker_present")

    @unittest.skipUnless(os.name == "posix", "private process groups require Linux/WSL")
    def test_success_cannot_leave_a_private_child_running(self):
        with tempfile.TemporaryDirectory() as directory:
            row = execute([sys.executable, "-c",
                           "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)']); print('PASS')"],
                          "PASS", 3, Path(directory), dict(os.environ))
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["reason"], "private_descendants_remaining")
        self.assertEqual(row["cleanup"], "REMAINING_GROUP_KILLED")

    @unittest.skipUnless(os.name == "posix", "private process groups require Linux/WSL")
    def test_output_is_bounded_without_temporary_log_files(self):
        with tempfile.TemporaryDirectory() as directory:
            row = execute([sys.executable, "-c", "import sys; sys.stdout.write('x'*1048576)"],
                          "PASS", 3, Path(directory), dict(os.environ))
        self.assertEqual(row["reason"], "output_budget_exceeded")
        self.assertEqual(row["stdout_bytes"], 262145)


if __name__ == "__main__":
    unittest.main()
