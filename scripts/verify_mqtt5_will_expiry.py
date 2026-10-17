#!/usr/bin/env python3
"""Check that MQTT 5 Will expiry begins at publication, including restart."""
import select
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, connect, packet, start, stop
from verify_mqtt5_will_metadata import EXPECTED_PROPERTIES, subscribe


def source(port, topic, delay, expiry, identity):
    child = subprocess.Popen([
        str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
        "--port", str(port), "--topic", "will/idle", "--client-id", identity,
        "--output", "jsonl", "--session-expiry-seconds", "never",
        "--will-topic", topic.decode(), "--will-message", "bye", "--will-qos", "1",
        "--will-retain", "true", "--will-delay-seconds", str(delay),
        "--will-message-expiry-seconds", str(expiry),
        "--will-payload-format", "1", "--will-content-type", "text",
        "--will-response-topic", "reply", "--will-correlation-data-hex", "00af",
        "--will-user-property", "a=1", "--will-user-property", "a=2",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        assert select.select([child.stderr], [], [], 5)[0], "client SUBACK readiness timeout"
        ready = child.stderr.readline()
        assert b"Assinatura ativa" in ready, ready
        child.kill()
        child.wait(timeout=4)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=4)


def receive(stream, topic, retained=False):
    header, body = packet(stream)
    assert header == (0x33 if retained else 0x32), (header, body)
    size = int.from_bytes(body[:2], "big")
    assert body[2:2 + size] == topic, body
    packet_id = body[2 + size:4 + size]
    cursor = 4 + size
    property_size = body[cursor]
    properties = body[cursor + 1:cursor + 1 + property_size]
    assert properties[:3] == b"\x01\x01\x02", properties
    remaining = int.from_bytes(properties[3:7], "big")
    assert 1 <= remaining <= 2, remaining
    assert properties[7:] == EXPECTED_PROPERTIES[2:], properties
    assert body[cursor + 1 + property_size:] == b"bye", body
    stream.sendall(b"\x40\x02" + packet_id)


def silence(stream, seconds):
    stream.settimeout(seconds)
    try:
        packet(stream)
        raise AssertionError("unexpected Will before delay or after expiry")
    except socket.timeout:
        pass
    finally:
        stream.settimeout(4)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-will-expiry-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            offline, _ = connect(port, True, 0xFFFFFFFF, b"expiry-offline")
            subscribe(offline, b"will/expiry")
            offline.sendall(b"\xe0\x00")
            offline.close()

            source(port, b"will/expiry", 3, 2, "expiry-source")
            time.sleep(0.1)
            stop(broker)
            broker = start(port, state)
            live, _ = connect(port, True, 0, b"expiry-live")
            subscribe(live, b"will/expiry")
            silence(live, 0.5)
            receive(live, b"will/expiry")
            live.close()

            offline, present = connect(port, False, 0xFFFFFFFF, b"expiry-offline")
            assert present
            receive(offline, b"will/expiry")
            offline.close()
            retained, _ = connect(port, True, 0, b"expiry-retained")
            subscribe(retained, b"will/expiry")
            receive(retained, b"will/expiry", retained=True)
            retained.close()
            time.sleep(2.2)
            expired, _ = connect(port, True, 0, b"expiry-gone")
            subscribe(expired, b"will/expiry")
            silence(expired, 0.4)
            expired.close()

            zero, _ = connect(port, True, 0, b"expiry-zero-watch")
            subscribe(zero, b"will/zero")
            source(port, b"will/zero", 0, 0, "expiry-zero-source")
            silence(zero, 0.4)
            zero.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("PASS: MQTT 5 Will expiry starts on publication, delayed/restart, offline/retained expiry and zero")


if __name__ == "__main__":
    main()
