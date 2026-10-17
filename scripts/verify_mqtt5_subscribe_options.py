#!/usr/bin/env python3
"""P148/C85: No Local and Retain As Published over TCP and durable restart."""
import select
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from verify_mqtt5_connack_receive_maximum import start, stop
from verify_mqtt5_sessions import packet


TOPIC = b"p148/options"
CLIENT_CHECK = Path(__file__).resolve().parents[2] / "xmqr-client/scripts/verify_subscribe_options_mqtt5.py"


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def connect(port, identity, clean=True, persistent=False):
    stream = socket.create_connection(("127.0.0.1", port), timeout=5)
    stream.settimeout(5)
    properties = b"\x11\xff\xff\xff\xff" if persistent else b""
    body = (b"\x00\x04MQTT\x05" + bytes([2 if clean else 0]) + b"\x00\x1e"
            + bytes([len(properties)]) + properties
            + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == 0, ack
    return stream, bool(ack[0] & 1)


def subscribe(stream):
    body = b"\x00\x01\x00" + len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x2e"
    stream.sendall(bytes([0x82, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x90 and ack[-1] == 2, ack


def publish(stream, payload, qos, packet_id):
    body = len(TOPIC).to_bytes(2, "big") + TOPIC
    if qos:
        body += packet_id.to_bytes(2, "big")
    body += b"\x00" + payload
    stream.sendall(bytes([0x31 | qos << 1, len(body)]) + body)
    if qos:
        header, ack = packet(stream)
        assert header == (0x40 if qos == 1 else 0x50) and ack[:2] == packet_id.to_bytes(2, "big"), (header, ack)
        if qos == 2:
            stream.sendall(bytes([0x62, 4]) + packet_id.to_bytes(2, "big") + b"\x00\x00")
            header, ack = packet(stream)
            assert header == 0x70 and ack[:2] == packet_id.to_bytes(2, "big"), (header, ack)


def receive(stream, payload, qos):
    header, body = packet(stream)
    assert header & 0xf9 == 0x31 and (header >> 1) & 3 == qos, (header, body)
    assert body.endswith(payload), body
    if qos:
        packet_id = body[2 + len(TOPIC):4 + len(TOPIC)]
        assert packet_id != b"\x00\x00"
        if qos == 1:
            stream.sendall(b"\x40\x04" + packet_id + b"\x00\x00")
        else:
            stream.sendall(b"\x50\x04" + packet_id + b"\x00\x00")
            header, released = packet(stream)
            assert header == 0x62 and released[:2] == packet_id, (header, released)
            stream.sendall(b"\x70\x04" + packet_id + b"\x00\x00")


def exercise(port, clean):
    same, present = connect(port, b"p148-durable", clean=clean, persistent=True)
    assert present is not clean
    try:
        if clean:
            subscribe(same)
        for qos in range(3):
            publish(same, f"self-{qos}".encode(), qos, qos + 10)
            assert not select.select([same], [], [], 0.15)[0], f"No Local forwarded self QoS{qos}"
            other, _ = connect(port, f"p148-other-{qos}".encode())
            try:
                publish(other, f"other-{qos}".encode(), qos, qos + 20)
            finally:
                other.close()
            receive(same, f"other-{qos}".encode(), qos)
        same.sendall(b"\xe0\x00")
    finally:
        same.close()


def main():
    assert CLIENT_CHECK.is_file(), "client C85 integration script missing"
    with tempfile.TemporaryDirectory(prefix="xmqr-p148-options-") as state:
        port = free_port()
        broker = start(port, state, 32)
        try:
            exercise(port, clean=True)
        finally:
            stop(broker)
        broker = start(port, state, 32)
        try:
            exercise(port, clean=False)
            subprocess.run([sys.executable, str(CLIENT_CHECK), "--port", str(port)], check=True, timeout=20)
        finally:
            stop(broker)
    print("P148_C85_PASS QoS0/1/2 No Local/RAP, session restart and client")


if __name__ == "__main__":
    main()
