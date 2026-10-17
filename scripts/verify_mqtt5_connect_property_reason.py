#!/usr/bin/env python3
"""P183: invalid CONNECT/Will property identifiers receive CONNACK 0x81."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import expect_silence, subscribe


def rejected_connect(port, identity, connect_properties, will_properties=None):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    flags = 0x06 if will_properties is not None else 0x02
    body = b"\x00\x04MQTT\x05" + bytes([flags]) + b"\x00\x1e"
    body += bytes([len(connect_properties)]) + connect_properties
    body += len(identity).to_bytes(2, "big") + identity
    if will_properties is not None:
        body += bytes([len(will_properties)]) + will_properties
        body += b"\x00\x0awill/check\x00\x04will"
    assert len(body) < 128
    stream.sendall(bytes([0x10, len(body)]) + body)
    return stream


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p183-connect-property-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p183-watcher")
            subscribe(watcher)
            expiry = b"\x11\xff\xff\xff\xff"
            cases = (
                (b"p183-connect", expiry + b"\x0b", None),
                (b"p183-will", expiry, b"\x21"),
                (b"p183-exact", b"\x27\x00\x00\x00\x05\x0b", None),
            )
            for identity, connect_properties, will_properties in cases:
                source = rejected_connect(port, identity, connect_properties, will_properties)
                assert packet(source) == (0x20, b"\x00\x81\x00")
                assert source.recv(1) == b""
                source.close()
                resumed, present = connect(port, False, 0xffffffff, identity)
                assert not present, "rejected CONNECT must not create a session"
                resumed.sendall(b"\xe0\x00")
                resumed.close()
            expect_silence(watcher, 0.3)
            too_small = rejected_connect(port, b"p183-limit", b"\x27\x00\x00\x00\x04\x0b")
            assert too_small.recv(1) == b"", "Maximum Packet Size 4 cannot fit CONNACK"
            too_small.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P183_CONNECT_PROPERTY_REASON_PASS CONNECT, Will, no session/Will, max packet")


if __name__ == "__main__":
    main()
