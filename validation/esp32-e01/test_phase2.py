# SPDX-License-Identifier: MIT
from argparse import Namespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evidence import CAMPAIGN_MILESTONES, MILESTONES, Transcript, marker
import prepare_phase2
from run_phase2 import Lab, Supervisor, exercise, metrics, payload, validate_external, validate_message


class PhysicalEvidence(unittest.TestCase):
    def test_full_sequence_requires_every_stage(self):
        for removed in (None, *range(len(CAMPAIGN_MILESTONES))):
            state = Transcript(CAMPAIGN_MILESTONES)
            for index, line in enumerate(CAMPAIGN_MILESTONES):
                if index != removed:
                    state.accept((line + "\n").encode())
            self.assertEqual(state.result() == "PASS_PHYSICAL_CAMPAIGN", removed is None)
            self.assertFalse(state.summary()["phase2_closed"])

    def test_old_mode_and_error_veto_campaign(self):
        state = Transcript(CAMPAIGN_MILESTONES)
        for line in MILESTONES:
            state.accept((line + "\n").encode())
        self.assertNotEqual(state.result(), "PASS_PHYSICAL_CAMPAIGN")
        state = Transcript(CAMPAIGN_MILESTONES)
        for line in (*CAMPAIGN_MILESTONES[:-1], "E01_FAIL stage=P85_NEGATIVE_NOT_REJECTED", "E01_STOP"):
            state.accept((line + "\n").encode())
        self.assertEqual(state.result(), "FAIL_INITIAL_SLICE")

    def test_closed_metrics_encoding_bounds_and_private_fields(self):
        for raw in (b"P85_MEMORY stage=idle largest_probe=4097\n", b"P85_MEMORY stage=idle largest_probe=999999\n",
                    b"P85_TIME kind=wifi milliseconds=60001\n", b"P85_TIME kind=wifi milliseconds=0002\n",
                    b"P85_MEMORY stage=idle largest_probe=8192 password=SYNTHETIC\n"):
            self.assertIsNone(marker(raw))
        self.assertIsNotNone(marker(b"P85_MEMORY stage=idle largest_probe=12288\n"))

    def test_metrics_missing_duplicate_drift_and_time_veto(self):
        valid = [f"P85_MEMORY stage={s} largest_probe=65536" for s in ("idle", "wifi", "restart", "final")]
        valid += [f"P85_TIME kind={s} milliseconds=1000" for s in ("wifi", "broker")]
        self.assertFalse(metrics(valid)["total_free_heap_measured"])
        for lines in (valid[:-1], valid + valid[:1], [*valid[:3], "P85_MEMORY stage=final largest_probe=8192", *valid[4:]],
                      [*valid[:-1], "P85_TIME kind=broker milliseconds=60001"]):
            with self.assertRaises(ValueError):
                metrics(lines)

    def test_mosquitto_qos2_retained_and_exact_binary(self):
        valid = f"DATA|2|1|{payload(11).hex()}\n".encode()
        validate_external(valid)
        for output in (valid.replace(b"DATA|2|", b"DATA|1|"), valid.replace(b"|1|", b"|0|"), valid[:-4], b"", valid + valid):
            with self.assertRaises(ValueError):
                validate_external(output)

    def test_wire_topic_payload_qos_and_flag(self):
        topic = b"e01/board/bytes"
        validate_message((topic, 1, False, payload(7)), topic, 7)
        for value in ((topic, 0, False, payload(7)), (topic, 1, True, payload(7)), (topic, 1, False, payload(6))):
            with self.assertRaises(ValueError):
                validate_message(value, topic, 7)

    def test_console_does_not_make_supervisor_complete(self):
        value = Supervisor.__new__(Supervisor)
        value.results = []
        self.assertFalse(value.complete())


class ScopeGuards(unittest.TestCase):
    def test_private_case_refuses_git_and_existing_config_before_tools(self):
        with patch.object(prepare_phase2, "run") as command:
            with self.assertRaises(ValueError):
                prepare_phase2.prepare(prepare_phase2.REPO, "unused")
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory); (root / "p85-case.json").write_text("synthetic-original")
                with self.assertRaises(ValueError):
                    prepare_phase2.prepare(root, "unused")
                self.assertEqual((root / "p85-case.json").read_text(), "synthetic-original")
            command.assert_not_called()

    def test_flash_requires_explicit_authorization_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("run_phase2.command") as command:
                with self.assertRaises(ValueError):
                    exercise(Namespace(private_dir=Path(directory), flash=False))
                command.assert_not_called()

    def test_existing_lab_is_not_removed(self):
        value = Lab(Path("synthetic"), "127.0.0.1", 28883, Path("synthetic"))
        with patch("run_phase2.command") as command:
            self.assertEqual(value.cleanup(), [])
            command.assert_not_called()

    def test_cleanup_attempts_all_owned_resources_despite_errors(self):
        value = Lab(Path("synthetic"), "127.0.0.1", 28883, Path("synthetic"))
        value.container = value.volume = value.network = True
        with patch("run_phase2.command", side_effect=RuntimeError("SYNTHETIC_PRIVATE")) as command:
            result = value.cleanup()
        self.assertEqual(command.call_count, 4)
        self.assertEqual(result, ["CONTAINER_STOP", "CONTAINER_REMOVE", "VOLUME_REMOVE", "NETWORK_REMOVE"])
        self.assertNotIn("SYNTHETIC_PRIVATE", str(result))


if __name__ == "__main__":
    unittest.main()
