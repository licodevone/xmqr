#!/usr/bin/env python3
"""P181: contextual subscription property errors yield MQTT 5 DISCONNECT."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_subscription_user_properties import send_sub, send_unsub
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p181-sub-property-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p181-watcher")
            subscribe(watcher)
            cases = (
                (send_sub, b"\x09", 0x81),
                (send_unsub, b"\x0b", 0x81),
                (send_sub, b"\x0b\x01\x0b\x02", 0x82),
            )
            for index, (sender, properties, reason) in enumerate(cases):
                will = f"p181-will-{index}".encode()
                source = connect_will(port, f"p181-source-{index}".encode(), 0, 0, will)
                sender(source, index + 1, properties)
                assert packet(source) == (0xe0, bytes([reason, 0]))
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, will)

            legacy = connect_311(port)
            send_sub(legacy, 7, b"\x09")
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
            legacy.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P181_SUBSCRIPTION_PROPERTY_DISCONNECT_PASS context, duplicate, Will, MQTT311")


if __name__ == "__main__":
    main()
