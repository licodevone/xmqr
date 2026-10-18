#!/usr/bin/env python3
"""P196: malformed initial MQTT 5 CONNECT text receives CONNACK 0x81."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import expect_silence, subscribe


def rejected_connect(port, identity, properties=b"", will_properties=None,
                     will_topic=b"will/check", username=None, level=5):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    flags = 0x02 | (0x04 if will_properties is not None else 0)
    flags |= 0x80 if username is not None else 0
    body = b"\x00\x04MQTT" + bytes([level, flags]) + b"\x00\x1e"
    if level == 5:
        body += bytes([len(properties)]) + properties
    body += len(identity).to_bytes(2, "big") + identity
    if will_properties is not None:
        if level == 5:
            body += bytes([len(will_properties)]) + will_properties
        body += len(will_topic).to_bytes(2, "big") + will_topic + b"\x00\x04will"
    if username is not None:
        body += len(username).to_bytes(2, "big") + username
    assert len(body) < 128
    stream.sendall(bytes([0x10, len(body)]) + body)
    return stream


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p196-connect-utf8-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p196-watcher")
            subscribe(watcher)
            max5 = b"\x27\x00\x00\x00\x05"
            bad_pair = b"\x26\x00\x01\xff\x00\x01v"
            cases = (
                (b"p196-before", max5 + bad_pair, None, b"will/check", None),
                (b"p196-after", bad_pair + max5, None, b"will/check", None),
                (b"\xff", max5, None, b"will/check", None),
                (b"p196-will-content", max5, b"\x03\x00\x01\xff", b"will/check", None),
                (b"p196-will-response", max5, b"\x08\x00\x01\xff", b"will/check", None),
                (b"p196-will-user", max5, bad_pair, b"will/check", None),
                (b"p196-will-topic", max5, b"", b"\xff", None),
                (b"p196-username", max5, None, b"will/check", b"\xff"),
            )
            for identity, props, will_props, topic, username in cases:
                source = rejected_connect(port, identity, props, will_props, topic, username)
                assert packet(source) == (0x20, b"\x00\x81\x00")
                assert source.recv(1) == b"", "rejected CONNECT must close"
                source.close()
                if identity != b"\xff":
                    resumed, present = connect(port, False, 0xffffffff, identity)
                    assert not present, "rejected CONNECT must not create a session"
                    resumed.sendall(b"\xe0\x00")
                    resumed.close()
            fake_id = b"\x26\x00\x02\xff\x27\x00\x01v"
            for props in (max5 + fake_id, fake_id + max5):
                source = rejected_connect(port, b"p196-fake-byte", props)
                assert packet(source) == (0x20, b"\x00\x81\x00")
                assert source.recv(1) == b""
                source.close()
            too_small = rejected_connect(port, b"p196-limit", fake_id + b"\x27\x00\x00\x00\x04")
            assert too_small.recv(1) == b"", "Maximum Packet Size 4 excludes CONNACK"
            too_small.close()
            old = rejected_connect(port, b"\xff", level=4)
            assert old.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 CONNACK"
            old.close()
            valid, present = connect(port, True, 0, b"p196-valid")
            assert not present
            valid.sendall(b"\xe0\x00")
            valid.close()
            expect_silence(watcher, 0.3)
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P196_CONNECT_UTF8_PASS CONNACK, limits, no session/Will, MQTT 3.1.1")


if __name__ == "__main__":
    main()
