#!/usr/bin/env python3
"""P194: a second CONNECT is a protocol error before its body is parsed."""

import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


def second_connect(identity, will_payload):
    topic = b"will/check"
    properties = b"\x11\xff\xff\xff\xff"  # Durable session, if wrongly accepted.
    body = (b"\x00\x04MQTT\x05\x06\x00\x1e"
            + bytes([len(properties)]) + properties
            + len(identity).to_bytes(2, "big") + identity
            + b"\x00"  # No Will properties.
            + len(topic).to_bytes(2, "big") + topic
            + len(will_payload).to_bytes(2, "big") + will_payload)
    assert len(body) < 128
    return bytes([0x10, len(body)]) + body


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p194-second-connect-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p194-watcher")
            subscribe(watcher)
            for index, malformed in enumerate((False, True)):
                original = f"original-{index}".encode()
                shadow = f"shadow-{index}".encode()
                source = connect_will(port, f"p194-source-{index}".encode(), 0, 0, original)
                source.sendall(b"\x10\x00" if malformed else second_connect(shadow, b"shadow-will"))
                assert packet(source) == (0xE0, b"\x82\x00")
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, original)
                expect_silence(watcher, 0.2)
                if not malformed:
                    fresh, present = connect(port, False, 0xFFFFFFFF, shadow)
                    assert not present, "second CONNECT must not create a session"
                    fresh.sendall(b"\xe0\x00")
                    fresh.close()

            legacy = connect_311(port)
            legacy.sendall(second_connect(b"legacy-shadow", b"shadow-will"))
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
            legacy.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P194_SECOND_CONNECT_PASS 0x82, malformed body, original Will, no shadow session/Will, MQTT311")


if __name__ == "__main__":
    main()
