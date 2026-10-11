#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P55: isolated real-process quota boundaries and durable replay.

Uses independent MQTT byte fixtures and the explicitly selected client CLI.
Unix is required by the broker's directory-fsync contract; no Mosquitto claim.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("fixtures", Path(__file__).with_name("verify_interop.py"))
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


class QuotaBroker(fixtures.Broker):
    def __init__(self, root, limits):
        super().__init__(root)
        self.limits = limits

    def start(self):
        # The existing harness starts with a private env. Add quotas only to
        # that child by overriding its environment construction, never globally.
        config = self.root / "broker.toml"
        config.write_text(
            f'version=1\n[broker]\nmode="open-lab"\nbind="127.0.0.1:{self.port}"\nstate_dir="state"\n[limits]\n'
            + "".join(f"{key}={value}\n" for key, value in self.limits.items()), encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if not key.startswith("MQTT_")}
        env.update(MQTT_CONFIG=str(config), RUST_LOG="error")
        self.process = subprocess.Popen([str(fixtures.BROKER)], env=env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        import time
        deadline = time.monotonic() + fixtures.TIMEOUT
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError(self.process.stderr.read().decode())
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return self
            except OSError:
                time.sleep(0.02)
        self.stop()
        raise AssertionError("broker readiness timeout")


def publish(client, payload, qos=1, topic="test/state", identifier=1, retain=False, finish=True):
    packet_id = struct.pack("!H", identifier)
    body = fixtures.text(topic) + (packet_id if qos else b"") + payload
    client.send(0x30 | (qos << 1) | int(retain), body)
    if qos:
        assert client.receive() == (0x40 if qos == 1 else 0x50, packet_id)
        if qos == 2 and finish:
            client.send(0x62, packet_id)
            assert client.receive() == (0x70, packet_id)
    else:
        client.ping()  # Barrier: the broker processed the QoS0 publish.


def delivery(client, acknowledge=True):
    header, body = client.receive()
    assert header >> 4 == 3, (header, body)
    length = int.from_bytes(body[:2], "big")
    topic = body[2:2 + length].decode()
    qos = (header >> 1) & 3
    offset = 2 + length
    identifier = body[offset:offset + 2] if qos else b""
    offset += 2 if qos else 0
    if acknowledge and qos:
        client.send(0x40 if qos == 1 else 0x50, identifier)
        if qos == 2:
            assert client.receive() == (0x62, identifier)
            client.send(0x70, identifier)
    return topic, body[offset:], identifier


class StateLimits(unittest.TestCase):
    def setup_broker(self, **limits):
        directory = tempfile.TemporaryDirectory(prefix="xmqr-p55-")
        self.addCleanup(directory.cleanup)
        self.broker = QuotaBroker(directory.name, limits)
        self.addCleanup(self.broker.stop)
        self.broker.start()

    def client(self, identifier, clean=True):
        client = fixtures.WireClient(self.broker, identifier, clean)
        self.addCleanup(client.close)
        return client

    def closed_without_ack(self, client):
        with self.assertRaises((EOFError, ConnectionResetError)):
            client.receive()

    def restart(self):
        self.broker.stop()  # Test-owned process crash: all clients become offline.
        self.broker.start()

    def test_sessions_boundary_independent_of_tcp_admission(self):
        self.setup_broker(max_sessions=1, max_connections=4)
        first = self.client("first", clean=False)
        # TCP accepts the second socket; MQTT cannot commit a second session.
        with socket.create_connection(("127.0.0.1", self.broker.port), timeout=fixtures.TIMEOUT) as second:
            second.sendall(b'\x10\x10\x00\x04MQTT\x04\x00\x00\x1e\x00\x04next')
            self.assertEqual(second.recv(1), b"")
        first.ping()
        self.restart()
        resumed = self.client("first", clean=False)
        self.assertEqual(resumed.connack, (0x20, b"\x01\0"))
        resumed.ping()

    def test_subscriptions_boundary_keeps_original_filter(self):
        self.setup_broker(max_subscriptions=1)
        client = self.client("subscriber", clean=False)
        self.assertEqual(client.subscribe([("test/state", 1)]), (0x90, b"\0\x01\x01"))
        client.send(0x82, b"\0\x02" + fixtures.text("test/other") + b"\x01")
        self.closed_without_ack(client)
        self.restart()
        resumed = self.client("subscriber", clean=False)
        source = self.client("source")
        publish(source, b"kept")
        self.assertEqual(delivery(resumed)[:2], ("test/state", b"kept"))
        publish(source, b"rejected", topic="test/other", identifier=2)
        resumed.ping()

    def test_retained_boundary_rejects_without_puback_and_recovers(self):
        self.setup_broker(max_retained=1)
        source = self.client("source")
        publish(source, b"kept", retain=True)
        source.send(0x33, fixtures.text("test/other") + b"\0\x02rejected")
        self.closed_without_ack(source)
        self.restart()
        subscriber = self.client("subscriber")
        self.assertEqual(subscriber.subscribe([("test/#", 1)]), (0x90, b"\0\x01\x01"))
        self.assertEqual(delivery(subscriber)[:2], ("test/state", b"kept"))
        subscriber.ping()

    def test_offline_boundary_preserves_first_committed_message(self):
        self.setup_broker(max_offline=1)
        subscriber = self.client("subscriber", clean=False)
        self.assertEqual(subscriber.subscribe([("test/state", 1)]), (0x90, b"\0\x01\x01"))
        subscriber.send(0xe0)
        self.assertEqual(subscriber.socket.recv(1), b"")
        source = self.client("source")
        publish(source, b"first")
        source.send(0x32, fixtures.text("test/state") + b"\0\x02second")
        self.closed_without_ack(source)
        self.restart()
        resumed = self.client("subscriber", clean=False)
        self.assertEqual(delivery(resumed)[:2], ("test/state", b"first"))
        resumed.ping()

    def test_inbound_qos2_boundary_preserves_accepted_responsibility(self):
        self.setup_broker(max_inflight=1)
        source = self.client("source", clean=False)
        publish(source, b"accepted", qos=2, retain=True, finish=False)
        source.send(0x35, fixtures.text("test/other") + b"\0\x02rejected")
        self.closed_without_ack(source)
        self.restart()
        resumed = self.client("source", clean=False)
        resumed.send(0x62, b"\0\x01")
        self.assertEqual(resumed.receive(), (0x70, b"\0\x01"))
        subscriber = self.client("subscriber")
        self.assertEqual(subscriber.subscribe([("test/#", 2)]), (0x90, b"\0\x01\x02"))
        self.assertEqual(delivery(subscriber)[:2], ("test/state", b"accepted"))
        subscriber.ping()

    def test_outbound_inflight_defers_and_offline_overflow_rejects(self):
        self.setup_broker(max_inflight=1, max_offline=1)
        subscriber = self.client("subscriber", clean=False)
        self.assertEqual(subscriber.subscribe([("test/state", 1)]), (0x90, b"\0\x01\x01"))
        source = self.client("source")
        publish(source, b"first")
        first = delivery(subscriber, acknowledge=False)
        publish(source, b"second", identifier=2)
        subscriber.ping()  # No second PUBLISH before the first ACK.
        source.send(0x32, fixtures.text("test/state") + b"\0\x03third")
        self.closed_without_ack(source)
        self.restart()
        resumed = self.client("subscriber", clean=False)
        self.assertEqual(delivery(resumed)[:2], first[:2])
        self.assertEqual(delivery(resumed)[:2], ("test/state", b"second"))
        resumed.ping()

    def test_independent_cli_qos_0_1_2_with_configured_quotas(self):
        self.setup_broker(max_sessions=4, max_retained=2, max_subscriptions=2,
                          max_offline=2, max_inflight=2)
        subscriber = self.client("observer")
        self.assertEqual(subscriber.subscribe([("test/state", 2)]), (0x90, b"\0\x01\x02"))
        for qos in (0, 1, 2):
            subprocess.run([str(CLIENT), "pub", "--open-lab", "--host", "127.0.0.1",
                "--port", str(self.broker.port), "--topic", "test/state", "--message", f"qos{qos}",
                "--qos", str(qos)], check=True, capture_output=True, timeout=fixtures.TIMEOUT)
            self.assertEqual(delivery(subscriber)[:2], ("test/state", f"qos{qos}".encode()))
            subscriber.ping()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--client", type=Path, required=True)
    args = parser.parse_args()
    if os.name != "posix":
        print("BLOCKED: Unix directory fsync is required; use Linux/WSL", file=sys.stderr)
        sys.exit(2)
    fixtures.BROKER = args.broker.resolve(strict=True)
    CLIENT = args.client.resolve(strict=True)
    unittest.main(argv=[__file__], verbosity=2)
