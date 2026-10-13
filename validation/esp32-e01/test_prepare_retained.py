# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_retained


class PrivateRetainedGuards(unittest.TestCase):
    def test_git_root_is_refused_before_tools(self):
        with patch.object(prepare_retained, "run") as tool:
            with self.assertRaises(ValueError):
                prepare_retained.prepare(prepare_retained.REPO, "unused")
            tool.assert_not_called()

    def test_existing_case_config_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "p84-observer.json"
            target.write_text("synthetic-existing")
            with patch.object(prepare_retained, "run") as tool:
                with self.assertRaises(ValueError):
                    prepare_retained.prepare(root, "unused")
                tool.assert_not_called()
            self.assertEqual(target.read_text(), "synthetic-existing")

    def test_bad_identity_is_refused_before_new_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for config in ({"mqtt_username": "unexpected", "mqtt_url": "mqtts://localhost:28883"},
                           {"mqtt_username": "e01-board", "mqtt_url": "mqtt://localhost:28883"}):
                (root / "firmware-config.json").write_text(json.dumps(config))
                with patch.object(prepare_retained, "run") as tool:
                    with self.assertRaises(ValueError):
                        prepare_retained.prepare(root, "unused")
                    tool.assert_not_called()
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_loader_refuses_traversal_git_and_missing_files(self):
        with self.assertRaises(ValueError):
            prepare_retained.load(prepare_retained.REPO)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                prepare_retained.load(root)
            for name in ("../outside", str(root), "p84-case-invalid"):
                (root / "p84-observer.json").write_text(json.dumps({"case_directory": name}))
                with self.assertRaises(ValueError):
                    prepare_retained.load(root)

    def test_loader_accepts_only_distinct_bounded_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "p84-case-" + "a" * 32
            case = root / name
            case.mkdir()
            (case / "broker").mkdir()
            (case / "observer").mkdir()
            original = {"case_directory": name, "username": "e01-observer", "password": "synthetic" * 4}
            config = root / "p84-observer.json"
            config.write_text(json.dumps(original))
            self.assertEqual(prepare_retained.load(root), (case, original))
            for value in (original | {"username": "e01-board"}, original | {"password": "short"}):
                config.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    prepare_retained.load(root)


if __name__ == "__main__":
    unittest.main()
