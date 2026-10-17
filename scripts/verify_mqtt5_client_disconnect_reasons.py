#!/usr/bin/env python3
"""Exercise client-side MQTT 5 error DISCONNECT reasons and durable Will."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


def error_disconnect(stream, reason):
    stream.sendall(bytes([0xe0, 2, reason, 0]))
    assert stream.recv(1) == b"", "server did not close after DISCONNECT"
    stream.close()


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-disconnect-reasons-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0xFFFFFFFF, b"error-reason-watcher")
            subscribe(watcher)
            source = connect_will(port, b"error-80", 0, 0xFFFFFFFF, b"error-80-will")
            error_disconnect(source, 0x80)
            expect_will(watcher, b"error-80-will")

            source = connect_will(port, b"error-93", 2, 0xFFFFFFFF, b"error-93-will")
            error_disconnect(source, 0x93)
            expect_silence(watcher, 0.2)
            watcher.close()
            stop(broker)
            broker = start(port, state)
            watcher, present = connect(port, False, 0xFFFFFFFF, b"error-reason-watcher")
            assert present
            expect_will(watcher, b"error-93-will")
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P174_CLIENT_DISCONNECT_PASS reason 0x80, 0x93, durable Will restart")


if __name__ == "__main__":
    main()
