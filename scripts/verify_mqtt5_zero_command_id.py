#!/usr/bin/env python3
"""P189: MQTT 5 zero Packet Identifier never changes subscription or publication state."""

import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


TOPIC = b"p189/data"


def send_sub(stream, packet_id):
    body = packet_id.to_bytes(2, "big") + b"\x00" + len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00"
    stream.sendall(bytes([0x82, len(body)]) + body)


def send_unsub(stream, packet_id):
    body = packet_id.to_bytes(2, "big") + b"\x00" + len(TOPIC).to_bytes(2, "big") + TOPIC
    stream.sendall(bytes([0xA2, len(body)]) + body)


def send_publish(stream, packet_id, qos, payload, mqtt5=True, retain=False):
    body = len(TOPIC).to_bytes(2, "big") + TOPIC
    if qos:
        body += packet_id.to_bytes(2, "big")
    if mqtt5:
        body += b"\x00"
    body += payload
    header = 0x30 | (qos << 1) | int(retain)
    stream.sendall(bytes([header, len(body)]) + body)


def publish_valid(port, payload):
    source, _ = connect(port, True, 0, b"p189-publisher")
    send_publish(source, 0, 0, payload)
    source.sendall(b"\xc0\x00")
    assert packet(source) == (0xD0, b"")
    source.sendall(b"\xe0\x00")
    source.close()


def expect_payload(stream, payload):
    header, body = packet(stream)
    assert header & 0xF0 == 0x30 and body.endswith(payload), (header, body)


def expect_protocol_error(stream):
    assert packet(stream) == (0xE0, b"\x82\x00")
    assert stream.recv(1) == b""
    stream.close()


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p189-zero-command-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p189-watcher")
            subscribe(watcher)
            subscribe(watcher, TOPIC)

            zero_sub = connect_will(port, b"p189-zero-sub", 0, 60, b"zero-sub")
            send_sub(zero_sub, 0)
            expect_protocol_error(zero_sub)
            expect_will(watcher, b"zero-sub")
            resumed, present = connect(port, False, 60, b"p189-zero-sub")
            assert present
            publish_valid(port, b"after-zero-sub")
            expect_payload(watcher, b"after-zero-sub")
            expect_silence(resumed, 0.25)
            resumed.sendall(b"\xe0\x00")
            resumed.close()

            zero_unsub = connect_will(port, b"p189-zero-unsub", 0, 60, b"zero-unsub")
            subscribe(zero_unsub, TOPIC)
            send_unsub(zero_unsub, 0)
            expect_protocol_error(zero_unsub)
            expect_will(watcher, b"zero-unsub")
            resumed, present = connect(port, False, 60, b"p189-zero-unsub")
            assert present
            publish_valid(port, b"after-zero-unsub")
            expect_payload(watcher, b"after-zero-unsub")
            expect_payload(resumed, b"after-zero-unsub")
            resumed.sendall(b"\xe0\x00")
            resumed.close()

            for qos in (1, 2):
                will = f"zero-publish-qos{qos}".encode()
                source = connect_will(port, will, 0, 0, will)
                send_publish(source, 0, qos, b"not-published", retain=True)
                expect_protocol_error(source)
                expect_will(watcher, will)
                expect_silence(watcher, 0.2)

            late, _ = connect(port, True, 0, b"p189-late")
            subscribe(late, TOPIC)
            expect_silence(late, 0.25)
            late.sendall(b"\xe0\x00")
            late.close()

            for sender in (send_sub, send_unsub):
                legacy = connect_311(port)
                sender(legacy, 0)
                assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
                legacy.close()
            for qos in (1, 2):
                legacy = connect_311(port)
                send_publish(legacy, 0, qos, b"not-published", mqtt5=False)
                assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
                legacy.close()

            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P189_ZERO_COMMAND_ID_PASS sub, unsub, QoS1/2, Will, durable subscription, retained, MQTT311")


if __name__ == "__main__":
    main()
