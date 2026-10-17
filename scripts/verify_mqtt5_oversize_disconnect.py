#!/usr/bin/env python3
"""Exercise MQTT 5 Packet too large DISCONNECT without reading the body."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


OVERSIZE_HEADER = b"\x30\x80\x80\x04"  # Remaining Length 65536 + 4-byte header.


def connect_311(port):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    identity = b"oversize-311"
    body = (b"\x00\x04MQTT\x04\x02\x00\x1e"
            + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    assert packet(stream) == (0x20, b"\x00\x00")
    return stream


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-oversize-disconnect-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"oversize-watcher")
            subscribe(watcher)
            source = connect_will(port, b"oversize-source", 0, 0, b"oversize-will")
            source.sendall(OVERSIZE_HEADER)
            assert packet(source) == (0xe0, b"\x95\x00")
            assert source.recv(1) == b""
            source.close()
            expect_will(watcher, b"oversize-will")
            watcher.sendall(b"\xe0\x00")
            watcher.close()

            legacy = connect_311(port)
            legacy.sendall(OVERSIZE_HEADER)
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must close without v5 DISCONNECT"
            legacy.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P175_OVERSIZE_DISCONNECT_PASS MQTT5 0x95, Will, MQTT311 close")


if __name__ == "__main__":
    main()
