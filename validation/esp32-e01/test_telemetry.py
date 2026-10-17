# SPDX-License-Identifier: MIT
"""Host-side validation of the physical subscriber transcript."""
import json
import unittest

from run_telemetry import TOPIC, verify_messages


def frame(seq, *, run_id=42, topic=TOPIC, temperature=20.0, humidity=40.0):
    payload = json.dumps({"run_id": run_id, "seq": seq, "temperature_c": temperature,
                          "humidity_pct": humidity, "source": "simulated"}).encode()
    return json.dumps({"event": "publish", "topic": topic, "qos": 1, "retain": False,
                       "payload_bytes": list(payload)}).encode()


class TranscriptTests(unittest.TestCase):
    def test_accepts_five_ordered_varying_samples_from_one_run(self):
        verify_messages([frame(index, temperature=20.0 + index) for index in range(1, 6)])

    def test_rejects_missing_duplicate_foreign_or_out_of_range_sample(self):
        valid = [frame(index, temperature=20.0 + index) for index in range(1, 6)]
        for bad in (valid[:-1],
                    valid[:2] + [valid[1]] + valid[3:],
                    valid[:2] + [frame(3, run_id=43)] + valid[3:],
                    valid[:2] + [frame(3, topic="other")] + valid[3:],
                    valid[:2] + [frame(3, temperature=31.0)] + valid[3:]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    verify_messages(bad)


if __name__ == "__main__":
    unittest.main()
