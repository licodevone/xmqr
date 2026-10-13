# SPDX-License-Identifier: MIT
"""Independent negative fixtures for P80 acceptance accounting."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
import benchmark_pressure as b
from test_benchmark_fanout import Peer


class Contracts(unittest.TestCase):
    def test_packet_budget_pauses_before_wall_deadline_without_overrun(self):
        self.assertEqual(b.nonreader_batch(4990, 1, 60), 10)
        self.assertEqual(b.nonreader_batch(4999, 1, 60), 1)
        self.assertEqual(b.nonreader_batch(5000, 1, 60), 0)

    def test_wall_deadline_and_illegal_budget_still_fail(self):
        for sent in (0, 4999, 5000):
            with self.assertRaises(TimeoutError):
                b.nonreader_batch(sent, 60, 60)
        for sent in (-1, 5001):
            with self.assertRaises(AssertionError):
                b.nonreader_batch(sent, 1, 60)

    def test_wrong_ack_does_not_count_as_publish(self):
        with self.assertRaisesRegex(AssertionError, 'identifier'):
            b.publish(Peer([(0x40, b'\0\7')]), 1, 0)

    def test_wrong_drain_order_fails(self):
        body = b.f.text('benchmark/value') + b'\0\1' + (1).to_bytes(8, 'big') + b'x'*248
        with self.assertRaisesRegex(AssertionError, 'ordering'):
            b.drain(Peer([(0x32, body)]), 1, 1)

    def test_wrong_pubrel_cannot_complete_qos2(self):
        body = b.f.text('benchmark/value') + b'\0\1' + b'\0'*8 + b'x'*248
        with self.assertRaisesRegex(AssertionError, 'identifier'):
            b.drain(Peer([(0x34, body), (0x62, b'\0\2')]), 2, 1)

    def test_corrupt_delivery_is_not_success(self):
        with self.assertRaisesRegex(AssertionError, 'mismatch'):
            b.receive_publish(Peer([(0x30, b.f.text('wrong')+b'\0'*256)]), 0, 0)

    def test_cli_rejects_bounds_and_existing_report_before_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root/'report.json'
            report.write_text('preserve')
            common = [sys.executable, '-B', str(Path(b.__file__)), '--broker', '/not-a-binary',
                      '--admin', '/not-a-binary', '--state-root', temporary, '--report', str(report)]
            for tail in ([], ['--repetitions', '0'], ['--limits', '65'], ['--limits', '1', '1']):
                result = subprocess.run(common+tail, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(report.read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
