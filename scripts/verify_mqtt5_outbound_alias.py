#!/usr/bin/env python3
"""Check broker Topic Alias negotiation and compression on real MQTT 5 TCP."""
import json
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, packet, start, stop


def connect(port, identity, alias_max=0, packet_max=None):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    properties = b"\x22" + alias_max.to_bytes(2, "big")
    if packet_max is not None:
        properties += b"\x27" + packet_max.to_bytes(4, "big")
    body = (b"\x00\x04MQTT\x05\x02\x00\x1e" + bytes([len(properties)])
            + properties + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == 0, (header, ack)
    assert len(ack) + 2 <= (packet_max or 65536), ack
    return stream


def subscribe(stream, topic=b"alias/#", qos=2):
    body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + bytes([qos])
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00" + bytes([qos]))


def publish(stream, topic, payload, qos=0, identifier=0, retain=False):
    body = (len(topic).to_bytes(2, "big") + topic
            + (identifier.to_bytes(2, "big") if qos else b"") + b"\x00" + payload)
    stream.sendall(bytes([0x30 | (qos << 1) | int(retain), len(body)]) + body)
    if qos:
        assert packet(stream) == (0x40 if qos == 1 else 0x50,
                                  identifier.to_bytes(2, "big"))
        if qos == 2:
            stream.sendall(b"\x62\x02" + identifier.to_bytes(2, "big"))
            assert packet(stream) == (0x70, identifier.to_bytes(2, "big"))


def receive(stream, topic, payload, qos, alias=None, shortened=False, retained=False):
    header, body = packet(stream)
    assert header >> 4 == 3 and (header >> 1) & 3 == qos, (header, body)
    assert bool(header & 1) == retained, header
    name_size = int.from_bytes(body[:2], "big")
    assert body[2:2 + name_size] == (b"" if shortened else topic), body
    cursor = 2 + name_size
    identifier = None
    if qos:
        identifier = body[cursor:cursor + 2]
        cursor += 2
    size = body[cursor]
    cursor += 1
    expected = b"" if alias is None else b"\x23" + alias.to_bytes(2, "big")
    assert body[cursor:cursor + size] == expected and body[cursor + size:] == payload, body
    if qos == 1:
        stream.sendall(b"\x40\x02" + identifier)
    elif qos == 2:
        stream.sendall(b"\x50\x02" + identifier)
        assert packet(stream) == (0x62, identifier)
        stream.sendall(b"\x70\x02" + identifier)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-outbound-alias-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            subscriber = connect(port, b"out-alias-sub", alias_max=1)
            subscribe(subscriber)
            publisher = connect(port, b"out-alias-pub")
            publish(publisher, b"alias/one", b"first")
            receive(subscriber, b"alias/one", b"first", 0, alias=1)
            publish(publisher, b"alias/one", b"second", 1, 1)
            receive(subscriber, b"alias/one", b"second", 1, alias=1, shortened=True)
            publish(publisher, b"alias/one", b"third", 2, 2)
            receive(subscriber, b"alias/one", b"third", 2, alias=1, shortened=True)
            publish(publisher, b"alias/two", b"different")
            receive(subscriber, b"alias/two", b"different", 0)
            subscriber.close()

            subscriber = connect(port, b"out-alias-new", alias_max=1)
            subscribe(subscriber)
            publish(publisher, b"alias/one", b"reset")
            receive(subscriber, b"alias/one", b"reset", 0, alias=1)
            subscriber.close()
            subscriber = connect(port, b"out-alias-zero")
            subscribe(subscriber)
            publish(publisher, b"alias/one", b"plain")
            receive(subscriber, b"alias/one", b"plain", 0)
            subscriber.close()

            small = connect(port, b"out-alias-small", alias_max=1, packet_max=9)
            subscribe(small, topic=b"a", qos=0)
            publish(publisher, b"a", b"x")
            receive(small, b"a", b"x", 0)  # Alias would exceed the 9-byte cap.
            publish(publisher, b"a", b"y")
            receive(small, b"a", b"y", 0)
            small.close()

            publish(publisher, b"alias/retained", b"persisted", retain=True)
            retained_sub = connect(port, b"out-alias-retained", alias_max=1)
            subscribe(retained_sub, topic=b"alias/retained", qos=0)
            receive(retained_sub, b"alias/retained", b"persisted", 0,
                    alias=1, retained=True)
            retained_sub.close()

            client = subprocess.Popen([
                str(CLIENT), "sub", "--protocol-version", "5", "--open-lab",
                "--port", str(port), "--topic", "alias/one", "--count", "2",
                "--topic-alias-maximum", "1", "--output", "jsonl",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(0.3)
                assert client.poll() is None
                publish(publisher, b"alias/one", b"client-one")
                publish(publisher, b"alias/one", b"client-two")
                out, err = client.communicate(timeout=7)
                rows = [json.loads(line) for line in out.splitlines()]
                assert client.returncode == 0 and len(rows) == 2, (out, err)
                assert all(row["topic"] == "alias/one" for row in rows), rows
                assert [bytes(row["payload_bytes"]) for row in rows] == [b"client-one", b"client-two"]
            finally:
                if client.poll() is None:
                    client.kill()
                    client.wait(timeout=4)

            external = subprocess.Popen([
                "mosquitto_sub", "-V", "mqttv5", "-i", "alias-mosquitto",
                "-h", "127.0.0.1", "-p", str(port), "-t", "alias/one", "-C", "2",
                "-D", "connect", "topic-alias-maximum", "1",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(0.3)
                assert external.poll() is None
                publish(publisher, b"alias/one", b"external-one")
                publish(publisher, b"alias/one", b"external-two")
                out, err = external.communicate(timeout=7)
                # Mosquitto 2.0.22 also rejects these valid bytes from an
                # isolated fixture; record the limitation, never claim interop.
                assert external.returncode == 2 and out == b"external-one\n", (out, err)
                assert b"network protocol error" in err.lower(), err
            finally:
                if external.poll() is None:
                    external.kill()
                    external.wait(timeout=4)
            publisher.close()
        finally:
            stop(broker)
        broker = start(port, state)
        try:
            restored = connect(port, b"out-alias-restored", alias_max=1)
            subscribe(restored, topic=b"alias/retained", qos=0)
            receive(restored, b"alias/retained", b"persisted", 0,
                    alias=1, retained=True)
            restored.close()
        finally:
            stop(broker)
    print("PASS: outbound MQTT 5 Topic Alias QoS0/1/2, retained/restart, max, reconnect, XMQR client; Mosquitto 2.0.22 limitation reproduced")


if __name__ == "__main__":
    main()
