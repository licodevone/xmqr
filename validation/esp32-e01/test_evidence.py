# SPDX-License-Identifier: MIT
import unittest

from evidence import BOOT, MAX_MARKERS, MAX_TOTAL_BYTES, MILESTONES, RETAINED_MILESTONES, Transcript, collect, marker


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        self.now += .01
        return self.now


class Stream:
    def __init__(self, data, fragment=128):
        self.data = data
        self.fragment = fragment

    def read(self, size):
        count = min(size, self.fragment, len(self.data))
        value, self.data = self.data[:count], self.data[count:]
        return value


def transcript(lines):
    state = Transcript()
    for line in lines:
        state.accept((line + "\n").encode())
    return state


class Evidence(unittest.TestCase):
    def test_retained_sequence_is_required_in_retained_mode(self):
        state = collect(Stream(("\n".join(RETAINED_MILESTONES) + "\n").encode()), clock=Clock(),
                        milestones=RETAINED_MILESTONES)
        self.assertEqual(state.result(), "PASS_RETAINED_SLICE")
        self.assertFalse(state.summary()["phase2_closed"])

    def test_old_sequence_cannot_pass_retained_mode(self):
        state = Transcript(RETAINED_MILESTONES)
        for line in MILESTONES:
            state.accept((line + "\n").encode())
        self.assertEqual(state.result(), "FAIL_TRANSCRIPT")

    def test_each_missing_retained_marker_and_wrong_mode_veto(self):
        for index in range(len(RETAINED_MILESTONES)):
            state = Transcript(RETAINED_MILESTONES)
            for line in RETAINED_MILESTONES[:index] + RETAINED_MILESTONES[index + 1:]:
                state.accept((line + "\n").encode())
            self.assertNotEqual(state.result(), "PASS_RETAINED_SLICE")
        self.assertEqual(transcript(RETAINED_MILESTONES).result(), "FAIL_TRANSCRIPT")

    def test_retained_fail_and_unknown_fields_veto(self):
        state = Transcript(RETAINED_MILESTONES)
        for line in (*RETAINED_MILESTONES[:-1], "E01_FAIL stage=OBSERVER_CONFIRM_TIMEOUT", "E01_STOP"):
            state.accept((line + "\n").encode())
        self.assertEqual(state.result(), "FAIL_INITIAL_SLICE")
        self.assertIsNone(marker(b"E01_RETAINED_STORED version=1 bytes=1024 password=SYNTHETIC\n"))

    def test_complete_ordered_sequence_passes_initial_slice_only(self):
        state = transcript(MILESTONES)
        self.assertEqual(state.result(), "PASS_INITIAL_SLICE")
        self.assertFalse(state.summary()["phase2_closed"])

    def test_each_missing_milestone_prevents_pass(self):
        for index in range(len(MILESTONES)):
            with self.subTest(index=index):
                state = transcript(MILESTONES[:index] + MILESTONES[index + 1:])
                self.assertNotEqual(state.result(), "PASS_INITIAL_SLICE")

    def test_reordered_milestones_fail(self):
        lines = list(MILESTONES)
        lines[1], lines[2] = lines[2], lines[1]
        self.assertEqual(transcript(lines).result(), "FAIL_TRANSCRIPT")

    def test_fail_vetoes_apparent_pass(self):
        lines = (*MILESTONES[:-1], "E01_FAIL stage=BYTES_OR_DELIVERY", "E01_STOP")
        self.assertEqual(transcript(lines).result(), "FAIL_INITIAL_SLICE")

    def test_real_wifi_failure_is_a_failure_not_invalid_transcript(self):
        state = transcript([BOOT, "E01_FAIL stage=WIFI_TARGET_NOT_FOUND_24GHZ", "E01_STOP"])
        self.assertEqual(state.result(), "FAIL_INITIAL_SLICE")

    def test_reboot_and_duplicate_milestones_fail(self):
        for line in MILESTONES:
            with self.subTest(line=line):
                state = transcript([*MILESTONES[:1], line, *MILESTONES[1:]])
                self.assertEqual(state.result(), "FAIL_TRANSCRIPT")

    def test_stop_alone_is_not_success(self):
        self.assertEqual(transcript(["E01_STOP"]).result(), "FAIL_TRANSCRIPT")

    def test_fail_before_boot_is_not_valid_evidence(self):
        self.assertEqual(transcript(["E01_FAIL stage=WIFI_CONNECT", "E01_STOP"]).result(), "FAIL_TRANSCRIPT")

    def test_diagnostics_before_boot_are_rejected(self):
        state = transcript(["E01_WIFI_ASSOCIATED", *MILESTONES])
        self.assertEqual(state.result(), "FAIL_TRANSCRIPT")

    def test_known_diagnostics_after_boot_do_not_break_sequence(self):
        lines = [BOOT, "E01_WIFI_AP_FOUND channel=6 rssi=-42",
                 "E01_WIFI_AP_AUTH method=WPA2Personal", "E01_WIFI_ASSOCIATED",
                 *MILESTONES[1:]]
        self.assertEqual(transcript(lines).result(), "PASS_INITIAL_SLICE")

    def test_secrets_and_unknown_fields_are_never_returned(self):
        synthetic = [b"E01_PASSWORD value=SYNTHETIC_SECRET\n",
                     b"E01_WIFI_UP password=SYNTHETIC_SECRET\n",
                     b"E01_FAIL stage=SYNTHETIC_SECRET\n",
                     b"E01_WIFI_AP_AUTH method=SYNTHETIC_SECRET\n"]
        for raw in synthetic:
            with self.subTest(raw=raw):
                state = Transcript()
                self.assertIsNone(state.accept(raw))
                self.assertNotIn("SYNTHETIC_SECRET", str(state.summary()))
                self.assertEqual(state.result(), "FAIL_TRANSCRIPT")

    def test_prefix_invalid_ascii_and_missing_newline_do_not_parse(self):
        for raw in [b"prefix E01_WIFI_UP\n", b" E01_WIFI_UP\n", b"E01_WIFI_UP\xff\n",
                    b"E01_WIFI_UP", b"E01_WIFI_UP \n", b"E01_STOP\r\r\n"]:
            self.assertIsNone(marker(raw))

    def test_crlf_is_valid(self):
        self.assertEqual(marker(b"E01_WIFI_UP\r\n"), "E01_WIFI_UP")

    def test_numeric_diagnostic_bounds(self):
        for raw in [b"E01_WIFI_AP_FOUND channel=0 rssi=-42\n",
                    b"E01_WIFI_AP_FOUND channel=15 rssi=-42\n",
                    b"E01_WIFI_AP_FOUND channel=1 rssi=-128\n",
                    b"E01_WIFI_AP_FOUND channel=1 rssi=1\n",
                    b"E01_WIFI_DISCONNECTED reason=65536\n",
                    b"E01_WIFI_DISCONNECTED reason=00001\n"]:
            self.assertIsNone(marker(raw))
        self.assertEqual(marker(b"E01_WIFI_DISCONNECTED reason=65535\n"),
                         "E01_WIFI_DISCONNECTED reason=65535")

    def test_marker_count_is_bounded(self):
        state = transcript([BOOT] + ["E01_WIFI_ASSOCIATED"] * MAX_MARKERS)
        self.assertEqual(len(state.markers), MAX_MARKERS)
        self.assertIn("MARKER_LIMIT", state.violations)

    def test_fragmented_serial_sequence(self):
        data = ("\r\n".join(MILESTONES) + "\r\n").encode()
        for fragment in [1, 3, 7, 128]:
            with self.subTest(fragment=fragment):
                emitted = []
                state = collect(Stream(data, fragment), seconds=20, clock=Clock(), emit=emitted.append)
                self.assertEqual(state.result(), "PASS_INITIAL_SLICE")
                self.assertEqual(emitted, list(MILESTONES))

    def test_long_line_cannot_be_truncated_into_pass(self):
        data = BOOT.encode() + b"\n" + b"x" * 600 + b"\n" + b"E01_STOP\n"
        state = collect(Stream(data), seconds=5, clock=Clock())
        self.assertIn("LINE_LIMIT", state.violations)
        self.assertNotEqual(state.result(), "PASS_INITIAL_SLICE")

    def test_total_byte_budget_counts_discarded_noise(self):
        state = collect(Stream(b"x\n" * 40000), seconds=100, clock=Clock())
        self.assertIn("BYTE_LIMIT", state.violations)
        self.assertFalse(state.markers)
        self.assertLessEqual(state.total_bytes, MAX_TOTAL_BYTES)

    def test_timeout_is_bounded_and_not_success(self):
        state = collect(Stream(b""), seconds=1, clock=Clock())
        self.assertIn("TIMEOUT", state.violations)
        self.assertNotEqual(state.result(), "PASS_INITIAL_SLICE")

    def test_partial_last_line_cannot_be_accepted(self):
        state = collect(Stream(BOOT.encode()), seconds=1, clock=Clock())
        self.assertIn("PARTIAL_LINE", state.violations)
        self.assertFalse(state.markers)

    def test_fail_after_stop_in_same_chunk_vetoes_pass(self):
        data = ("\n".join((*MILESTONES, "E01_FAIL stage=PUBLISH")) + "\n").encode()
        state = collect(Stream(data), seconds=10, clock=Clock())
        self.assertNotEqual(state.result(), "PASS_INITIAL_SLICE")

    def test_fail_after_stop_in_next_chunk_vetoes_pass(self):
        data = ("\n".join((*MILESTONES, "E01_FAIL stage=PUBLISH")) + "\n").encode()
        state = collect(Stream(data, fragment=1), seconds=20, clock=Clock())
        self.assertNotEqual(state.result(), "PASS_INITIAL_SLICE")

    def test_bad_read_contract_is_rejected(self):
        class BadStream:
            def read(self, size):
                return b"x" * (size + 1)
        state = collect(BadStream(), seconds=1, clock=Clock())
        self.assertIn("READ_CONTRACT", state.violations)

    def test_invalid_deadlines_are_refused(self):
        for seconds in [0, 181, -1, True, 1.5]:
            with self.assertRaises(ValueError):
                collect(Stream(b""), seconds=seconds, clock=Clock())


if __name__ == "__main__":
    unittest.main()
