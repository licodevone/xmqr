# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Luis E. S. Pinheiro
"""Bounded MQTT 3.1.1 checks against a real XMQR process and Mosquitto clients.

Run after cargo build --locked --bins:
python3 scripts/verify_interop.py --broker /path/to/debug/mqtt-broker
Only loopback listeners and temporary state/configuration directories are used.
"""

import argparse
import os
from pathlib import Path
import queue
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
import uuid


BROKER = None
TIMEOUT = 5


class Broker:
    def __init__(self, root):
        self.root = Path(root)
        self.state = self.root / "state"
        self.state.mkdir(exist_ok=True)
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            self.port = reserve.getsockname()[1]
        self.process = None

    def start(self):
        env = {key: value for key, value in os.environ.items() if not key.startswith("MQTT_")}
        env.update(MQTT_MODE="open-lab", MQTT_BIND=f"127.0.0.1:{self.port}",
                   MQTT_STATE_DIR=str(self.state), RUST_LOG="error")
        self.process = subprocess.Popen([str(BROKER)], env=env, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.PIPE)
        until = time.monotonic() + TIMEOUT
        while time.monotonic() < until:
            if self.process.poll() is not None:
                raise AssertionError(self.process.stderr.read().decode())
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return self
            except OSError:
                time.sleep(0.02)
        self.stop()
        raise AssertionError("broker readiness timeout")

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()  # Only the test-owned process; exercises crash recovery.
            self.process.wait(timeout=TIMEOUT)
            self.process.stderr.close()
            self.process = None

    def publish(self, topic, payload, qos=0, retain=False):
        args = ["mosquitto_pub", "-h", "127.0.0.1", "-p", str(self.port),
                "-V", "mqttv311", "-i", f"interop-pub-{uuid.uuid4().hex[:12]}",
                "-t", topic, "-m", payload, "-q", str(qos)]
        if retain:
            args.append("-r")
        subprocess.run(args, check=True, capture_output=True, timeout=TIMEOUT)


class Subscriber:
    def __init__(self, broker, filters, qos=0):
        args = ["mosquitto_sub", "-h", "127.0.0.1", "-p", str(broker.port),
                "-V", "mqttv311", "-i", f"interop-sub-{uuid.uuid4().hex[:12]}",
                "-q", str(qos), "-d", "-F", "DATA|%t|%q|%r|%p"]
        for topic_filter in filters:
            args.extend(["-t", topic_filter])
        # libmosquitto buffers debug output when piped. Observe SUBACK without
        # waiting for the first publication or relying on a fixed sleep.
        self.process = subprocess.Popen(["stdbuf", "-oL", *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, bufsize=1)
        self.lines = queue.Queue()
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()
        try:
            until = time.monotonic() + TIMEOUT
            while time.monotonic() < until:
                if "received SUBACK" in self.lines.get(timeout=max(0.01, until-time.monotonic())):
                    return
            raise AssertionError("SUBACK timeout")
        except BaseException:
            self.close()
            raise

    def read(self):
        for line in self.process.stdout:
            self.lines.put(line.strip())

    def message(self, timeout=TIMEOUT):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            try:
                line = self.lines.get(timeout=max(0.01, until-time.monotonic()))
            except queue.Empty:
                return None
            if line.startswith("DATA|"):
                _, topic, qos, retained, payload = line.split("|", 4)
                return topic, int(qos), bool(int(retained)), payload
        return None

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=TIMEOUT)
        self.reader.join(timeout=TIMEOUT)
        self.process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def text(value):
    encoded = value.encode("utf-8")
    return struct.pack("!H", len(encoded)) + encoded


