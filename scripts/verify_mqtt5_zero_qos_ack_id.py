#!/usr/bin/env python3
"""P188: zero Packet Identifier in QoS ACKs is a MQTT 5 Protocol Error."""

import socket
import tempfile

from verify_mqtt5_negative_puback import publish, publisher, receive, subscribe as subscribe_data
from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_will, subscribe as subscribe_will


def send_zero_ack(stream, header):
    stream.sendall(bytes([header, 2, 0, 0]))


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p188-zero-ack-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p188-watcher")
            subscribe_will(watcher)
            for header in (0x40, 0x50, 0x62, 0x70):
                will = f"p188-{header:02x}".encode()
                source = connect_will(port, will, 0, 0, will)
                send_zero_ack(source, header)
                assert packet(source) == (0xE0, b"\x82\x00"), f"ACK {header:#x}"
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, will)

            durable = connect_will(port, b"p188-durable", 0, 60, b"p188-durable-will")
            subscribe_data(durable)
            sending = publisher(port)
            publish(sending, b"pending", 1)
            packet_id = receive(durable, b"pending")
            assert packet_id != 0
            send_zero_ack(durable, 0x40)
            assert packet(durable) == (0xE0, b"\x82\x00")
            assert durable.recv(1) == b""
            durable.close()
            expect_will(watcher, b"p188-durable-will")
            resumed, present = connect(port, False, 60, b"p188-durable")
            assert present
            replay_id = receive(resumed, b"pending")
            assert replay_id == packet_id
            resumed.sendall(b"\x40\x02" + replay_id.to_bytes(2, "big"))
            resumed.sendall(b"\xe0\x00")
            resumed.close()
            sending.sendall(b"\xe0\x00")
            sending.close()

            legacy = connect_311(port)
            send_zero_ack(legacy, 0x40)
            assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
            legacy.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P188_ZERO_QOS_ACK_ID_PASS four ACKs, Will, durable replay, MQTT311")


if __name__ == "__main__":
    main()
