#!/usr/bin/env python3
"""P184: semantic CONNECT/Will property errors receive protocol-error CONNACK."""
import socket
import tempfile

from verify_mqtt5_connect_property_reason import rejected_connect
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import expect_silence, subscribe


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p184-connect-semantic-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p184-watcher")
            subscribe(watcher)
            expiry = b"\x11\xff\xff\xff\xff"
            cases = (
                (b"p184-connect", expiry + expiry, None),
                (b"p184-will", expiry, b"\x01\x02"),
                (b"p184-exact", b"\x27\x00\x00\x00\x05\x21\x00\x00", None),
            )
            for identity, connect_properties, will_properties in cases:
                source = rejected_connect(port, identity, connect_properties, will_properties)
                try:
                    response = packet(source)
                except AssertionError as error:
                    raise AssertionError(f"{identity!r}: {error}") from error
                assert response == (0x20, b"\x00\x82\x00"), (identity, response)
                assert source.recv(1) == b""
                source.close()
                resumed, present = connect(port, False, 0xffffffff, identity)
                assert not present, "rejected CONNECT must not create a session"
                resumed.sendall(b"\xe0\x00")
                resumed.close()
            expect_silence(watcher, 0.3)
            too_small = rejected_connect(port, b"p184-limit", b"\x27\x00\x00\x00\x04\x21\x00\x00")
            assert too_small.recv(1) == b"", "Maximum Packet Size 4 cannot fit CONNACK"
            too_small.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P184_CONNECT_PROPERTY_SEMANTIC_REASON_PASS CONNECT, Will, no session/Will, max packet")


if __name__ == "__main__":
    main()
