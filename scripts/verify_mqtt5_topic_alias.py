#!/usr/bin/env python3
"""Exercise inbound MQTT 5 Topic Alias over real TCP without persistent setup."""
import socket
import subprocess
import tempfile

from verify_mqtt5_sessions import BROKER, CLIENT, packet, start, stop


def connect(port, identity):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    body = (b"\x00\x04MQTT\x05\x02\x00\x1e\x00"
            + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack == b"\x00\x00\x08\x27\x00\x01\x00\x00\x22\x00\x10", ack
    return stream


def publish(stream, name, alias, payload, qos=0, identifier=0):
    properties = b"\x23" + alias.to_bytes(2, "big")
    body = (len(name).to_bytes(2, "big") + name
            + (identifier.to_bytes(2, "big") if qos else b"")
            + bytes([len(properties)]) + properties + payload)
    stream.sendall(bytes([0x30 | (qos << 1), len(body)]) + body)
    if qos:
        assert packet(stream) == (0x40 if qos == 1 else 0x50,
                                  identifier.to_bytes(2, "big"))
        if qos == 2:
            stream.sendall(b"\x62\x02" + identifier.to_bytes(2, "big"))
            assert packet(stream) == (0x70, identifier.to_bytes(2, "big"))


def receive(stream, expected_topic, expected_payload):
    header, body = packet(stream)
    assert header == 0x30, (header, body)
    size = int.from_bytes(body[:2], "big")
    assert body[2:2 + size] == expected_topic, body
    assert body[2 + size:] == b"\x00" + expected_payload, body


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-topic-alias-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            subscriber = connect(port, b"alias-sub")
            topic = b"alias/#"
            body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x00"
            subscriber.sendall(bytes([0x82, len(body)]) + body)
            assert packet(subscriber) == (0x90, b"\x00\x01\x00\x00")
            publisher = connect(port, b"alias-pub")
            publish(publisher, b"alias/one", 1, b"first")
            receive(subscriber, b"alias/one", b"first")
            publish(publisher, b"", 1, b"second", qos=1, identifier=1)
            receive(subscriber, b"alias/one", b"second")
            publish(publisher, b"", 1, b"third", qos=2, identifier=2)
            receive(subscriber, b"alias/one", b"third")
            publish(publisher, b"alias/two", 1, b"rebind")
            receive(subscriber, b"alias/two", b"rebind")
            publish(publisher, b"", 1, b"after-rebind")
            receive(subscriber, b"alias/two", b"after-rebind")
            publisher.close()

            fresh = connect(port, b"alias-fresh")
            publish(fresh, b"", 1, b"invalid")
            assert fresh.recv(1) == b"", "alias crossed connection boundary"
            fresh.close()

            result = subprocess.run(
                [CLIENT, "pub", "--protocol-version", "5", "--open-lab", "--port", str(port),
                 "--topic", "alias/client", "--message", "client", "--qos", "1"],
                capture_output=True, timeout=8)
            assert result.returncode == 0, result.stderr
            receive(subscriber, b"alias/client", b"client")
            result = subprocess.run(
                ["mosquitto_pub", "-V", "mqttv5", "-i", "alias-external", "-h", "127.0.0.1", "-p", str(port),
                 "-t", "alias/mosquitto", "-m", "external", "-q", "1"],
                capture_output=True, timeout=8)
            assert result.returncode == 0, result.stderr
            receive(subscriber, b"alias/mosquitto", b"external")
            subscriber.close()
        finally:
            stop(broker)
    print("PASS: MQTT 5 inbound Topic Alias QoS0/1/2, rebind, connection reset, client and Mosquitto")


if __name__ == "__main__":
    main()
