#!/usr/bin/env python3
"""P208: invalid PUBACK/PUBREC/PUBCOMP fixed-header flags on real TCP."""
import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


def main():
    assert BROKER.is_file(), "build Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p208-qos-ack-flags-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p208-watcher")
            subscribe(watcher)
            for index, header in enumerate((0x41, 0x4f, 0x51, 0x5f, 0x71, 0x7f)):
                will = f"p208-will-{index}".encode()
                source = connect_will(port, f"p208-source-{index}".encode(), 0, 0, will)
                source.sendall(bytes([header, 0]))
                assert packet(source) == (0xe0, b"\x81\x00")
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, will)

                legacy = connect_311(port)
                legacy.sendall(bytes([header, 0]))
                assert legacy.recv(1) == b""
                legacy.close()
            healthy, _ = connect(port, True, 0, b"p208-healthy")
            healthy.sendall(b"\xc0\x00")
            assert packet(healthy) == (0xd0, b"")
            healthy.sendall(b"\xe0\x00")
            watcher.sendall(b"\xe0\x00")
            healthy.close()
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P208_QOS_ACK_FLAGS_PASS PUBACK/PUBREC/PUBCOMP, Will, 311, healthy")


if __name__ == "__main__":
    main()
