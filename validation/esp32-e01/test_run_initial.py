# SPDX-License-Identifier: MIT
from pathlib import Path
import tempfile
import unittest
from argparse import Namespace
import json
from unittest.mock import patch

from run_initial import NAME, VOLUME, finish_lab, monitor, save_report, verified_backups


class BackupGate(unittest.TestCase):
    def test_missing_backup_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                verified_backups(Path(directory))

    def test_partial_backup_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["esptool", "verify"]:
                (root / f"firmware-original-20261013-{name}.bin").write_bytes(b"partial")
            with self.assertRaises(ValueError):
                verified_backups(root)

    def test_different_complete_backups_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "firmware-original-20261013-esptool.bin").write_bytes(bytes(4194304))
            (root / "firmware-original-20261013-verify.bin").write_bytes(b"a" * 4194304)
            with self.assertRaises(ValueError):
                verified_backups(root)

    def test_matching_complete_backups_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["esptool", "verify"]:
                (root / f"firmware-original-20261013-{name}.bin").write_bytes(bytes(4194304))
            self.assertEqual(len(verified_backups(root)), 64)


class MonitorGuards(unittest.TestCase):
    def test_reports_are_unique_and_old_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "initial-result.json"
            old.write_text("historical")
            names = [save_report(root, {"result": "SYNTHETIC"}) for _ in range(2)]
            self.assertNotEqual(*names)
            self.assertEqual(old.read_text(), "historical")
            self.assertEqual(json.loads((root / names[0]).read_text())["result"], "SYNTHETIC")

    def test_monitor_does_not_invoke_docker_or_flash_and_has_no_source_claim(self):
        from evidence import Transcript
        fake_transcript = Transcript()
        fake_transcript.accept(b"E01_BOOT fixture=0.1.0 payload=1024\n")
        fake_transcript.accept(b"E01_FAIL stage=WIFI_TARGET_NOT_FOUND_24GHZ\n")
        fake_transcript.accept(b"E01_STOP\n")
        with tempfile.TemporaryDirectory() as directory:
            args = Namespace(private_dir=Path(directory), serial_port="SYNTHETIC", seconds=1)
            with patch("run_initial.serial.Serial"), patch("run_initial.time.sleep"), \
                 patch("run_initial.collect", return_value=fake_transcript), \
                 patch("run_initial.command") as command:
                report = monitor(args)
            command.assert_not_called()
            self.assertFalse(report["flashed"])
            self.assertIsNone(report["source_sha256"])
            self.assertFalse(report["firmware_identity_verified"])
            self.assertEqual(report["result"], "FAIL_INITIAL_SLICE")

    def test_monitor_markers_cannot_attest_installed_firmware(self):
        from evidence import MILESTONES, Transcript
        fake = Transcript()
        for line in MILESTONES:
            fake.accept((line + "\n").encode())
        with tempfile.TemporaryDirectory() as directory:
            args = Namespace(private_dir=Path(directory), serial_port="SYNTHETIC", seconds=1)
            with patch("run_initial.serial.Serial"), patch("run_initial.time.sleep"), \
                 patch("run_initial.collect", return_value=fake), patch("run_initial.command"):
                report = monitor(args)
            self.assertEqual(report["result"], "OBSERVED_MARKERS_ONLY")
            self.assertFalse(report["phase2_closed"])

    def test_monitor_failure_is_recorded_without_exception_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            args = Namespace(private_dir=Path(directory), serial_port="SYNTHETIC", seconds=1)
            with patch("run_initial.serial.Serial", side_effect=RuntimeError("SYNTHETIC_SECRET")):
                with self.assertRaises(RuntimeError):
                    monitor(args)
            result = next(Path(directory).glob("e01-result-*.json")).read_text()
            self.assertNotIn("SYNTHETIC_SECRET", result)
            self.assertIn("FAIL_MONITOR_OPERATION", result)


class CleanupGuards(unittest.TestCase):
    def test_report_write_failure_cannot_skip_owned_cleanup(self):
        with patch("run_initial.command") as command, \
             patch("run_initial.save_report", side_effect=OSError("SYNTHETIC_SECRET")):
            with self.assertRaises(OSError):
                finish_lab(Path("unused"), {}, True, True)
        self.assertEqual(command.call_count, 3)

    def test_stop_failure_does_not_skip_other_cleanup_or_approve_pass(self):
        report = {"result": "PASS_INITIAL_SLICE"}
        with patch("run_initial.command", side_effect=[RuntimeError("SYNTHETIC_SECRET"), b"", b""]) as command, \
             patch("run_initial.save_report"):
            with self.assertRaises(RuntimeError):
                finish_lab(Path("unused"), report, True, True)
        self.assertEqual(command.call_count, 3)
        self.assertEqual(report["result"], "FAIL_CLEANUP")
        self.assertEqual(report["cleanup_errors"], ["CONTAINER_STOP"])
        self.assertNotIn("SYNTHETIC_SECRET", str(report))
        self.assertEqual(command.call_args_list[1].args[0], ["docker", "rm", NAME])
        self.assertEqual(command.call_args_list[2].args[0], ["docker", "volume", "rm", VOLUME])

    def test_unowned_resources_are_never_removed(self):
        with patch("run_initial.command") as command, patch("run_initial.save_report"):
            finish_lab(Path("unused"), {}, False, False)
        command.assert_not_called()

    def test_every_cleanup_failure_is_retained_only_as_fixed_code(self):
        report = {}
        with patch("run_initial.command", side_effect=RuntimeError("SYNTHETIC_SECRET")), \
             patch("run_initial.save_report"):
            with self.assertRaises(RuntimeError):
                finish_lab(Path("unused"), report, True, True)
        self.assertEqual(report["cleanup_errors"], ["CONTAINER_STOP", "CONTAINER_REMOVE", "VOLUME_REMOVE"])
        self.assertNotIn("SYNTHETIC_SECRET", str(report))


if __name__ == "__main__":
    unittest.main()
