#!/usr/bin/env python3
"""Real TCP MQTT 5 Message Expiry across retention, offline queue and restart."""
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, connect, packet, start, stop


def subscribe(stream, topic: bytes):
    body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x01"
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00\x01")


def publish_body(stream, topic: bytes, expected: bytes, retained: bool):
    header, body = packet(stream)
    assert header & 0xF7 == (0x33 if retained else 0x32), (header, body)
    length = int.from_bytes(body[:2], "big")
    assert body[2:2 + length] == topic, body
    packet_id = body[2 + length:4 + length]
    properties = body[4 + length:]
    assert properties[:2] == b"\x05\x02", properties
    remaining = int.from_bytes(properties[2:6], "big")
    assert 1 <= remaining <= 2, remaining
    assert properties[6:] == expected, properties
    stream.sendall(b"\x40\x02" + packet_id)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build binaries first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-message-expiry-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            topic = b"expiry/check"
            offline, present = connect(port, True, 0xFFFFFFFF, b"expiry-offline")
            assert not present
            subscribe(offline, topic)
            offline.sendall(b"\xe0\x00")
            offline.close()
            late, present = connect(port, True, 0xFFFFFFFF, b"expiry-late")
            assert not present
            subscribe(late, topic)
            late.sendall(b"\xe0\x00")
            late.close()
            external_topic = b"expiry/external"
            external_late, _ = connect(port, True, 0xFFFFFFFF, b"expiry-external-late")
            subscribe(external_late, external_topic)
            external_late.sendall(b"\xe0\x00")
            external_late.close()
            result = subprocess.run([
                CLIENT, "pub", "--open-lab", "--port", str(port),
                "--protocol-version", "5", "--topic", topic.decode(),
                "--message", "short-lived", "--qos", "1", "--retain", "true",
                "--message-expiry-seconds", "2",
            ], capture_output=True, timeout=8)
            assert result.returncode == 0, result.stderr
            external = subprocess.run([
                "mosquitto_pub", "-V", "mqttv5", "-i", "expiry-external-pub", "-h", "127.0.0.1", "-p", str(port),
                "-t", external_topic.decode(), "-m", "external", "-q", "2",
                "-D", "publish", "message-expiry-interval", "1",
            ], capture_output=True, timeout=8)
            assert external.returncode == 0, external.stderr
            resumed, present = connect(port, False, 0xFFFFFFFF, b"expiry-offline")
            assert present
            publish_body(resumed, topic, b"short-lived", False)
            resumed.sendall(b"\xe0\x00")
            resumed.close()
            retained, _ = connect(port, True, 0, b"expiry-retained")
            subscribe(retained, topic)
            publish_body(retained, topic, b"short-lived", True)
            retained.sendall(b"\xe0\x00")
            retained.close()
            time.sleep(2.3)
            stop(broker)
            broker = start(port, state)
            late, present = connect(port, False, 0xFFFFFFFF, b"expiry-late")
            assert present
            late.settimeout(0.6)
            try:
                packet(late)
                raise AssertionError("expired offline delivery was replayed")
            except socket.timeout:
                pass
            late.sendall(b"\xe0\x00")
            late.close()
            external_late, present = connect(port, False, 0xFFFFFFFF, b"expiry-external-late")
            assert present
            external_late.settimeout(0.6)
            try:
                packet(external_late)
                raise AssertionError("expired Mosquitto QoS2 delivery was replayed")
            except socket.timeout:
                pass
            external_late.sendall(b"\xe0\x00")
            external_late.close()
            fresh, _ = connect(port, True, 0, b"expiry-fresh")
            subscribe(fresh, topic)
            fresh.settimeout(0.6)
            try:
                packet(fresh)
                raise AssertionError("expired retained delivery was replayed")
            except socket.timeout:
                pass
            fresh.sendall(b"\xe0\x00")
            fresh.close()
            print("PASS: MQTT 5 Message Expiry client/Mosquitto QoS2 wire, remaining interval, offline/retained expiry after restart")
        finally:
            if broker.poll() is None:
                stop(broker)


if __name__ == "__main__":
    main()
