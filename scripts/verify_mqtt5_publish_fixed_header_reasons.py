#!/usr/bin/env python3
"""P190: malformed PUBLISH flags report the right MQTT 5 reason without publishing."""

import socket
import tempfile

from verify_mqtt5_oversize_disconnect import connect_311
from verify_mqtt5_sessions import BROKER, connect, packet, start, stop
from verify_mqtt5_will_delay import connect_will, expect_silence, expect_will, subscribe


TOPIC = b"p190/data"


def send_publish(stream, header, mqtt5=True, payload=b"not-published"):
    body = len(TOPIC).to_bytes(2, "big") + TOPIC
    if mqtt5:
        body += b"\x00"
    body += payload
    assert len(body) < 128
    stream.sendall(bytes([header, len(body)]) + body)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p190-publish-flags-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"p190-watcher")
            subscribe(watcher)
            subscribe(watcher, TOPIC)

            for index, (header, reason) in enumerate(((0x37, 0x81), (0x39, 0x82))):
                will = f"p190-will-{index}".encode()
                source = connect_will(port, f"p190-invalid-{index}".encode(), 0, 0, will)
                send_publish(source, header)
                assert packet(source) == (0xE0, bytes((reason, 0)))
                assert source.recv(1) == b""
                source.close()
                expect_will(watcher, will)
                expect_silence(watcher, 0.2)

                legacy = connect_311(port)
                send_publish(legacy, header, mqtt5=False)
                assert legacy.recv(1) == b"", "MQTT 3.1.1 must not receive MQTT 5 DISCONNECT"
                legacy.close()

            late, _ = connect(port, True, 0, b"p190-late")
            subscribe(late, TOPIC)
            expect_silence(late, 0.25)
            late.sendall(b"\xe0\x00")
            late.close()

            valid, _ = connect(port, True, 0, b"p190-valid")
            send_publish(valid, 0x30, payload=b"valid")
            valid.sendall(b"\xc0\x00")
            assert packet(valid) == (0xD0, b"")
            header, body = packet(watcher)
            assert header & 0xF0 == 0x30 and body.endswith(b"valid"), (header, body)
            valid.sendall(b"\xe0\x00")
            valid.close()
            watcher.sendall(b"\xe0\x00")
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P190_PUBLISH_FLAGS_PASS QoS3=0x81, QoS0-DUP=0x82, Will, no fanout/retained, valid, MQTT311")


if __name__ == "__main__":
    main()
