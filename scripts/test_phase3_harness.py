#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic parser/assertion contracts for P91, with no broker/Docker."""
import json
import unittest

import phase3_soak as soak
import verify_phase3_interop as external


class HarnessContracts(unittest.TestCase):
    def output(self, values, qos=1, retain=False):
        return b'\n'.join(json.dumps(dict(event='publish', topic='phase2/value', qos=qos,
                                        retain=retain, payload_bytes=list(value))).encode() for value in values)

    def test_sequence_payload_exactly_1024_and_distinct(self):
        self.assertEqual(len(soak.payload(0)), 1024)
        self.assertEqual(soak.payload(1)[:8], b'\0' * 7 + b'\1')
        self.assertNotEqual(soak.payload(0), soak.payload(1))

    def test_qos1_replay_is_not_false_failure(self):
        self.assertEqual(external.validate_logical(self.output([b'a', b'a', b'b']),
                                                  'xmqr', [b'a', b'b'], 1), 1)

    def test_missing_logical_sequence_is_failure_even_with_duplicate(self):
        with self.assertRaises(AssertionError):
            external.validate_logical(self.output([b'a', b'a']), 'xmqr', [b'a', b'b'], 1)

    def test_qos2_duplicate_application_delivery_is_failure(self):
        with self.assertRaises(AssertionError):
            external.validate_logical(self.output([b'a', b'a'], qos=2), 'xmqr', [b'a'], 2)

    def test_wrong_qos_and_retain_are_failures(self):
        for data in (self.output([b'a'], qos=0), self.output([b'a'], retain=True)):
            with self.assertRaises(AssertionError):
                external.validate_logical(data, 'xmqr', [b'a'], 1)

    def test_external_mosquitto_binary_bytes_parser(self):
        value = b'\0\xff\r\n'
        output = b'debug\nDATA|phase2/value|2|1|' + value.hex().encode() + b'\n'
        self.assertEqual(external.validate_logical(output, 'mosquitto', [value], 2, retained=True), 0)

    def test_unknown_bytes_are_not_silently_filtered(self):
        with self.assertRaises(AssertionError):
            external.validate_logical(self.output([b'wrong']), 'xmqr', [b'a'], 1)


if __name__ == '__main__':
    unittest.main()
