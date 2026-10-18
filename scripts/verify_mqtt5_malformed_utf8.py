#!/usr/bin/env python3
"""P195: malformed UTF-8 yields MQTT 5 DISCONNECT 0x81 without side effects."""

import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


TOPIC = b"p195/data"


def frame(header, body):
    assert len(body) < 128
    return bytes([header, len(body)]) + body


def publish(topic, properties=b"", payload=b"discard", retain=False, mqtt5=True):
    body = len(topic).to_bytes(2, "big") + topic
    if mqtt5:
        body += bytes([len(properties)]) + properties
    return frame(0x31 if retain else 0x30, body + payload)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    bad_pair = b"\x26\x00\x01\xff\x00\x01v"
    cases = (
        ("publish-topic", publish(b"\xff", retain=True)),
        ("publish-property", publish(TOPIC, bad_pair, retain=True)),
        ("subscribe-filter", frame(0x82, b"\x00\x01\x00\x00\x01\xff\x00")),
        ("auth-method", frame(0xF0, b"\x19\x04\x15\x00\x01\xff")),
        ("disconnect-reason", frame(0xE0, b"\x00\x04\x1f\x00\x01\x00")),
        ("puback-reason", frame(0x40, b"\x00\x01\x00\x04\x1f\x00\x01\xff")),
    )
    with tempfile.TemporaryDirectory(prefix="xmqr-p195-utf8-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p195-watcher")
            subscribe(watcher)
            subscribe(watcher, TOPIC)
            for index, (name, wire) in enumerate(cases):
                will = f"p195-will-{index}".encode()
                source = connect_will(port, f"p195-{name}".encode(), 0, 0, will)
                source.sendall(wire)
                assert packet(source) == (0xE0, b"\x81\x00"), name
                assert source.recv(1) == b"", name
                source.close()
                expect_will(watcher, will)
                expect_silence(watcher, 0.15)

            late, _ = connect(port, True, 0, b"p195-late")
            subscribe(late, TOPIC)
            expect_silence(late, 0.2)  # Neither retained PUBLISH was stored.
            late.sendall(b"\xe0\x00")
            late.close()

            legacy = connect_311(port)
            legacy.sendall(publish(b"\xff", mqtt5=False))
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
            legacy.close()

            valid, _ = connect(port, True, 0, b"p195-valid")
            valid.sendall(publish(TOPIC, payload=b"valid"))
            assert packet(watcher)[1].endswith(b"valid")
            valid.sendall(b"\xe0\x00")
            valid.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P195_UTF8_PASS 0x81, Will, no fanout/retained, valid, MQTT311")


if __name__ == "__main__":
    main()
