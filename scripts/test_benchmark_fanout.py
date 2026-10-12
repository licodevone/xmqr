# SPDX-License-Identifier: MIT
"""P72 negative contracts: corrupt delivery, ACK identity and unsafe CLI inputs."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
import benchmark_fanout as b


class Peer:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.sent = []

    def send(self, header, body=b''):
        self.sent.append((header, body))

    def receive(self):
        return next(self.replies)


class Contracts(unittest.TestCase):
    def test_corrupt_sequence_cannot_count_as_delivery(self):
        subscriber = Peer([(0x30, b.f.text('benchmark/value') + b'\0' * 8)])
        with self.assertRaisesRegex(AssertionError, 'mismatch'):
            b.delivery(Peer([]), [subscriber], 0, 1, 8)

    def test_wrong_publisher_ack_identifier_fails(self):
        with self.assertRaisesRegex(AssertionError, 'identifier'):
            b.delivery(Peer([(0x40, b'\0\x02')]), [], 1, 0, 8)

    def test_qos2_requires_both_direction_handshakes(self):
        publisher = Peer([(0x50, b'\0\x01'), (0x70, b'\0\x01')])
        subscriber = Peer([(0x34, b.f.text('benchmark/value') + b'\0\x07' + b'\0' * 8),
                           (0x62, b'\0\x07')])
        b.delivery(publisher, [subscriber], 2, 0, 8)
        self.assertEqual(publisher.sent[-1], (0x62, b'\0\x01'))
        self.assertEqual(subscriber.sent, [(0x50, b'\0\x07'), (0x70, b'\0\x07')])

    @unittest.skipUnless(sys.platform == 'linux', 'Linux benchmark CLI')
    def test_invalid_bounds_and_existing_report_refused_before_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / 'existing.json'
            report.write_text('preserve')
            common = [sys.executable, '-B', str(Path(b.__file__)), '--broker', '/bin/false',
                      '--admin', '/bin/false', '--state-root', temporary, '--report', str(report)]
            for tail, diagnostic in [([], 'report exists'), (['--messages', '0'], 'bounds'),
                                     (['--fanouts', '1', '1'], 'bounds'),
                                     (['--fanouts', '64'], 'bounds')]:
                result = subprocess.run(common + tail, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual(report.read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
