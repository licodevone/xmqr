#!/usr/bin/env python3
"""P162: negotiate Server Keep Alive and exercise the resulting idle deadline."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import packet


ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / "target/debug/mqtt-broker"
CLIENT = ROOT.parent / "xmqr-client/target/debug/mqtt-client"


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def start(port, state, cap):
    env = {
        "MQTT_MODE": "open-lab",
        "MQTT_STATE_DIR": state,
        "MQTT_BIND": f"127.0.0.1:{port}",
        "MQTT_SERVER_KEEP_ALIVE_SECONDS": str(cap),
    }
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


def connect(port, level, keep_alive, identity, properties=b""):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    body = (b"\x00\x04MQTT" + bytes([level, 2])
            + keep_alive.to_bytes(2, "big"))
    if level == 5:
        body += bytes([len(properties)]) + properties
    body += len(identity).to_bytes(2, "big") + identity
    stream.sendall(bytes([0x10, len(body)]) + body)
    return stream, packet(stream)


def connack_properties(ack):
    assert ack[:2] == b"\x00\x00", ack
    length = ack[2]
    data = ack[3:]
    assert length == len(data), ack
    properties = []
    sizes = {0x27: 4, 0x22: 2, 0x2a: 1, 0x21: 2, 0x13: 2}
    while data:
        identifier = data[0]
        size = sizes[identifier]
        properties.append((identifier, int.from_bytes(data[1:1 + size], "big")))
        data = data[1 + size:]
    return properties


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-server-keep-alive-") as state:
        port = free_port()
        broker = start(port, state, 2)
        try:
            for requested, expected in [(30, [2]), (0, [2]), (2, []), (1, [])]:
                stream, (header, ack) = connect(
                    port, 5, requested, f"keep-{requested}".encode())
                assert header == 0x20
                negotiated = [value for key, value in connack_properties(ack)
                              if key == 0x13]
                assert negotiated == expected, (requested, negotiated, ack)
                stream.sendall(b"\xe0\x00")
                stream.close()

            stream, (header, ack) = connect(
                port, 5, 30, b"too-small", b"\x27\x00\x00\x00\x09")
            assert (header, ack) == (0x20, b"\x00\x95\x00"), ack
            assert stream.recv(1) == b"", "refused connection stayed open"
            stream.close()

            stream, (header, ack) = connect(port, 4, 30, b"legacy")
            assert (header, ack) == (0x20, b"\x00\x00")
            stream.sendall(b"\xe0\x00")
            stream.close()

            stream, (header, ack) = connect(port, 5, 30, b"idle")
            assert header == 0x20 and (0x13, 2) in connack_properties(ack)
            assert stream.recv(1) == b"", "idle connection exceeded negotiated 3s deadline"
            stream.close()

            stream, (header, ack) = connect(port, 5, 30, b"ping")
            assert header == 0x20 and (0x13, 2) in connack_properties(ack)
            for _ in range(2):
                time.sleep(1.6)
                stream.sendall(b"\xc0\x00")
                assert packet(stream) == (0xd0, b""), "PINGREQ did not reset deadline"
            stream.sendall(b"\xe0\x00")
            stream.close()

            client = subprocess.Popen(
                [CLIENT, "sub", "--open-lab", "--protocol-version", "5",
                 "--host", "127.0.0.1", "--port", str(port),
                 "--keepalive-seconds", "30", "--topic", "keep/#", "--count", "1"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                time.sleep(4.5)
                assert client.poll() is None, (
                    "client did not honor server Keep Alive", client.stderr.read())
            finally:
                client.terminate()
                client.communicate(timeout=6)
        finally:
            broker.terminate()
            broker.wait(timeout=8)
    print("P162_KEEP_ALIVE_PASS cap, zero/equal/lower, packet budget, idle, ping, client, MQTT311")


if __name__ == "__main__":
    main()
