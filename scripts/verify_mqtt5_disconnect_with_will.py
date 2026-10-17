#!/usr/bin/env python3
"""Exercise explicit MQTT 5 DISCONNECT with Will across restart."""
import socket
import tempfile
import time

from verify_mqtt5_sessions import BROKER, connect, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


DIAGNOSTICS = b"\x1f\x00\x02no\x26\x00\x01k\x00\x01v"


def disconnect(stream, reason, properties=b""):
    body = bytes([reason, len(properties)]) + properties
    stream.sendall(bytes([0xe0, len(body)]) + body)
    stream.close()


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-disconnect-will-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0xFFFFFFFF, b"disconnect-watcher")
            subscribe(watcher)

            source = connect_will(port, b"explicit-will", 0, 0xFFFFFFFF, b"requested")
            disconnect(source, 4, DIAGNOSTICS)
            expect_will(watcher, b"requested")

            source = connect_will(port, b"normal-will", 0, 0xFFFFFFFF, b"cancelled")
            disconnect(source, 0, DIAGNOSTICS)
            expect_silence(watcher, 0.5)

            source = connect_will(port, b"delayed-will", 2, 0xFFFFFFFF, b"after-restart")
            disconnect(source, 4, b"\x11\xff\xff\xff\xff" + DIAGNOSTICS)
            expect_silence(watcher, 0.2)
            watcher.close()
            stop(broker)
            broker = start(port, state)
            watcher, present = connect(port, False, 0xFFFFFFFF, b"disconnect-watcher")
            assert present
            expect_will(watcher, b"after-restart")
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P172_DISCONNECT_WITH_WILL_PASS explicit, normal, delayed restart")


if __name__ == "__main__":
    main()
