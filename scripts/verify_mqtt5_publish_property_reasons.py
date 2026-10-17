#!/usr/bin/env python3
"""P185: contextual PUBLISH property errors yield MQTT 5 DISCONNECT."""
import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


TOPIC = b"p185/data"


def publish(stream, properties, payload, qos=0, mqtt5=True):
    body = len(TOPIC).to_bytes(2, "big") + TOPIC
    if qos:
        body += b"\x00\x01"
    if mqtt5:
        body += bytes([len(properties)]) + properties
    body += payload
    assert len(body) < 128
    stream.sendall(bytes([0x30 | (qos << 1), len(body)]) + body)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p185-publish-property-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p185-watcher")
            subscribe(watcher)
            subscribe(watcher, TOPIC)
            cases = (
                (b"\x21\x00\x01", 0x81, 0),
                (b"\x02\x00\x00\x00\x01\x02\x00\x00\x00\x02", 0x82, 1),
                (b"\x01\x02", 0x82, 0),
            )
            for index, (properties, reason, qos) in enumerate(cases):
                will = f"p185-will-{index}".encode()
                source = connect_will(port, f"p185-source-{index}".encode(), 0, 0, will)
                publish(source, properties, b"rejected", qos)
                assert packet(source) == (0xe0, bytes([reason, 0]))
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, will)
                expect_silence(watcher, 0.2)

            valid, _ = connect(port, True, 0, b"p185-valid")
            publish(valid, b"\x26\x00\x01k\x00\x01v", b"accepted", 1)
            ack = packet(valid)
            assert ack == (0x40, b"\x00\x01"), ack
            header, body = packet(watcher)
            assert header == 0x30 and body.endswith(b"accepted"), (header, body)
            valid.sendall(b"\xe0\x00")
            valid.close()

            legacy = connect_311(port)
            publish(legacy, b"", b"\x21legacy", mqtt5=False)
            header, body = packet(watcher)
            assert header == 0x30 and body.endswith(b"\x21legacy"), (header, body)
            legacy.sendall(b"\xe0\x00")
            legacy.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P185_PUBLISH_PROPERTY_REASONS_PASS context, duplicate, PFI, Will, no delivery, MQTT311")


if __name__ == "__main__":
    main()
