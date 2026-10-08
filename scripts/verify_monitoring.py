# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Luis E. S. Pinheiro
"""P43 loopback integration: independent MQTT fixtures + independent CLI.

No Mosquitto. Run on Unix with the broker and client built from separate projects.
All listeners/state/processes belong to the test and are bounded/temporary.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location(
    "will_fixtures", Path(__file__).parent / "verify_last_will.py")
will = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(will)
fixtures = will.fixtures
CLIENT = None


def free_port():
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        return reserve.getsockname()[1]


class MonitoredBroker(fixtures.Broker):
    def __init__(self, root):
        super().__init__(root)
        self.monitor_port = free_port()
        while self.monitor_port == self.port:
            self.monitor_port = free_port()

    def environment(self, enabled=True):
        env = {k: v for k, v in os.environ.items() if not k.startswith("MQTT_")}
        env.update(MQTT_MODE="open-lab", MQTT_BIND=f"127.0.0.1:{self.port}",
                   MQTT_STATE_DIR=str(self.state), RUST_LOG="error",
                   MQTT_MONITOR_BIND=f"127.0.0.1:{self.monitor_port}")
        if enabled:
            env["MQTT_MONITOR_ENABLED"] = "true"
        return env

    def start(self, enabled=True):
        self.process = subprocess.Popen([str(fixtures.BROKER)],
            env=self.environment(enabled), stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE)
        until = time.monotonic() + fixtures.TIMEOUT
        try:
            while time.monotonic() < until:
                if self.process.poll() is not None:
                    raise AssertionError(self.process.stderr.read().decode())
                try:
                    with socket.create_connection(("127.0.0.1", self.port), timeout=.1):
                        if not enabled or self.http("/ready")[0] == 200:
                            return self
                except OSError:
                    pass
                time.sleep(.02)
            raise AssertionError("broker readiness timeout")
        except BaseException:
            self.stop()
            raise

    def request(self, raw):
        with socket.create_connection(("127.0.0.1", self.monitor_port),
                                     timeout=fixtures.TIMEOUT) as stream:
            stream.sendall(raw)
            response = bytearray()
            while True:
                try:
                    chunk = stream.recv(4096)
                except ConnectionResetError:
                    if b"\r\n\r\n" not in response:
                        raise
                    break
                if not chunk:
                    break
                response.extend(chunk)
                assert len(response) < 32768
        header, body = bytes(response).split(b"\r\n\r\n", 1)
        length = next(int(line.split(b":", 1)[1]) for line in header.split(b"\r\n")
                      if line.lower().startswith(b"content-length:"))
        assert len(body) == length, "incomplete HTTP response"
        return int(header.split(b" ")[1]), header.decode("ascii"), body.decode("utf-8")

    def http(self, path):
        return self.request(f"GET {path} HTTP/1.1\r\nHost: local\r\n\r\n".encode())

    def metrics(self):
        code, headers, body = self.http("/metrics")
        assert code == 200
        assert "text/plain; version=0.0.4" in headers
        return {line.rsplit(" ", 1)[0]: float(line.rsplit(" ", 1)[1])
                for line in body.splitlines() if line and not line.startswith("#")}


class MonitoringIntegration(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="xmqr-p43-")
        self.addCleanup(self.directory.cleanup)
        self.broker = MonitoredBroker(self.directory.name)
        self.addCleanup(self.broker.stop)
        self.broker.start()

    def publish(self, topic, payload, qos=0, retain=False):
        subprocess.run([str(CLIENT), "pub", "--open-lab", "--host", "127.0.0.1",
            "--port", str(self.broker.port), "--topic", topic, "--message", payload,
            "--qos", str(qos), "--retain", str(retain).lower()],
            check=True, capture_output=True, timeout=10)

    def wait_metric(self, name, expected):
        until = time.monotonic() + fixtures.TIMEOUT
        while time.monotonic() < until:
            if self.broker.metrics()[name] == expected:
                return
            time.sleep(.02)
        self.assertEqual(self.broker.metrics()[name], expected, name)

    def test_http_endpoints_fixed_labels_and_negative_requests(self):
        self.assertEqual(self.broker.http("/health")[0], 200)
        self.assertEqual(self.broker.http("/ready")[0], 200)
        self.assertEqual(self.broker.http("/missing")[0], 404)
        for raw, expected in [
            (b"POST /ready HTTP/1.1\r\n\r\n", 405),
            (b"GET /health HTTP/1.1\r\nContent-Length: 1\r\n\r\nx", 400),
            (b"GET /health HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n", 400),
            (b"GET /health HTTP/1.1\r\nX: " + b"a" * 4096 + b"\r\n\r\n", 431),
            (b"GET /health HTTP/1.1\r\n", 408),
        ]:
            self.assertEqual(self.broker.request(raw)[0], expected)
        body = self.broker.http("/metrics")[2]
        reasons = [line for line in body.splitlines() if line.startswith("xmqr_rejections_total{")]
        self.assertEqual(len(reasons), 7)
        for secret_label in ("topic=", "username=", "client_id=", "payload="):
            self.assertNotIn(secret_label, body)
        self.assertGreaterEqual(self.broker.metrics()["xmqr_monitor_rejected_total"], 5)

    def test_cli_qos_utf8_1024_retained_and_message_counters(self):
        topic = "é" * 512
        for qos in (0, 1, 2):
            with fixtures.WireClient(self.broker, f"observer{qos}") as subscriber:
                self.assertEqual(subscriber.subscribe([(topic, 2)]), (0x90, b"\0\x01\x02"))
                if qos:
                    self.assertEqual(will.publication(subscriber), (topic, qos - 1, True, "private-payload".encode()))
                    subscriber.ping()
                before = self.broker.metrics()
                self.publish(topic, "private-payload", qos, True)
                self.assertEqual(will.publication(subscriber), (topic, qos, False, b"private-payload"))
                subscriber.ping()
                for prefix in ("received", "sent"):
                    key = f'xmqr_messages_{prefix}_total{{qos="{qos}"}}'
                    self.wait_metric(key, before[key] + 1)
                self.wait_metric("xmqr_retained_messages", 1)
        text = self.broker.http("/metrics")[2]
        self.assertNotIn(topic, text)
        self.assertNotIn("private-payload", text)
        metrics = self.broker.metrics()
        self.assertGreater(metrics["xmqr_persistence_commits_total"], 0)
        self.assertGreaterEqual(metrics["xmqr_persistence_commit_attempts_total"], metrics["xmqr_persistence_commits_total"])
        self.assertEqual(metrics["xmqr_persistence_errors_total"], 0)

    def test_offline_resume_and_inflight_gauges_drain(self):
        topic = "offline/value"
        client = fixtures.WireClient(self.broker, "persistent", False)
        self.assertEqual(client.subscribe([(topic, 1)]), (0x90, b"\0\x01\x01"))
        client.send(0xe0)
        self.assertEqual(client.socket.recv(1), b"")
        client.close()
        self.publish(topic, "queued", 1)
        self.wait_metric("xmqr_offline_messages", 1)
        with fixtures.WireClient(self.broker, "persistent", False) as resumed:
            self.assertEqual(resumed.connack, (0x20, b"\x01\0"))
            self.assertEqual(will.publication(resumed), (topic, 1, False, b"queued"))
            resumed.ping()
            self.wait_metric("xmqr_offline_messages", 0)
            self.wait_metric("xmqr_inflight_messages", 0)

    def test_will_counter_and_authentication_rejection(self):
        topic = "é" * 512
        with fixtures.WireClient(self.broker, "will-observer") as observer:
            self.assertEqual(observer.subscribe([(topic, 2)]), (0x90, b"\0\x01\x02"))
            before = self.broker.metrics()["xmqr_wills_published_total"]
            source = will.WillClient(self.broker, "will-source", topic, b"private-will", 2, True)
            source.close()
            self.assertEqual(will.publication(observer), (topic, 2, False, b"private-will"))
            observer.ping()
            self.wait_metric("xmqr_wills_published_total", before + 1)
        key = 'xmqr_rejections_total{reason="authentication"}'
        before = self.broker.metrics()[key]
        rejected = fixtures.WireClient.__new__(fixtures.WireClient)
        rejected.socket = socket.create_connection(("127.0.0.1", self.broker.port), timeout=fixtures.TIMEOUT)
        with rejected:
            rejected.send(0x10, fixtures.text("MQTT") + bytes([4, 0xc2, 0, 30]) +
                          fixtures.text("invalid-auth") + fixtures.text("private-user") + fixtures.text("private-pass"))
            self.assertEqual(rejected.receive(), (0x20, b"\0\x05"))
        self.wait_metric(key, before + 1)
        body = self.broker.http("/metrics")[2]
        for secret in ("private-will", "private-user", "private-pass"):
            self.assertNotIn(secret, body)

    def test_slow_http_connections_allow_mqtt_progress(self):
        connections = []
        try:
            for _ in range(16):
                stream = socket.create_connection(("127.0.0.1", self.broker.monitor_port), timeout=fixtures.TIMEOUT)
                connections.append(stream)
                stream.sendall(b"G")
            with fixtures.WireClient(self.broker, "mqtt-under-http-load") as client:
                client.ping()
            # MQTT has its own admission and handlers; all waits above are bounded.
        finally:
            for stream in connections:
                stream.close()

    def test_disabled_default_and_invalid_bind_fail_closed(self):
        self.broker.stop()
        self.broker.start(enabled=False)
        with fixtures.WireClient(self.broker, "disabled-monitor") as client:
            client.ping()
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", self.broker.monitor_port), timeout=.2)
        self.broker.stop()
        for enabled, bind in [("true", "0.0.0.0:9090"), ("true", "127.0.0.1:0"), ("yes", "127.0.0.1:9090")]:
            env = self.broker.environment()
            env.update(MQTT_MONITOR_ENABLED=enabled, MQTT_MONITOR_BIND=bind)
            result = subprocess.run([str(fixtures.BROKER)], env=env, capture_output=True, timeout=fixtures.TIMEOUT)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--client", type=Path, required=True)
    args = parser.parse_args()
    fixtures.BROKER = args.broker.resolve()
    CLIENT = args.client.resolve()
    for binary in (fixtures.BROKER, CLIENT):
        if not binary.is_file():
            parser.error(f"binary missing: {binary}")
    unittest.main(argv=["verify-monitoring"], verbosity=2)
