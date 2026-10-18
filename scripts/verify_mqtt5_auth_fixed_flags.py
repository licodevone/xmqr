#!/usr/bin/env python3
"""P204: malformed AUTH fixed-header flags produce MQTT 5 DISCONNECT."""
import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


def main():
    assert BROKER.is_file(), "build Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p204-auth-flags-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p204-watcher")
            subscribe(watcher)
            for index, (header, body) in enumerate(((0xf1, b""), (0xff, b"\xff\x00"))):
                marker = f"p204-will-{index}".encode()
                source = connect_will(port, f"p204-source-{index}".encode(), 0, 0, marker)
                source.sendall(bytes([header, len(body)]) + body)
                assert packet(source) == (0xe0, b"\x81\x00"), hex(header)
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, marker)

                legacy = connect_311(port)
                legacy.sendall(bytes([header, len(body)]) + body)
                assert legacy.recv(1) == b""
                legacy.close()

            healthy, _ = connect(port, True, 0, b"p204-healthy")
            healthy.sendall(b"\xc0\x00")
            assert packet(healthy) == (0xd0, b"")
            healthy.sendall(b"\xe0\x00")
            watcher.sendall(b"\xe0\x00")
            healthy.close()
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P204_AUTH_FLAGS_PASS headers/body, Will, 311, healthy")


if __name__ == "__main__":
    main()
