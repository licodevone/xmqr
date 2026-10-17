#!/usr/bin/env python3
"""Exercise MQTT 5 PUBREL/PUBCOMP 0x92 and subsequent durable QoS 2 traffic."""
import socket
import tempfile

from verify_mqtt5_negative_pubrec import accept, receive, subscribe
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop


TOPIC = b"negative/qos2"
DIAGNOSTICS = b"\x1f\x00\x02no\x26\x00\x01k\x00\x01v"


def publisher(port):
    stream, present = connect(port, True, 0, identity=b"completion-publisher")
    assert not present
    return stream


def publish(stream, payload, packet_id, reason):
    identifier = packet_id.to_bytes(2, "big")
    body = len(TOPIC).to_bytes(2, "big") + TOPIC + identifier + b"\x00" + payload
    stream.sendall(bytes([0x34, len(body)]) + body)
    assert packet(stream) == (0x50, identifier)
    ack = identifier + bytes([reason, len(DIAGNOSTICS)]) + DIAGNOSTICS
    stream.sendall(bytes([0x62, len(ack)]) + ack)
    assert packet(stream) == (0x70, identifier)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-completion-reasons-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            subscriber, present = connect(port, True, 60, identity=b"completion-subscriber")
            assert not present
            subscribe(subscriber)
            sending = publisher(port)
            publish(sending, b"reason-92", 1, 0x92)
            first_id = receive(subscriber, b"reason-92")
            identifier = first_id.to_bytes(2, "big")
            subscriber.sendall(b"\x50\x02" + identifier)
            assert packet(subscriber) == (0x62, identifier)
            ack = identifier + b"\x92" + bytes([len(DIAGNOSTICS)]) + DIAGNOSTICS
            subscriber.sendall(bytes([0x70, len(ack)]) + ack)
            subscriber.sendall(b"\xc0\x00")
            assert packet(subscriber) == (0xd0, b"")

            publish(sending, b"next", 2, 0)
            second_id = receive(subscriber, b"next")
            accept(subscriber, second_id)
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()
            sending.close()
            stop(broker)

            broker = start(port, state)
            resumed, present = connect(port, False, 60, identity=b"completion-subscriber")
            assert present
            resumed.settimeout(0.7)
            try:
                replay = packet(resumed)
            except socket.timeout:
                pass
            else:
                raise AssertionError(f"completed delivery replayed: {replay}")
            resumed.settimeout(4)
            sending = publisher(port)
            publish(sending, b"after-restart", 3, 0)
            third_id = receive(resumed, b"after-restart")
            accept(resumed, third_id)
            resumed.sendall(b"\xe0\x00")
            resumed.close()
            sending.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P171_QOS2_COMPLETION_PASS PUBREL/PUBCOMP 0x92, next delivery, restart")


if __name__ == "__main__":
    main()
