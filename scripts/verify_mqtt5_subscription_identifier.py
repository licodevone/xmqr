#!/usr/bin/env python3
"""P150/C87: MQTT 5 Subscription Identifier over disposable TCP/v12 state."""
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from verify_mqtt5_connack_receive_maximum import start, stop
from verify_mqtt5_sessions import packet
from verify_mqtt5_subscribe_options import connect, free_port


TOPIC = b"p150/value"
CLIENT = Path(__file__).resolve().parents[2] / "xmqr-client/target/release/mqtt-client"


def subscribe(stream, identifier, filters=(b"p150/value", b"p150/#")):
    properties = b"\x0b" + bytes([identifier])
    body = b"\x00\x01" + bytes([len(properties)]) + properties
    for item in filters:
        body += len(item).to_bytes(2, "big") + item + b"\x02"
    stream.sendall(bytes([0x82, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x90 and ack[-len(filters):] == bytes([2] * len(filters)), ack


def publish(stream, payload, qos, packet_id, retain=False):
    body = len(TOPIC).to_bytes(2, "big") + TOPIC
    if qos:
        body += packet_id.to_bytes(2, "big")
    body += b"\x00" + payload
    stream.sendall(bytes([0x30 | (qos << 1) | int(retain), len(body)]) + body)
    if qos:
        header, ack = packet(stream)
        assert header == (0x40 if qos == 1 else 0x50) and ack[:2] == packet_id.to_bytes(2, "big"), (header, ack)
        if qos == 2:
            stream.sendall(b"\x62\x04" + packet_id.to_bytes(2, "big") + b"\x00\x00")
            header, ack = packet(stream)
            assert header == 0x70 and ack[:2] == packet_id.to_bytes(2, "big"), (header, ack)


def receive(stream, payload, qos, ids, retain=False):
    header, body = packet(stream)
    assert header & 0xf0 == 0x30 and (header >> 1) & 3 == qos and bool(header & 1) == retain, (header, body)
    topic_len = int.from_bytes(body[:2], "big")
    assert body[2:2 + topic_len] == TOPIC, body
    cursor = 2 + topic_len
    packet_id = None
    if qos:
        packet_id = body[cursor:cursor + 2]
        assert packet_id != b"\x00\x00"
        cursor += 2
    property_len = body[cursor]
    cursor += 1
    properties = body[cursor:cursor + property_len]
    cursor += property_len
    assert properties == b"".join(b"\x0b" + bytes([value]) for value in ids), properties
    assert body[cursor:] == payload, body
    if qos == 1:
        stream.sendall(b"\x40\x04" + packet_id + b"\x00\x00")
    elif qos == 2:
        stream.sendall(b"\x50\x04" + packet_id + b"\x00\x00")
        header, released = packet(stream)
        assert header == 0x62 and released[:2] == packet_id, (header, released)
        stream.sendall(b"\x70\x04" + packet_id + b"\x00\x00")


def barrier(stream):
    stream.sendall(b"\xc0\x00")
    assert packet(stream) == (0xd0, b"")


def rejected(port, identity, frame):
    with connect(port, identity)[0] as stream:
        stream.sendall(frame)
        stream.settimeout(3)
        first = stream.recv(1)
        assert first in (b"", b"\xe0"), f"malformed packet accepted: {first!r}"


def main():
    assert CLIENT.is_file(), "build client C87 release binary first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p150-") as state:
        port = free_port()
        broker = start(port, state, 32)
        try:
            subscriber, present = connect(port, b"p150-durable", persistent=True)
            assert not present
            subscribe(subscriber, 17)
            with connect(port, b"p150-publisher")[0] as publisher:
                for qos in range(3):
                    payload = f"live-{qos}".encode()
                    publish(publisher, payload, qos, qos + 10)
                    receive(subscriber, payload, qos, [17, 17])
                    barrier(subscriber)
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
        finally:
            stop(broker)
        broker = start(port, state, 32)
        try:
            subscriber, present = connect(port, b"p150-durable", clean=False, persistent=True)
            assert present
            with connect(port, b"p150-publisher-after")[0] as publisher:
                publish(publisher, b"after-restart", 1, 30)
            receive(subscriber, b"after-restart", 1, [17, 17])
            barrier(subscriber)
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            with connect(port, b"p150-publisher-offline")[0] as publisher:
                publish(publisher, b"offline", 1, 31)
            subscriber, present = connect(port, b"p150-durable", clean=False, persistent=True)
            assert present
            receive(subscriber, b"offline", 1, [17, 17])
            barrier(subscriber)
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            with connect(port, b"p150-retained-publisher")[0] as publisher:
                publish(publisher, b"retained", 1, 32, retain=True)
            with connect(port, b"p150-retained-sub")[0] as retained:
                subscribe(retained, 19, (TOPIC,))
                receive(retained, b"retained", 1, [19], retain=True)
                barrier(retained)
            # Client C87 wire/JSONL against the XMQR broker, after a retained publication.
            result = subprocess.run([str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
                                     "--port", str(port), "--topic", TOPIC.decode(),
                                     "--subscription-identifier", "23", "--count", "1",
                                     "--output", "jsonl"], capture_output=True, timeout=12)
            assert result.returncode == 0 and b'"subscription_identifiers":[23]' in result.stdout, (result.stdout, result.stderr)
            filter_bytes = len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00"
            for identity, properties in [(b"p150-zero", b"\x0b\x00"),
                                         (b"p150-duplicate", b"\x0b\x11\x0b\x12")]:
                body = b"\x00\x03" + bytes([len(properties)]) + properties + filter_bytes
                rejected(port, identity, bytes([0x82, len(body)]) + body)
            body = len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x02\x0b\x11x"
            rejected(port, b"p150-publish-property", bytes([0x30, len(body)]) + body)
        finally:
            stop(broker)
    print("P150_C87_PASS live QoS0/1/2, overlap, v12 restart, offline, retained, client JSONL, malformed properties")


if __name__ == "__main__":
    main()
