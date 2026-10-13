# SPDX-License-Identifier: MIT
from pathlib import Path
import tempfile
import unittest

from run_initial import verified_backups


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


if __name__ == "__main__":
    unittest.main()
