#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P47: real SIGTERM/SIGINT, durable Will and QoS2 across server stop."""
import argparse
import importlib.util
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
import sys

sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location('wills', Path(__file__).with_name('verify_last_will.py'))
wills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wills)
fixtures = wills.fixtures


class Shutdown(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xmqr-p47-')
        self.broker = fixtures.Broker(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.broker.stop)
        self.broker.start()

    def stop(self, sig):
        process = self.broker.process
        process.send_signal(sig)
        self.assertEqual(process.wait(timeout=18), 0)
        process.stderr.close()
        self.broker.process = None

    def test_sigterm_will_retained_offline_and_no_republication(self):
        observer = fixtures.WireClient(self.broker, 'persistent', clean=False)
        self.assertEqual(observer.subscribe([('status/device', 2)]), (0x90, b'\0\x01\x02'))
        source = wills.WillClient(self.broker, 'source', 'status/device', b'offline', 2, True, clean=False)
        self.stop(signal.SIGTERM)
        observer.close()
        source.close()
        self.assertTrue((self.broker.state / 'state.snapshot').exists())
        self.broker.start()
        observer = fixtures.WireClient(self.broker, 'persistent', clean=False)
        self.addCleanup(observer.close)
        self.assertEqual(observer.connack, (0x20, b'\x01\0'))
        self.assertEqual(wills.publication(observer), ('status/device', 2, False, b'offline'))
        wills.no_message(observer)
        retained = fixtures.WireClient(self.broker, 'retained')
        self.addCleanup(retained.close)
        retained.subscribe([('status/device', 2)])
        self.assertEqual(wills.publication(retained), ('status/device', 2, True, b'offline'))
        wills.no_message(retained)

    def test_sigint_preserves_accepted_inbound_qos2(self):
        source = fixtures.WireClient(self.broker, 'qos2', clean=False)
        source.send(0x35, fixtures.text('retained/qos2') + b'\0\x07' + b'accepted')
        self.assertEqual(source.receive(), (0x50, b'\0\x07'))
        self.stop(signal.SIGINT)
        source.close()
        self.broker.start()
        source = fixtures.WireClient(self.broker, 'qos2', clean=False)
        self.addCleanup(source.close)
        self.assertEqual(source.connack, (0x20, b'\x01\0'))
        source.send(0x62, b'\0\x07')
        self.assertEqual(source.receive(), (0x70, b'\0\x07'))
        observer = fixtures.WireClient(self.broker, 'read')
        self.addCleanup(observer.close)
        observer.subscribe([('retained/qos2', 2)])
        self.assertEqual(wills.publication(observer), ('retained/qos2', 2, True, b'accepted'))

    def test_failure_does_not_claim_durable_shutdown(self):
        # Make snapshot publication impossible only inside this test's state.
        (self.broker.state / 'state.snapshot.tmp').mkdir()
        process = self.broker.process
        process.send_signal(signal.SIGTERM)
        self.assertNotEqual(process.wait(timeout=18), 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker', type=Path, required=True)
    args = parser.parse_args()
    fixtures.BROKER = args.broker.resolve()
    unittest.main(argv=['verify_shutdown'], verbosity=2)
