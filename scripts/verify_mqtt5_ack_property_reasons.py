#!/usr/bin/env python3
"""P187: MQTT 5 QoS acknowledgment property errors are diagnosed before state changes."""
import socket
import tempfile

from verify_mqtt5_negative_puback import publish, publisher, receive, subscribe as subscribe_data
from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe as subscribe_will


def send_ack(stream, header, packet_id, properties):
    body = packet_id.to_bytes(2, "big") + b"\x00" + bytes([len(properties)]) + properties
    stream.sendall(bytes([header, len(body)]) + body)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p187-ack-property-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p187-watcher")
            subscribe_will(watcher)
            cases = (
                (b"\x11", 0x81),
                (b"\x1f\x00\x01a\x1f\x00\x01b", 0x82),
            )
            for header in (0x40, 0x50, 0x62, 0x70):
                for index, (properties, reason) in enumerate(cases):
                    will = f"p187-{header:02x}-{index}".encode()
                    source = connect_will(port, will, 0, 0, will)
                    send_ack(source, header, 7, properties)
                    assert packet(source) == (0xe0, bytes([reason, 0]))
                    assert source.recv(1) == b""
                    source.close()
                    expect_will(watcher, will)

            durable = connect_will(port, b"p187-durable", 0, 60, b"p187-durable-will")
            subscribe_data(durable)
            sending = publisher(port)
            publish(sending, b"pending", 1)
            packet_id = receive(durable, b"pending")
            send_ack(durable, 0x40, packet_id, b"\x1f\x00\x01a\x1f\x00\x01b")
            assert packet(durable) == (0xe0, b"\x82\x00")
            assert durable.recv(1) == b""
            durable.close()
            expect_will(watcher, b"p187-durable-will")
            resumed, present = connect(port, False, 60, b"p187-durable")
            assert present
            replay_id = receive(resumed, b"pending")
            resumed.sendall(b"\x40\x02" + replay_id.to_bytes(2, "big"))
            resumed.sendall(b"\xe0\x00")
            resumed.close()
            sending.sendall(b"\xe0\x00")
            sending.close()

            legacy = connect_311(port)
            send_ack(legacy, 0x40, 7, b"\x11")
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
            legacy.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P187_ACK_PROPERTY_REASONS_PASS four ACKs, Will, durable replay, MQTT311")


if __name__ == "__main__":
    main()
