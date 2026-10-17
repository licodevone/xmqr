#!/usr/bin/env python3
"""Exercise MQTT 5 protocol error DISCONNECT for fixed-header flags."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-fixed-flags-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"flags-watcher")
            subscribe(watcher)
            for index, invalid in enumerate((b"\xc1\x00", b"\xe1\x00")):
                will = f"flags-will-{index}".encode()
                source = connect_will(port, f"flags-source-{index}".encode(), 0, 0, will)
                source.sendall(invalid)
                assert packet(source) == (0xe0, b"\x82\x00")
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, will)

                legacy = connect_311(port)
                legacy.sendall(invalid)
                assert legacy.recv(1) == b"", "MQTT 3.1.1 must close without v5 DISCONNECT"
                legacy.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P178_FIXED_HEADER_FLAGS_PASS PINGREQ, DISCONNECT, Will, MQTT311 close")


if __name__ == "__main__":
    main()
