#!/usr/bin/env python3
"""P180: MQTT 5 User Property on SUBSCRIBE/UNSUBSCRIBE and atomic rejection."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop


TOPIC = b"p180/user-property"
PAIR = b"\x26\x00\x01k\x00\x01v"
PROPERTIES = PAIR + PAIR


def send_sub(stream, packet_id, properties):
    body = packet_id.to_bytes(2, "big") + bytes([len(properties)]) + properties
    body += len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00"
    stream.sendall(bytes([0x82, len(body)]) + body)


def send_unsub(stream, packet_id, properties):
    body = packet_id.to_bytes(2, "big") + bytes([len(properties)]) + properties
    body += len(TOPIC).to_bytes(2, "big") + TOPIC
    stream.sendall(bytes([0xa2, len(body)]) + body)


def publish(port, payload):
    source, _ = connect(port, True, 0, b"p180-source")
    body = len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00" + payload
    source.sendall(bytes([0x30, len(body)]) + body)
    source.sendall(b"\xe0\x00")
    source.close()


def expect_delivery(stream, payload):
    header, body = packet(stream)
    assert header == 0x30 and body.endswith(payload), (header, body)


def expect_no_delivery(stream):
    stream.settimeout(0.5)
    try:
        unexpected = packet(stream)
    except socket.timeout:
        pass
    else:
        raise AssertionError(f"unexpected delivery: {unexpected}")
    stream.settimeout(4)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p180-user-properties-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            session, present = connect(port, True, 0xffffffff, b"p180-session")
            assert not present
            send_sub(session, 1, PAIR + b"\x0b\x03" + PAIR)
            assert packet(session) == (0x90, b"\x00\x01\x00\x00")
            publish(port, b"before")
            expect_delivery(session, b"before")

            send_unsub(session, 2, b"\x1f\x00\x00")
            assert packet(session) == (0xe0, b"\x81\x00")
            assert session.recv(1) == b"", "invalid UNSUBSCRIBE must close"
            session.close()
            session, present = connect(port, False, 0xffffffff, b"p180-session")
            assert present
            publish(port, b"still-subscribed")
            expect_delivery(session, b"still-subscribed")

            send_unsub(session, 3, PROPERTIES)
            assert packet(session) == (0xb0, b"\x00\x03\x00\x00")
            publish(port, b"after-remove")
            expect_no_delivery(session)

            send_sub(session, 4, b"\x1f\x00\x00")
            assert packet(session) == (0xe0, b"\x81\x00")
            assert session.recv(1) == b"", "invalid SUBSCRIBE must close"
            session.close()
            session, present = connect(port, False, 0xffffffff, b"p180-session")
            assert present
            publish(port, b"still-unsubscribed")
            expect_no_delivery(session)
            session.sendall(b"\xe0\x00")
            session.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P180_SUBSCRIPTION_USER_PROPERTIES_PASS repeat, identifier, durable atomic rejection")


if __name__ == "__main__":
    main()
