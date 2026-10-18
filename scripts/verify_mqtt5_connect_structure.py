#!/usr/bin/env python3
"""P199: malformed fields after complete CONNECT properties receive CONNACK 0x81."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import expect_silence, subscribe


def send_connect(port, flags, properties, suffix, level=5):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    body = b"\x00\x04MQTT" + bytes([level, flags]) + b"\x00\x1e"
    if level == 5:
        body += bytes([len(properties)]) + properties
    body += suffix
    assert len(body) < 128
    stream.sendall(bytes([0x10, len(body)]) + body)
    return stream


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p199-connect-structure-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p199-watcher")
            subscribe(watcher)
            expiry = b"\x11\xff\xff\xff\xff"
            max5 = b"\x27\x00\x00\x00\x05"
            identity = b"p199-device"
            client = len(identity).to_bytes(2, "big") + identity
            cases = (
                (0x02, b"\x00\x0cp199-device", "client-id"),
                (0x06, client + b"\x00\x00\x0bwill/check", "will-topic"),
                (0x06, client + b"\x00\x00\x0awill/check\x00\x05will", "will-payload"),
                (0x82, client + b"\x00\x03ab", "username"),
                (0x42, client + b"\x00\x03ab", "password"),
                (0x02, client + b"\x00", "trailing-byte"),
            )
            for flags, suffix, label in cases:
                source = send_connect(port, flags, expiry + max5, suffix)
                assert packet(source) == (0x20, b"\x00\x81\x00"), label
                assert source.recv(1) == b"", label
                source.close()
                resumed, present = connect(port, False, 0, identity)
                assert not present, f"{label} created a session"
                resumed.sendall(b"\xe0\x00")
                resumed.close()
            too_small = send_connect(port, 0x02, expiry + b"\x27\x00\x00\x00\x04",
                                     b"\x00\x0cp199-device")
            assert too_small.recv(1) == b"", "Maximum Packet Size 4 excludes CONNACK"
            too_small.close()
            embedded = send_connect(port, 0x06, expiry,
                                    client + b"\x00\x00\x0awill/check\x00\x05x\x27\x00\x00\x04\x00")
            assert packet(embedded) == (0x20, b"\x00\x81\x00")
            assert embedded.recv(1) == b""
            embedded.close()
            old = send_connect(port, 0x02, b"", b"\x00\x0cp199-device", level=4)
            assert old.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 CONNACK"
            old.close()
            valid, present = connect(port, True, 0, b"p199-valid")
            assert not present
            valid.sendall(b"\xe0\x00")
            valid.close()
            expect_silence(watcher, 0.3)
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P199_CONNECT_STRUCTURE_PASS CONNACK, limits, session/Will, MQTT 3.1.1")


if __name__ == "__main__":
    main()
