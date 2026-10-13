# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sync_wifi


class WifiSynchronization(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "source"
        self.target = self.root / "build"
        self.source.mkdir()
        self.target.mkdir()
        self.wifi = {"ssid": "synthetic-test", "password_file": "password.txt"}
        self.original = {"ssid": "old-test", "wifi_password": "old-test-password",
                         "mqtt_url": "mqtts://127.0.0.1:28883", "mqtt_username": "test-user",
                         "mqtt_password": "synthetic-mqtt", "extension": {"keep": True}}
        self.config = self.target / "firmware-config.json"
        self.password = self.source / "password.txt"
        self.password.write_text("new-test-password\r\n", encoding="utf-8")
        self.write_wifi()
        self.config.write_text(json.dumps(self.original), encoding="utf-8")

    def write_wifi(self):
        (self.source / "wifi-config.json").write_text(json.dumps(self.wifi), encoding="utf-8")

    def test_update_preserves_other_fields_and_exact_backup(self):
        before = self.config.read_bytes()
        self.assertTrue(sync_wifi.sync(self.source, self.target))
        expected = self.original | {"ssid": "synthetic-test", "wifi_password": "new-test-password"}
        self.assertEqual(json.loads(self.config.read_text()), expected)
        backups = list(self.target.glob("firmware-config-before-sync-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)

    def test_noop_does_not_write_or_add_backup(self):
        sync_wifi.sync(self.source, self.target)
        before = self.config.stat().st_mtime_ns
        self.assertFalse(sync_wifi.sync(self.source, self.target))
        self.assertEqual(self.config.stat().st_mtime_ns, before)
        self.assertEqual(len(list(self.target.glob("*before-sync*"))), 1)

    def test_preserves_spaces_and_accepts_bom(self):
        self.password.write_bytes(b"\xef\xbb\xbf  synthetic spaces  \r\n")
        sync_wifi.sync(self.source, self.target)
        self.assertEqual(json.loads(self.config.read_text())["wifi_password"], "  synthetic spaces  ")

    def test_password_bounds_and_controls_refused_without_writes(self):
        before = self.config.read_bytes()
        for value in ("short", "z" * 64, "x" * 65, "valid\ninvalid", "abc\0defghi", "abc\tdefgh", "abc\x7fdefgh", "é" * 32):
            with self.subTest(length=len(value)):
                self.password.write_text(value, encoding="utf-8")
                with self.assertRaises(ValueError):
                    sync_wifi.sync(self.source, self.target)
                self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(len(list(self.target.glob("*before-sync*"))), 0)

    def test_64_hexadecimal_is_accepted(self):
        self.password.write_text("aB09" * 16)
        self.assertTrue(sync_wifi.sync(self.source, self.target))

    def test_ssid_utf8_limits(self):
        for value in ("", "é" * 17, "test\nnetwork"):
            self.wifi["ssid"] = value
            self.write_wifi()
            with self.assertRaises(ValueError):
                sync_wifi.sync(self.source, self.target)
        self.wifi["ssid"] = "é" * 16
        self.write_wifi()
        self.assertTrue(sync_wifi.sync(self.source, self.target))

    def test_password_path_escape_and_absolute_refused(self):
        for name in ("../outside.txt", str(self.password.resolve()), "nested/password.txt"):
            self.wifi["password_file"] = name
            self.write_wifi()
            with self.assertRaises(ValueError):
                sync_wifi.sync(self.source, self.target)

    def test_repository_roots_refused(self):
        for source, target in ((sync_wifi.REPO, self.target), (self.source, sync_wifi.REPO)):
            with self.assertRaises(ValueError):
                sync_wifi.sync(source, target)

    def test_external_symlink_refused(self):
        self.password.unlink()
        outside = self.root / "outside.txt"
        outside.write_text("synthetic-password")
        try:
            self.password.symlink_to(outside)
        except OSError:
            self.skipTest("host cannot create symbolic links")
        with self.assertRaises(ValueError):
            sync_wifi.sync(self.source, self.target)

    def test_external_resolution_refused_even_without_symlink_privilege(self):
        resolve = Path.resolve
        outside = self.root / "outside.txt"
        outside.write_text("synthetic-password")

        def redirected(path, *args, **kwargs):
            return outside if path == self.password else resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", redirected):
            with self.assertRaises(ValueError):
                sync_wifi.sync(self.source, self.target)
        self.assertEqual(len(list(self.target.glob("*before-sync*"))), 0)

    def test_missing_target_does_not_create_configuration(self):
        self.config.unlink()
        with self.assertRaises(FileNotFoundError):
            sync_wifi.sync(self.source, self.target)
        self.assertFalse(self.config.exists())
        self.assertEqual(list(self.target.iterdir()), [])

    def test_concurrent_update_is_preserved(self):
        original_read = sync_wifi.read_bounded
        reads = 0

        def competing_read(path):
            nonlocal reads
            if path == self.config:
                reads += 1
                if reads == 2:
                    self.config.write_text("synthetic-concurrent-update")
            return original_read(path)

        with patch.object(sync_wifi, "read_bounded", competing_read):
            with self.assertRaises(ValueError):
                sync_wifi.sync(self.source, self.target)
        self.assertEqual(self.config.read_text(), "synthetic-concurrent-update")
        self.assertEqual(len(list(self.target.glob("*.tmp"))), 0)

    def test_insecure_or_invalid_target_refused(self):
        for value in ({}, self.original | {"mqtt_url": "mqtt://127.0.0.1"},
                      self.original | {"mqtt_url": "mqtts://user:password@localhost"}):
            self.config.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                sync_wifi.sync(self.source, self.target)
        self.assertEqual(len(list(self.target.glob("*before-sync*"))), 0)

    def test_replace_failure_preserves_original_and_backup(self):
        before = self.config.read_bytes()
        with patch.object(sync_wifi.os, "replace", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                sync_wifi.sync(self.source, self.target)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(len(list(self.target.glob("*before-sync*"))), 1)
        self.assertEqual(len(list(self.target.glob("*.tmp"))), 0)

    def test_oversized_input_refused(self):
        self.password.write_bytes(b"x" * (sync_wifi.MAX_INPUT + 1))
        with self.assertRaises(ValueError):
            sync_wifi.sync(self.source, self.target)


if __name__ == "__main__":
    unittest.main()
