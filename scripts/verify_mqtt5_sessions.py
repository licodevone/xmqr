#!/usr/bin/env python3
"""Exercise MQTT 5 durable session resume across broker restart in open-lab."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / "target/debug/mqtt-broker"
CLIENT = ROOT.parent / "xmqr-client/target/debug/mqtt-client"


def packet(stream):
    header = stream.recv(1)
    if not header:
        raise AssertionError("connection closed before MQTT packet")
    remaining = 0
    factor = 1
    while True:
        digit = stream.recv(1)
        if not digit:
            raise AssertionError("truncated MQTT length")
        remaining += (digit[0] & 127) * factor
        if digit[0] & 128 == 0:
            break
        factor *= 128
    body = bytearray()
    while len(body) < remaining:
        chunk = stream.recv(remaining - len(body))
        if not chunk:
            raise AssertionError("truncated MQTT body")
        body.extend(chunk)
    return header[0], bytes(body)


def connect(port, clean, expiry, identity=b"session-check"):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    properties = bytes([0x11]) + expiry.to_bytes(4, "big")
    body = (b"\x00\x04MQTT\x05" + bytes([2 if clean else 0]) + b"\x00\x1e"
            + bytes([len(properties)]) + properties
            + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == 0, (header, ack)
    return stream, bool(ack[0] & 1)


def start(port, state):
    env = dict(os.environ, MQTT_MODE="open-lab", MQTT_STATE_DIR=state,
               MQTT_BIND=f"127.0.0.1:{port}")
    process = subprocess.Popen([BROKER], env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    for _ in range(100):
        if process.poll() is not None:
            raise AssertionError("broker stopped before listening")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return process
        except OSError:
            time.sleep(0.05)
    raise AssertionError("broker did not listen")


def stop(process):
    process.terminate()
    process.wait(timeout=8)


def main():
    if not BROKER.is_file() or not CLIENT.is_file():
        raise RuntimeError("build Linux broker and client binaries first")
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-session-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            subscriber, present = connect(port, True, 0xFFFFFFFF)
            assert not present
            topic = b"session/check"
            body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x01"
            subscriber.sendall(bytes([0x82, len(body)]) + body)
            assert packet(subscriber) == (0x90, b"\x00\x01\x00\x01")
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            publication = subprocess.run(
                [CLIENT, "pub", "--open-lab", "--port", str(port), "--topic",
                 topic.decode(), "--message", "offline", "--qos", "1"],
                capture_output=True, timeout=8)
            assert publication.returncode == 0, publication.stderr
            external = subprocess.run(
                ["mosquitto_pub", "-V", "mqttv5", "-i", "external-pub",
                 "-h", "127.0.0.1", "-p", str(port),
                 "-t", topic.decode(), "-m", "external", "-q", "1"],
                capture_output=True, timeout=8)
            assert external.returncode == 0, external.stderr
            stop(broker)
            broker = start(port, state)
            subscriber, present = connect(port, False, 0xFFFFFFFF)
            assert present
            for expected in (b"offline", b"external"):
                header, delivered = packet(subscriber)
                assert header & 0xF6 == 0x32, (header, delivered)
                topic_length = int.from_bytes(delivered[:2], "big")
                assert delivered[2:2 + topic_length] == topic
                packet_id = delivered[2 + topic_length:4 + topic_length]
                assert delivered.endswith(expected), delivered
                subscriber.sendall(b"\x40\x02" + packet_id)
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            time.sleep(0.1)
            subscriber, present = connect(port, False, 0)
            assert present
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            time.sleep(0.1)
            subscriber, present = connect(port, False, 0xFFFFFFFF)
            assert not present
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            finite, present = connect(port, True, 1, b"finite-check")
            assert not present
            finite.sendall(b"\xe0\x00")
            finite.close()
            finite, present = connect(port, False, 1, b"finite-check")
            assert present
            finite.sendall(b"\xe0\x00")
            finite.close()
            time.sleep(1.4)
            finite, present = connect(port, False, 1, b"finite-check")
            assert not present
            finite.sendall(b"\xe0\x00")
            finite.close()
            finite, present = connect(port, True, 5, b"finite-restart")
            assert not present
            finite.sendall(b"\xe0\x00")
            finite.close()
            stop(broker)
            broker = start(port, state)
            finite, present = connect(port, False, 5, b"finite-restart")
            assert present
            finite.sendall(b"\xe0\x00")
            finite.close()
            time.sleep(5.3)
            stop(broker)
            broker = start(port, state)
            finite, present = connect(port, False, 5, b"finite-restart")
            assert not present
            finite.sendall(b"\xe0\x00")
            finite.close()
            print("PASS: MQTT 5 resume, client/Mosquitto offline QoS1 after restart, expiry zero clears session")
            print("PASS: finite Session Expiry resumes before deadline and expires automatically across restart")
        finally:
            if broker.poll() is None:
                stop(broker)


if __name__ == "__main__":
    main()
