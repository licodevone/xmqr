#!/usr/bin/env python3
"""P200: malformed reserved flags close MQTT 5 before mutating session state."""
import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


def frame(header, body):
    assert len(body) < 128
    return bytes([header, len(body)]) + body


def subscription_body(topic, unsubscribe=False):
    return (b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic
            + (b"" if unsubscribe else b"\x00"))


def publish(stream, topic, payload, qos2=False):
    body = len(topic).to_bytes(2, "big") + topic
    if qos2:
        body += b"\x00\x07"
    body += b"\x00" + payload
    stream.sendall(frame(0x34 if qos2 else 0x30, body))


def invalid_vectors(port, watcher):
    bodies = {6: b"\x00\x07", 8: subscription_body(b"p200/sub"),
              10: subscription_body(b"p200/sub", True)}
    for kind, body in bodies.items():
        for flags in (0, 1, 3, 15):
            marker = f"p200-{kind}-{flags}".encode()
            source = connect_will(port, marker, 0, 0, marker)
            source.sendall(frame((kind << 4) | flags, body))
            assert packet(source) == (0xe0, b"\x81\x00"), (kind, flags)
            assert source.recv(1) == b""
            source.close()
            expect_will(watcher, marker)
        legacy = connect_311(port)
        legacy.sendall(frame(kind << 4, body))
        assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
        legacy.close()


def no_partial_subscribe(port):
    identity = b"p200-sub-session"
    source, _ = connect(port, True, 60, identity)
    source.sendall(frame(0x80, subscription_body(b"p200/no-sub")))
    assert packet(source) == (0xe0, b"\x81\x00")
    source.close()
    resumed, present = connect(port, False, 60, identity)
    assert present
    publisher, _ = connect(port, True, 0, b"p200-no-sub-pub")
    publish(publisher, b"p200/no-sub", b"absent")
    expect_silence(resumed, 0.25)
    publisher.sendall(b"\xe0\x00")
    resumed.sendall(b"\xe0\x00")
    publisher.close()
    resumed.close()


def no_partial_unsubscribe(port):
    identity = b"p200-unsub-session"
    topic = b"p200/still-sub"
    source, _ = connect(port, True, 60, identity)
    subscribe(source, topic)
    source.sendall(frame(0xa0, subscription_body(topic, True)))
    assert packet(source) == (0xe0, b"\x81\x00")
    source.close()
    resumed, present = connect(port, False, 60, identity)
    assert present
    publisher, _ = connect(port, True, 0, b"p200-still-sub-pub")
    publish(publisher, topic, b"present")
    header, body = packet(resumed)
    assert header & 0xf0 == 0x30 and body.endswith(b"present"), (header, body)
    publisher.sendall(b"\xe0\x00")
    resumed.sendall(b"\xe0\x00")
    publisher.close()
    resumed.close()


def no_partial_pubrel(port, watcher):
    identity = b"p200-qos2-session"
    topic = b"p200/qos2"
    subscribe(watcher, topic)
    source, _ = connect(port, True, 60, identity)
    publish(source, topic, b"once", qos2=True)
    header, body = packet(source)
    assert header == 0x50 and body[:2] == b"\x00\x07", (header, body)
    source.sendall(frame(0x60, b"\x00\x07"))
    assert packet(source) == (0xe0, b"\x81\x00")
    source.close()
    expect_silence(watcher, 0.25)
    resumed, present = connect(port, False, 60, identity)
    assert present
    resumed.sendall(b"\x62\x02\x00\x07")
    header, body = packet(resumed)
    assert header == 0x70 and body[:2] == b"\x00\x07", (header, body)
    header, body = packet(watcher)
    assert header & 0xf0 == 0x30 and body.endswith(b"once"), (header, body)
    resumed.sendall(b"\xe0\x00")
    resumed.close()


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p200-flags-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p200-watcher")
            subscribe(watcher)
            invalid_vectors(port, watcher)
            no_partial_subscribe(port)
            no_partial_unsubscribe(port)
            no_partial_pubrel(port, watcher)
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P200_FLAGS_PASS reserved flags, Will, MQTT311, no partial SUB/UNSUB/PUBREL")


if __name__ == "__main__":
    main()
