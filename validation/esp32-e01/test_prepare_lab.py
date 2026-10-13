# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_lab


class PrivateLabGuards(unittest.TestCase):
    def test_repository_is_refused_before_tools(self):
        with patch.object(prepare_lab, "run") as tool:
            with self.assertRaises(ValueError):
                prepare_lab.prepare(prepare_lab.REPO, "127.0.0.1", 28883, "unused")
            tool.assert_not_called()

    def test_existing_certificates_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "certs").mkdir()
            with patch.object(prepare_lab, "run") as tool:
                with self.assertRaises(ValueError):
                    prepare_lab.prepare(root, "127.0.0.1", 28883, "unused")
                tool.assert_not_called()

    def test_password_cannot_escape_private_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "wifi-config.json").write_text(json.dumps({
                "ssid": "synthetic", "password_file": "../outside.txt"
            }))
            with patch.object(prepare_lab, "run") as tool:
                with self.assertRaises(ValueError):
                    prepare_lab.prepare(root, "127.0.0.1", 28883, "unused")
                tool.assert_not_called()

    def test_low_port_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(prepare_lab, "run") as tool:
                with self.assertRaises(ValueError):
                    prepare_lab.prepare(Path(directory), "127.0.0.1", 80, "unused")
                tool.assert_not_called()


if __name__ == "__main__":
    unittest.main()
