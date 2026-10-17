#!/usr/bin/env python3
"""Exercise malformed MQTT Remaining Length after CONNACK."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


MALFORMED_HEADER = b"\x30\x80\x80\x80\x80"


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-malformed-length-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"malformed-watcher")
            subscribe(watcher)
            source = connect_will(port, b"malformed-source", 0, 0, b"malformed-will")
            source.sendall(MALFORMED_HEADER[:4])
            source.settimeout(0.5)
            try:
                premature = source.recv(1)
            except socket.timeout:
                pass
            else:
                raise AssertionError(f"partial header closed prematurely: {premature!r}")
            source.settimeout(4)
            source.sendall(MALFORMED_HEADER[4:])
            assert packet(source) == (0xe0, b"\x81\x00")
            assert source.recv(1) == b""
            source.close()
            expect_will(watcher, b"malformed-will")
            watcher.sendall(b"\xe0\x00")
            watcher.close()

            legacy = connect_311(port)
            legacy.sendall(MALFORMED_HEADER)
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must close without v5 DISCONNECT"
            legacy.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P177_MALFORMED_LENGTH_PASS partial, MQTT5 0x81, Will, MQTT311 close")


if __name__ == "__main__":
    main()
