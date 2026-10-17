#!/usr/bin/env python3
"""Real TCP MQTT 5 DISCONNECT Session Expiry override and restart."""
import socket
import tempfile
import time

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop


def disconnect(stream, seconds):
    stream.sendall(bytes([0xe0, 7, 0, 5, 0x11]) + seconds.to_bytes(4, "big"))
    assert stream.recv(1) == b""
    stream.close()


def main():
    assert BROKER.is_file(), "build Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-disconnect-expiry-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            first, present = connect(port, True, 5, b"disconnect-zero")
            assert not present
            disconnect(first, 0)
            again, present = connect(port, False, 5, b"disconnect-zero")
            assert not present
            disconnect(again, 0)

            finite, present = connect(port, True, 0xFFFFFFFF, b"disconnect-finite")
            assert not present
            disconnect(finite, 1)
            finite, present = connect(port, False, 0xFFFFFFFF, b"disconnect-finite")
            assert present
            disconnect(finite, 1)
            time.sleep(1.3)
            stop(broker)
            broker = start(port, state)
            finite, present = connect(port, False, 1, b"disconnect-finite")
            assert not present
            disconnect(finite, 0)

            forever, present = connect(port, True, 1, b"disconnect-forever")
            assert not present
            disconnect(forever, 0xFFFFFFFF)
            time.sleep(1.3)
            stop(broker)
            broker = start(port, state)
            forever, present = connect(port, False, 0xFFFFFFFF, b"disconnect-forever")
            assert present
            disconnect(forever, 0)

            invalid, present = connect(port, True, 0, b"disconnect-invalid")
            assert not present
            invalid.sendall(bytes([0xe0, 7, 0, 5, 0x11, 0, 0, 0, 1]))
            assert invalid.recv(1) == b""
            invalid.close()
            check, present = connect(port, False, 1, b"disconnect-invalid")
            assert not present
            disconnect(check, 0)
            print("PASS: MQTT 5 DISCONNECT expiry 0/finite/infinite, restart and invalid zero-to-positive")
        finally:
            if broker.poll() is None:
                stop(broker)


if __name__ == "__main__":
    main()
