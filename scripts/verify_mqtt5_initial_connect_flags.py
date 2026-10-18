#!/usr/bin/env python3
"""P207: malformed initial MQTT 5 CONNECT flags never create a session/Will."""
import select
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import subscribe


def malformed_connect(header, level=5, maximum=None):
    identity = b"p207-device"
    topic = b"will/check"
    payload = b"forbidden-will"
    properties = b"" if maximum is None else b"\x27" + maximum.to_bytes(4, "big")
    body = (b"\x00\x04MQTT" + bytes([level, 0x06]) + b"\x00\x1e"
            + bytes([len(properties)]) + properties
            + len(identity).to_bytes(2, "big") + identity
            + b"\x00" + len(topic).to_bytes(2, "big") + topic
            + len(payload).to_bytes(2, "big") + payload)
    assert len(body) < 128
    return bytes([header, len(body)]) + body


def main():
    assert BROKER.is_file(), "build Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p207-connect-flags-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p207-watcher")
            subscribe(watcher)
            for header in (0x11, 0x1f):
                for maximum, expected in ((None, (0x20, b"\x00\x81\x00")), (4, None)):
                    source = socket.create_connection(("127.0.0.1", port), timeout=4)
                    source.settimeout(4)
                    source.sendall(malformed_connect(header, maximum=maximum))
                    if expected is not None:
                        assert packet(source) == expected
                    assert source.recv(1) == b""
                    source.close()
                legacy = socket.create_connection(("127.0.0.1", port), timeout=4)
                legacy.settimeout(4)
                legacy.sendall(malformed_connect(header, level=4))
                assert legacy.recv(1) == b""
                legacy.close()
            assert not select.select([watcher], [], [], 0.3)[0], "invalid CONNECT emitted Will"
            healthy, _ = connect(port, True, 0, b"p207-healthy")
            healthy.sendall(b"\xc0\x00")
            assert packet(healthy) == (0xd0, b"")
            healthy.sendall(b"\xe0\x00")
            watcher.sendall(b"\xe0\x00")
            healthy.close()
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P207_INITIAL_CONNECT_FLAGS_PASS 0x81, limit, Will absent, MQTT311, healthy")


if __name__ == "__main__":
    main()