class WireClient:
    """Independent byte fixtures for cases normal clients refuse to send."""
    def __init__(self, broker, client_id, clean=True):
        self.socket = socket.create_connection(("127.0.0.1", broker.port), timeout=TIMEOUT)
        self.send(0x10, text("MQTT") + bytes([4, 2 if clean else 0, 0, 30]) + text(client_id))
        self.connack = self.receive()
        assert self.connack[0] == 0x20 and self.connack[1][1] == 0

    def send(self, header, body=b""):
        remaining = len(body)
        length = bytearray()
        while True:
            digit = remaining % 128
            remaining //= 128
            length.append(digit | (0x80 if remaining else 0))
            if not remaining:
                break
        self.socket.sendall(bytes([header]) + length + body)

    def exact(self, count):
        data = b""
        while len(data) < count:
            chunk = self.socket.recv(count-len(data))
            if not chunk:
                raise EOFError("broker closed connection")
            data += chunk
        return data

    def receive(self):
        header = self.exact(1)[0]
        size, multiplier = 0, 1
        for _ in range(4):
            digit = self.exact(1)[0]
            size += (digit & 127) * multiplier
            if not digit & 128:
                assert size <= 65536
                return header, self.exact(size)
            multiplier *= 128
        raise AssertionError("invalid remaining length")

    def subscribe(self, filters):
        self.send(0x82, b"\0\x01" + b"".join(text(f)+bytes([q]) for f, q in filters))
        return self.receive()

    def ping(self):
        self.send(0xc0)
        assert self.receive() == (0xd0, b"")

    def close(self):
        self.socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class Interoperability(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="xmqr-interop-")
        self.broker = Broker(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.broker.stop)
        self.broker.start()

    def test_exact_and_overlapping_wildcards_qos_0_1_2(self):
        # MQTT-3.3.5-1; §§4.3,4.7: independent publisher and subscriber.
        for qos in (0, 1, 2):
            for filters in (["sensors/one/value"], ["sensors/#", "sensors/+/value"]):
                with Subscriber(self.broker, filters, qos) as subscriber:
                    self.broker.publish("sensors/one/value", "24", qos)
                    self.assertEqual(subscriber.message(), ("sensors/one/value", qos, False, "24"))
                    self.assertIsNone(subscriber.message(timeout=0.2), "duplicate fan-out")

    def test_retained_recovery_and_system_namespace(self):
        # MQTT-3.3.1-6/8/9; MQTT-4.7.2-1.
        self.broker.publish("sensors/one/state", "online", 1, retain=True)
        self.broker.publish("$SYS/state", "ready", 1, retain=True)
        self.broker.stop()
        self.broker.start()
        with Subscriber(self.broker, ["#", "sensors/+/state"], 1) as subscriber:
            self.assertEqual(subscriber.message(), ("sensors/one/state", 1, True, "online"))
            self.assertIsNone(subscriber.message(timeout=0.2))
        with Subscriber(self.broker, ["$SYS/#"], 1) as subscriber:
            self.assertEqual(subscriber.message(), ("$SYS/state", 1, True, "ready"))
        self.broker.publish("sensors/one/state", "", 1, retain=True)
        with Subscriber(self.broker, ["sensors/#"], 1) as subscriber:
            self.assertIsNone(subscriber.message(timeout=0.2))

    def test_persistent_wildcard_reconnect_and_unsubscribe(self):
        # MQTT-3.1.2-4/5 and MQTT-3.10.4-1: byte-for-byte filter removal.
        with WireClient(self.broker, "persistent-sub", clean=False) as client:
            self.assertEqual(client.subscribe([("sensors/#", 1)]), (0x90, b"\0\x01\x01"))
        # Restart makes the subscription inactive before testing offline routing.
        self.broker.stop()
        self.broker.start()
        self.broker.publish("sensors/one/value", "offline", 1)
        self.broker.stop()
        self.broker.start()
        with WireClient(self.broker, "persistent-sub", clean=False) as client:
            self.assertEqual(client.connack, (0x20, b"\x01\0"))
            header, body = client.receive()
            self.assertEqual(header, 0x32)
            length = struct.unpack("!H", body[:2])[0]
            self.assertEqual(body[2:2+length], b"sensors/one/value")
            packet_id = body[2+length:4+length]
            self.assertEqual(body[4+length:], b"offline")
            client.send(0x40, packet_id)
            client.send(0xa2, b"\0\x02" + text("sensors/#"))
            self.assertEqual(client.receive(), (0xb0, b"\0\x02"))
            self.broker.publish("sensors/one/value", "removed", 1)
            client.ping()  # No publication precedes the response after UNSUBACK.

    def test_invalid_filters_and_publish_wildcards_close_connection(self):
        # MQTT-4.7.1-1/2/3, MQTT-3.3.2-2 and MQTT-4.8.0-1.
        for invalid in ("sensors+", "a/#/b", "a/+tail", "a/##"):
            with WireClient(self.broker, "invalid") as client:
                client.send(0x82, b"\0\x01" + text(invalid) + b"\0")
                with self.assertRaises(EOFError):
                    client.receive()
        with WireClient(self.broker, "invalid-publish") as client:
            client.send(0x30, text("sensors/+") + b"payload")
            with self.assertRaises(EOFError):
                client.receive()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    args = parser.parse_args()
    BROKER = args.broker.resolve(strict=True)
    for binary in ("mosquitto_pub", "mosquitto_sub", "stdbuf"):
        if shutil.which(binary) is None:
            parser.error(f"missing {binary}; install mosquitto-clients")
    unittest.main(argv=[__file__], verbosity=2)
