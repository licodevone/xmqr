#!/usr/bin/env python3
"""Exercise a rejected QoS 2 PUBREC without PUBREL or replay."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop


TOPIC = b"negative/qos2"


def publisher(port):
    stream, present = connect(port, True, 0, identity=b"negative-qos2-publisher")
    assert not present
    return stream


def publish(stream, payload, packet_id):
    identifier = packet_id.to_bytes(2, "big")
    body = len(TOPIC).to_bytes(2, "big") + TOPIC + identifier + b"\x00" + payload
    assert len(body) < 128
    stream.sendall(bytes([0x34, len(body)]) + body)
    assert packet(stream) == (0x50, identifier)
    stream.sendall(b"\x62\x02" + identifier)
    assert packet(stream) == (0x70, identifier)


def receive(stream, payload):
    header, body = packet(stream)
    assert header & 0xf0 == 0x30 and header & 0x06 == 0x04, (header, body)
    name_length = int.from_bytes(body[:2], "big")
    assert body[2:2 + name_length] == TOPIC, body
    offset = 2 + name_length
    packet_id = int.from_bytes(body[offset:offset + 2], "big")
    assert packet_id != 0 and body[offset + 2] == 0, body
    assert body[offset + 3:] == payload, body
    return packet_id


def subscribe(stream):
    body = b"\x00\x01\x00" + len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x02"
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00\x02")


def accept(stream, packet_id):
    identifier = packet_id.to_bytes(2, "big")
    stream.sendall(b"\x50\x02" + identifier)
    assert packet(stream) == (0x62, identifier)
    stream.sendall(b"\x70\x02" + identifier)
    stream.sendall(b"\xc0\x00")
    assert packet(stream) == (0xd0, b"")


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-negative-pubrec-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            subscriber, present = connect(port, True, 60, identity=b"negative-qos2-subscriber")
            assert not present
            subscribe(subscriber)
            sending = publisher(port)
            publish(sending, b"reject-me", 1)
            first_id = receive(subscriber, b"reject-me")
            properties = b"\x1f\x00\x02no\x26\x00\x01k\x00\x01v"
            ack = (first_id.to_bytes(2, "big") + b"\x80" + bytes([len(properties)])
                   + properties)
            subscriber.sendall(bytes([0x50, len(ack)]) + ack)
            subscriber.sendall(b"\xc0\x00")
            assert packet(subscriber) == (0xd0, b"")

            publish(sending, b"accepted", 2)
            second_id = receive(subscriber, b"accepted")
            accept(subscriber, second_id)
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            sending.close()
            stop(broker)

            broker = start(port, state)
            resumed, present = connect(port, False, 60, identity=b"negative-qos2-subscriber")
            assert present
            resumed.settimeout(0.7)
            try:
                replay = packet(resumed)
            except socket.timeout:
                pass
            else:
                raise AssertionError(f"rejected or completed delivery replayed: {replay}")
            resumed.settimeout(4)
            sending = publisher(port)
            publish(sending, b"after-restart", 3)
            third_id = receive(resumed, b"after-restart")
            accept(resumed, third_id)
            resumed.sendall(b"\xe0\x00")
            resumed.close()
            sending.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P170_NEGATIVE_PUBREC_PASS no PUBREL, quota released, reconnect without replay")


if __name__ == "__main__":
    main()
