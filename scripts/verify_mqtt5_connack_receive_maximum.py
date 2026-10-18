#!/usr/bin/env python3
"""P144: inspect CONNACK Receive Maximum and durable quota over real TCP."""
import json
import os
import select
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, packet, stop


def start(port, state, maximum):
    env = dict(os.environ, MQTT_MODE="open-lab", MQTT_STATE_DIR=state,
               MQTT_BIND=f"127.0.0.1:{port}", MQTT_MAX_INFLIGHT=str(maximum))
    process = subprocess.Popen([BROKER], env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    for _ in range(100):
        if process.poll() is not None:
            raise AssertionError("broker exited before listening")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return process
        except OSError:
            time.sleep(0.05)
    raise AssertionError("broker did not listen")


def connect(port, identity, maximum=None, clean=True, persistent=False, expected_reason=0,
            expected_frame_size=None):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    props = b""
    if maximum is not None:
        props += b"\x27" + maximum.to_bytes(4, "big")
    if persistent:
        props += b"\x11\xff\xff\xff\xff"
    body = (b"\x00\x04MQTT\x05" + bytes([2 if clean else 0]) + b"\x00\x1e"
            + bytes([len(props)]) + props + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == expected_reason and ack[2] == len(ack) - 3, ack
    assert maximum is None or len(ack) + 2 <= maximum, ack
    if expected_frame_size is not None:
        assert len(ack) + 2 == expected_frame_size, "CONNACK frame size mismatch"
    if expected_reason:
        assert ack == b"\x00" + bytes([expected_reason]) + b"\x00", ack
        assert stream.recv(1) == b"", "refused CONNECT remained active"
        return stream, {}, False
    found = {}
    position = 3
    while position < len(ack):
        kind = ack[position]
        size = {0x21: 2, 0x22: 2, 0x27: 4, 0x2a: 1}[kind]
        assert kind not in found, ack
        assert position + 1 + size <= len(ack), "truncated CONNACK property"
        found[kind] = int.from_bytes(ack[position + 1:position + 1 + size], "big")
        position += 1 + size
    assert position == len(ack)
    return stream, found, bool(ack[0] & 1)


def subscribe(stream, topic=b"p144/flow"):
    body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x02"
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00\x02")


def publish(stream, qos, identifier, payload, topic=b"p144/flow"):
    body = (len(topic).to_bytes(2, "big") + topic
            + (identifier.to_bytes(2, "big") if qos else b"") + b"\x00" + payload)
    stream.sendall(bytes([0x30 | (qos << 1), len(body)]) + body)
    if qos:
        assert packet(stream) == (0x40 if qos == 1 else 0x50,
                                  identifier.to_bytes(2, "big"))


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p144-flow-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state, 1)
        try:
            for maximum in (5, 6):
                identity = f"p144-denied-{maximum}".encode()
                stream, _, _ = connect(port, identity, maximum, persistent=True, expected_reason=0x95)
                stream.close()
                stream, _, present = connect(port, identity, clean=False, persistent=True)
                assert not present, "refused CONNECT created durable session"
                stream.close()
            shared = {0x2a: 1}
            expected = {7: (7, shared), 8: (7, shared), 9: (7, shared),
                        10: (10, {**shared, 0x21: 1}), 11: (10, {**shared, 0x21: 1}),
                        12: (12, {**shared, 0x27: 65536}),
                        13: (12, {**shared, 0x27: 65536}),
                        14: (12, {**shared, 0x27: 65536}),
                        15: (15, {**shared, 0x27: 65536, 0x22: 16}),
                        16: (15, {**shared, 0x27: 65536, 0x22: 16}),
                        17: (15, {**shared, 0x27: 65536, 0x22: 16}),
                        18: (18, {**shared, 0x27: 65536, 0x22: 16, 0x21: 1})}
            for maximum, (length, properties) in expected.items():
                stream, found, present = connect(port, f"p144-{maximum}".encode(), maximum,
                                                  expected_frame_size=length)
                assert not present and found == properties, found
                stream.close()
            subscriber, props, _ = connect(port, b"p144-sub")
            assert props[0x21] == 1
            subscribe(subscriber)
            publisher, props, _ = connect(port, b"p144-publisher", persistent=True)
            assert props[0x21] == 1
            publish(publisher, 0, 0, b"zero")
            assert packet(subscriber)[1].endswith(b"\x00zero")
            publish(publisher, 1, 1, b"one")
            header, body = packet(subscriber)
            assert header & 0x06 == 2 and body.endswith(b"\x00one"), (header, body)
            topic_length = int.from_bytes(body[:2], "big")
            subscriber.sendall(b"\x40\x02" + body[2 + topic_length:4 + topic_length])
            publish(publisher, 2, 2, b"first")
            # Sending another QoS2 PUBLISH now violates the advertised quota.
            body = b"\x00\x09p144/flow\x00\x03\x00second"
            publisher.sendall(bytes([0x34, len(body)]) + body)
            assert publisher.recv(1) == b"", "quota overflow was accepted"
            publisher.close()
            subscriber.close()
        finally:
            stop(broker)
        broker = start(port, state, 1)
        try:
            client = subprocess.Popen([
                CLIENT, "sub", "--open-lab", "--protocol-version", "5",
                "--port", str(port), "--topic", "p144/flow", "--qos", "2",
                "--count", "1", "--output", "jsonl", "--client-id", "p144-restart-sub",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ready, _, _ = select.select([client.stderr], [], [], 6)
            assert ready and b"Assinatura ativa" in client.stderr.readline()
            publisher, props, present = connect(port, b"p144-publisher", clean=False,
                                                persistent=True)
            assert present and props[0x21] == 1
            publisher.sendall(b"\x62\x02\x00\x02")
            assert packet(publisher) == (0x70, b"\x00\x02")
            output, errors = client.communicate(timeout=8)
            assert client.returncode == 0, errors
            event = json.loads(output)
            assert event["payload_bytes"] == list(b"first") and event["qos"] == 2, event
            publisher.close()
            for command in ([CLIENT, "pub", "--open-lab", "--protocol-version", "5",
                             "--port", str(port), "--topic", "p144/flow", "--message", "client",
                             "--qos", "1"],
                            ["mosquitto_pub", "-V", "mqttv5", "-i", "p144-mosquitto",
                             "-h", "127.0.0.1", "-p", str(port), "-t", "p144/flow",
                             "-m", "external", "-q", "1"]):
                result = subprocess.run(command, capture_output=True, timeout=8)
                assert result.returncode == 0, result.stderr
        finally:
            stop(broker)
        broker = start(port, state, 32)
        try:
            stream, props, _ = connect(port, b"p144-default")
            assert props[0x21] == 32, props
            stream.close()
        finally:
            stop(broker)
    print("PASS: P144 CONNACK Receive Maximum 1/32, packet-size boundaries, QoS0/1/2, overflow/restart, XMQR and Mosquitto")


if __name__ == "__main__":
    main()
