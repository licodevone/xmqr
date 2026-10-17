#!/usr/bin/env python3
"""P186: AUTH/DISCONNECT property context and duplication reason codes."""
import socket
import tempfile
import time

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


def send_control(stream, header, properties):
    body = bytes([0x19 if header == 0xf0 else 0, len(properties)]) + properties
    stream.sendall(bytes([header, len(body)]) + body)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p186-control-property-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p186-watcher")
            subscribe(watcher)
            cases = (
                (0xf0, b"\x11\x00\x00\x00\x01", 0x81),
                (0xf0, b"\x15\x00\x01a\x15\x00\x01b", 0x82),
                (0xe0, b"\x15\x00\x01a", 0x81),
                (0xe0, b"\x11\x00\x00\x00\x02\x11\x00\x00\x00\x03", 0x82),
            )
            for index, (header, properties, reason) in enumerate(cases):
                identity = f"p186-source-{index}".encode()
                will = f"p186-will-{index}".encode()
                source = connect_will(port, identity, 0, 0xffffffff, will)
                send_control(source, header, properties)
                assert packet(source) == (0xe0, bytes([reason, 0]))
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, will)
                if index == 3:
                    time.sleep(2.2)
                resumed, present = connect(port, False, 0xffffffff, identity)
                assert present, "invalid control property changed durable expiry/session"
                resumed.sendall(b"\xe0\x00")
                resumed.close()

            legacy = connect_311(port)
            send_control(legacy, 0xe0, b"\x15\x00\x01a")
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
            legacy.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P186_CONTROL_PROPERTY_REASONS_PASS AUTH, DISCONNECT, Will, durable state, MQTT311")


if __name__ == "__main__":
    main()
