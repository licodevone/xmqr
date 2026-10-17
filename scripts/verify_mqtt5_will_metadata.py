#!/usr/bin/env python3
"""Exercise MQTT 5 Will metadata from xmqr-client through the durable broker."""
import select
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, connect, packet, start, stop


EXPECTED_PROPERTIES = (
    b"\x01\x01"
    b"\x08\x00\x05reply"
    b"\x09\x00\x02\x00\xaf"
    b"\x26\x00\x01a\x00\x011"
    b"\x26\x00\x01a\x00\x012"
    b"\x03\x00\x04text"
)


def subscribe(stream, topic):
    body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x01"
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00\x01")


def receive(stream, topic, retained=False):
    header, body = packet(stream)
    assert header == (0x33 if retained else 0x32), (header, body)
    size = int.from_bytes(body[:2], "big")
    assert body[2:2 + size] == topic, body
    cursor = 2 + size
    packet_id = body[cursor:cursor + 2]
    cursor += 2
    assert body[cursor] == len(EXPECTED_PROPERTIES), body
    assert body[cursor + 1:cursor + 1 + len(EXPECTED_PROPERTIES)] == EXPECTED_PROPERTIES, body
    assert body[cursor + 1 + len(EXPECTED_PROPERTIES):] == b"bye", body
    stream.sendall(b"\x40\x02" + packet_id)


def client_will(port, topic, delay):
    child = subprocess.Popen([
        str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
        "--port", str(port), "--topic", "will/idle", "--client-id", f"source-{delay}", "--output", "jsonl",
        "--will-topic", topic.decode(), "--will-message", "bye",
        "--will-retain", "true", "--will-delay-seconds", str(delay),
        "--will-qos", "1",
        "--session-expiry-seconds", "never", "--will-payload-format", "1",
        "--will-content-type", "text", "--will-response-topic", "reply",
        "--will-correlation-data-hex", "00af",
        "--will-user-property", "a=1", "--will-user-property", "a=2",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        if not select.select([child.stderr], [], [], 5)[0]:
            child.kill()
            child.wait(timeout=4)
            raise AssertionError(f"client SUBACK readiness timeout: {child.stderr.read()!r}")
        ready = child.stderr.readline()
        assert b"Assinatura ativa" in ready, ready
        child.kill()
        child.wait(timeout=4)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=4)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-will-metadata-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            live, _ = connect(port, True, 0, b"meta-live")
            subscribe(live, b"will/meta")
            client_will(port, b"will/meta", 0)
            receive(live, b"will/meta")
            live.close()

            offline, _ = connect(port, True, 0xFFFFFFFF, b"meta-offline")
            subscribe(offline, b"will/meta-delayed")
            offline.sendall(b"\xe0\x00")
            offline.close()
            client_will(port, b"will/meta-delayed", 2)
            time.sleep(0.15)
            stop(broker)
            broker = start(port, state)
            offline, present = connect(port, False, 0xFFFFFFFF, b"meta-offline")
            assert present
            receive(offline, b"will/meta-delayed")
            offline.close()
            retained, _ = connect(port, True, 0, b"meta-retained")
            subscribe(retained, b"will/meta-delayed")
            receive(retained, b"will/meta-delayed", retained=True)
            retained.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("PASS: MQTT 5 Will metadata, client C94, immediate, delayed/restart, offline and retained")


if __name__ == "__main__":
    main()
