#!/usr/bin/env python3
"""P197: malformed inner lengths yield DISCONNECT 0x81 without partial effects."""
import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


TOPIC = b"p197/data"


def frame(header, body):
    assert len(body) < 128
    return bytes([header, len(body)]) + body


def publish(payload):
    return frame(0x30, len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00" + payload)


def expect_rejected(source, wire, watcher, will):
    source.sendall(wire)
    assert packet(source) == (0xE0, b"\x81\x00")
    assert source.recv(1) == b""
    source.close()
    expect_will(watcher, will)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    malformed = (
        ("publish", frame(0x31, len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x02\x26")),
        ("auth", frame(0xF0, b"\x19\x04\x15\x00\x02P")),
        ("disconnect", frame(0xE0, b"\x00\x00\x00")),
        ("puback", frame(0x40, b"\x00\x01\x00\x00\x00")),
        ("pubrel", frame(0x62, b"\x00\x01\x00\x03\x1f\x00")),
        ("pingreq", frame(0xC0, b"\x00")),
        ("variable-int", frame(0x82, b"\x00\x01\xff\xff\xff\xff")),
    )
    with tempfile.TemporaryDirectory(prefix="xmqr-p197-structure-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p197-watcher")
            subscribe(watcher)
            for index, (name, wire) in enumerate(malformed):
                will = f"p197-will-{index}".encode()
                source = connect_will(port, f"p197-{name}".encode(), 0, 0, will)
                expect_rejected(source, wire, watcher, will)

            late, _ = connect(port, True, 0, b"p197-late")
            subscribe(late, TOPIC)
            expect_silence(late, 0.2)  # Truncated retained PUBLISH was never stored.
            late.sendall(b"\xe0\x00")
            late.close()

            filter_wire = len(TOPIC).to_bytes(2, "big") + TOPIC
            malformed_sub = frame(0x82, b"\x00\x01\x00" + filter_wire + b"\x00\x00\x03x")
            source = connect_will(port, b"p197-partial-sub", 0, 0xffffffff, b"partial-sub")
            expect_rejected(source, malformed_sub, watcher, b"partial-sub")
            resumed, present = connect(port, False, 0xffffffff, b"p197-partial-sub")
            assert present
            sender, _ = connect(port, True, 0, b"p197-sender")
            sender.sendall(publish(b"not-delivered"))
            expect_silence(resumed, 0.2)  # First filter was not committed.
            resumed.sendall(b"\xe0\x00")
            resumed.close()

            source = connect_will(port, b"p197-partial-unsub", 0, 0xffffffff, b"partial-unsub")
            subscribe(source, TOPIC)
            malformed_unsub = frame(0xA2, b"\x00\x02\x00" + filter_wire + b"\x00\x03x")
            expect_rejected(source, malformed_unsub, watcher, b"partial-unsub")
            resumed, present = connect(port, False, 0xffffffff, b"p197-partial-unsub")
            assert present
            sender.sendall(publish(b"still-subscribed"))
            assert packet(resumed)[1].endswith(b"still-subscribed")
            resumed.sendall(b"\xe0\x00")
            resumed.close()

            legacy = connect_311(port)
            legacy.sendall(frame(0x30, b"\x00\x02x"))
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
            legacy.close()

            sender.sendall(b"\xc0\x00")
            assert packet(sender) == (0xD0, b"")
            sender.sendall(b"\xe0\x00")
            sender.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P197_STRUCTURE_PASS 0x81, Will, no partial state, MQTT311, valid PING")


if __name__ == "__main__":
    main()
