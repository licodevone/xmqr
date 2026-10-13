#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic parser/assertion contracts for P91, with no broker/Docker."""
import json
from pathlib import Path
import queue
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import phase3_soak as soak
from test_phase3_health import wait_healthy
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

    def test_primary_failure_survives_parallel_secondary_cancellation(self):
        class Laboratory:
            def __init__(self, *_):
                self.stage = 'synthetic_failure'
                self.operation = 'receive_fanout'
                self.health_diagnostic = None
                self.broker = SimpleNamespace(start=lambda: None,
                                              process=SimpleNamespace(pid=1, poll=lambda: None))

            def live(self, *_):
                raise EOFError()

            def close(self):
                pass

        failures = queue.Queue(maxsize=1)
        cancelled = threading.Event()
        with tempfile.TemporaryDirectory(prefix='p91-unit-') as temporary:
            args = SimpleNamespace(state_root=Path(temporary), seconds=5, recovery_interval=120, batch=1)
            with patch.object(soak, 'Laboratory', Laboratory), patch.object(
                    soak.pressure.fanout.baseline, 'process_sample', return_value={'rss_kib': 1}):
                with self.assertRaises(EOFError):
                    soak.scenario(args, None, None, None, 'mtls', 1, cancelled, failures)
                self.assertTrue(cancelled.is_set())
                with self.assertRaises(AssertionError):
                    soak.scenario(args, None, None, None, 'tcp', 1, cancelled, failures)
        first = failures.get_nowait()
        self.assertEqual(first['transport'], 'mtls')
        self.assertEqual(first['error_type'], 'EOFError')
        self.assertEqual(first['operation'], 'receive_fanout')
        self.assertTrue(failures.empty())

    def test_qos0_delivery_duplicate_flag_is_not_masked(self):
        class Peer:
            def receive(self):
                return 0x38, soak.f.text('benchmark/value') + soak.payload(0)
        with self.assertRaisesRegex(AssertionError, 'must not set DUP'):
            soak.receive(Peer(), 0, 0)

    def test_health_deadline_rejects_never_ready(self):
        class Broker:
            process = SimpleNamespace(pid=1, poll=lambda: None)
            def metrics(self):
                return dict(xmqr_ready=0, xmqr_persistence_errors_total=0)
        with self.assertRaises(TimeoutError):
            wait_healthy(Broker(), seconds=.01, interval=.001)

    def test_health_never_accepts_persistence_error_even_if_ready(self):
        class Broker:
            process = SimpleNamespace(pid=1, poll=lambda: None)
            def metrics(self):
                return dict(xmqr_ready=1, xmqr_persistence_errors_total=1)
        with self.assertRaisesRegex(AssertionError, 'never accepted'):
            wait_healthy(Broker(), seconds=.01)

    def test_health_bounded_transient_is_recorded_not_hidden(self):
        class Broker:
            process = SimpleNamespace(pid=1, poll=lambda: None)
            calls = 0
            def metrics(self):
                self.calls += 1
                return dict(xmqr_ready=int(self.calls == 2), xmqr_persistence_errors_total=0)
        values, probes = wait_healthy(Broker(), seconds=.1, interval=.001)
        self.assertEqual(values['xmqr_ready'], 1)
        self.assertEqual([item['metrics']['xmqr_ready'] for item in probes], [0, 1])

    def test_health_ready_response_after_deadline_is_rejected(self):
        class Broker:
            process = SimpleNamespace(pid=1, poll=lambda: None)
            def metrics(self):
                return dict(xmqr_ready=1, xmqr_persistence_errors_total=0)
        with patch('test_phase3_health.time.monotonic', side_effect=[0, 0, 0, 2, 2, 2, 2]):
            with self.assertRaises(TimeoutError):
                wait_healthy(Broker(), seconds=1, interval=0)

    def test_health_dead_process_is_never_treated_as_ready(self):
        class Broker:
            process = SimpleNamespace(pid=1, poll=lambda: 1)
            def metrics(self):
                return dict(xmqr_ready=1, xmqr_persistence_errors_total=0)
        with self.assertRaisesRegex(AssertionError, 'process died'):
            wait_healthy(Broker(), seconds=.1)

    def test_health_process_death_during_probe_rejects_ready_response(self):
        outcomes = iter([None, 1])
        class Broker:
            process = SimpleNamespace(pid=1, poll=lambda: next(outcomes))
            def metrics(self):
                return dict(xmqr_ready=1, xmqr_persistence_errors_total=0)
        with self.assertRaisesRegex(AssertionError, 'process died'):
            wait_healthy(Broker(), seconds=.1)

    def test_health_replaced_pid_rejects_ready_response(self):
        class Broker:
            process = SimpleNamespace(pid=1, poll=lambda: None)
            def metrics(self):
                self.process = SimpleNamespace(pid=2, poll=lambda: None)
                return dict(xmqr_ready=1, xmqr_persistence_errors_total=0)
        with self.assertRaisesRegex(AssertionError, 'process died or changed'):
            wait_healthy(Broker(), seconds=.1)

    def test_acl_subscriber_expected_refusal_has_protocol_evidence(self):
        xmqr = b'SUBACK recusou ou alterou QoS solicitado; confira ACL e limites do broker'
        mosquitto = b'Client fixture received SUBACK\nSubscribed (mid: 1): 128\nAll subscription requests were denied.'
        for kind, output, code in [('xmqr', xmqr, 1), ('mosquitto', mosquitto, 0)]:
            behavior, _ = external.validate_subscription_policy(output, kind, dict(Status='exited', ExitCode=code))
            self.assertEqual(behavior, 'immediate_refusal')

    def test_acl_subscriber_arbitrary_exit_and_transport_failures_rejected(self):
        for kind in ('xmqr', 'mosquitto'):
            for output in (b'', b'certificate verify failed', b'Timed out', b'Connection was lost'):
                with self.subTest(kind=kind, output=output):
                    with self.assertRaises(AssertionError):
                        external.validate_subscription_policy(output, kind, dict(Status='exited', ExitCode=1))

    def test_acl_subscriber_expected_marker_does_not_accept_unexpected_exit(self):
        output = b'Client fixture received SUBACK\nSubscribed (mid: 1): 128\nAll subscription requests were denied.'
        with self.assertRaises(AssertionError):
            external.validate_subscription_policy(output, 'mosquitto', dict(Status='exited', ExitCode=7))

    def test_acl_subscriber_positive_suback_is_not_refusal(self):
        output = b'Client fixture received SUBACK\nSubscribed (mid: 1): 1'
        with self.assertRaises(AssertionError):
            external.validate_subscription_policy(output, 'mosquitto', dict(Status='exited', ExitCode=0))
        behavior, _ = external.validate_subscription_policy(output, 'mosquitto', dict(Status='running', ExitCode=0))
        self.assertEqual(behavior, 'delivery_filter')

    def test_acl_subscriber_refusal_cannot_hide_later_transport_failure(self):
        output = b'Client fixture received SUBACK\nSubscribed (mid: 1): 128\nAll subscription requests were denied.\nConnection was lost'
        with self.assertRaises(AssertionError):
            external.validate_subscription_policy(output, 'mosquitto', dict(Status='exited', ExitCode=0))


if __name__ == '__main__':
    unittest.main()
