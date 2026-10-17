#!/usr/bin/env python3
"""P146: full durable QoS2 quota after restart returns MQTT 5 PUBREC 0x97."""
import socket
import tempfile

from verify_mqtt5_connack_receive_maximum import connect, publish, start, stop, subscribe
from verify_mqtt5_sessions import BROKER, packet


TOPIC = b"p144/flow"


def pubrel(stream, packet_id):
    stream.sendall(b"\x62\x02" + packet_id.to_bytes(2, "big"))
    assert packet(stream) == (0x70, packet_id.to_bytes(2, "big"))


def receive_qos2(stream, expected):
    header, body = packet(stream)
    assert header & 0x06 == 0x04 and body.endswith(b"\x00" + expected), (header, body)
    offset = 2 + int.from_bytes(body[:2], "big")
    packet_id = body[offset:offset + 2]
    stream.sendall(b"\x50\x02" + packet_id)
    assert packet(stream) == (0x62, packet_id)
    stream.sendall(b"\x70\x02" + packet_id)


def send_qos2(stream, packet_id, payload, duplicate=False):
    body = (len(TOPIC).to_bytes(2, "big") + TOPIC
            + packet_id.to_bytes(2, "big") + b"\x00" + payload)
    stream.sendall(bytes([0x3c if duplicate else 0x34, len(body)]) + body)
    return packet(stream)


def main():
    assert BROKER.is_file(), "build Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p146-quota-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state, 1)
        try:
            subscriber, props, present = connect(port, b"p146-sub", persistent=True)
            assert not present and props[0x21] == 1
            subscribe(subscriber)
            publisher, props, present = connect(port, b"p146-pub", persistent=True)
            assert not present and props[0x21] == 1
            publish(publisher, 2, 7, b"old")
            publisher.close()
            subscriber.close()
        finally:
            stop(broker)
        broker = start(port, state, 1)
        try:
            subscriber, props, present = connect(port, b"p146-sub", clean=False,
                                                 persistent=True)
            assert present and props[0x21] == 1
            publisher, props, present = connect(port, b"p146-pub", clean=False,
                                                persistent=True)
            assert present and props[0x21] == 1
            assert send_qos2(publisher, 8, b"rejected") == (0x50, b"\x00\x08\x97\x00")
            subscriber.settimeout(0.2)
            try:
                packet(subscriber)
                raise AssertionError("rejected QoS2 was delivered")
            except socket.timeout:
                pass
            subscriber.settimeout(4)
            assert send_qos2(publisher, 7, b"duplicate", duplicate=True) == (0x50, b"\x00\x07")
            pubrel(publisher, 7)
            receive_qos2(subscriber, b"old")
            assert send_qos2(publisher, 9, b"new") == (0x50, b"\x00\x09")
            pubrel(publisher, 9)
            receive_qos2(subscriber, b"new")
            publisher.close()
            subscriber.close()
        finally:
            stop(broker)
    print("PASS: P146 resumed QoS2 full quota, PUBREC 0x97, old transaction, restart/recovery")


if __name__ == "__main__":
    main()
