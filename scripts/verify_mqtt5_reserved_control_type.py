#!/usr/bin/env python3
"""P203: reserved MQTT 5 control type zero is rejected before its body."""
import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


def main():
    assert BROKER.is_file(), "build Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p203-reserved-control-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p203-watcher")
            subscribe(watcher)
            for index, (header, body) in enumerate(((0x00, b""), (0x0f, b"\xff\x00"))):
                marker = f"p203-will-{index}".encode()
                source = connect_will(port, f"p203-source-{index}".encode(), 0, 0, marker)
                source.sendall(bytes([header, len(body)]) + body)
                assert packet(source) == (0xe0, b"\x81\x00"), hex(header)
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, marker)

                legacy = connect_311(port)
                legacy.sendall(bytes([header, len(body)]) + body)
                assert legacy.recv(1) == b""
                legacy.close()

            healthy, _ = connect(port, True, 0, b"p203-healthy")
            healthy.sendall(b"\xc0\x00")
            assert packet(healthy) == (0xd0, b"")
            topic = b"will/check"
            body = len(topic).to_bytes(2, "big") + topic + b"\x00healthy"
            healthy.sendall(bytes([0x30, len(body)]) + body)
            header, body = packet(watcher)
            assert header & 0xf0 == 0x30 and body.endswith(b"healthy")
            healthy.sendall(b"\xe0\x00")
            watcher.sendall(b"\xe0\x00")
            healthy.close()
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P203_RESERVED_CONTROL_PASS headers/body, Will, 311, healthy")


if __name__ == "__main__":
    main()
