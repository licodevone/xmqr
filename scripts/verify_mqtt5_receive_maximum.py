#!/usr/bin/env python3
"""MQTT 5 Receive Maximum on real TCP, including replay after restart."""
import select
import json
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, packet, start, stop


def connect(port, identity, maximum, clean=True):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    props = b"\x11\xff\xff\xff\xff\x21" + maximum.to_bytes(2, "big")
    body = (b"\x00\x04MQTT\x05" + bytes([2 if clean else 0]) + b"\x00\x1e"
            + bytes([len(props)]) + props
            + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == 0, (header, ack)
    return stream, bool(ack[0] & 1)


def subscribe(stream, topic=b"receive/check"):
    body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x01"
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00\x01")


def publish(stream, payload, packet_id, qos=1, topic=b"receive/check"):
    body = (len(topic).to_bytes(2, "big") + topic
            + (packet_id.to_bytes(2, "big") if qos else b"") + b"\x00" + payload)
    stream.sendall(bytes([0x32 if qos else 0x30, len(body)]) + body)
    if qos:
        assert packet(stream) == (0x40, packet_id.to_bytes(2, "big"))


def receive(stream, expected, qos=1):
    header, body = packet(stream)
    assert header & 0x06 == qos << 1, (header, body)
    topic_size = int.from_bytes(body[:2], "big")
    cursor = 2 + topic_size
    packet_id = None
    if qos:
        packet_id = body[cursor:cursor + 2]
        cursor += 2
    assert body[cursor] == 0 and body[cursor + 1:] == expected, body
    return packet_id


def silence(stream):
    stream.settimeout(0.3)
    try:
        packet(stream)
        raise AssertionError("broker exceeded Receive Maximum")
    except socket.timeout:
        pass
    finally:
        stream.settimeout(4)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-receive-max-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            subscriber, _ = connect(port, b"receive-one", 1)
            subscribe(subscriber)
            publisher, _ = connect(port, b"receive-publisher", 2)
            publish(publisher, b"first", 1)
            first = receive(subscriber, b"first")
            publish(publisher, b"second", 2)
            silence(subscriber)
            publish(publisher, b"qos-zero", 0, qos=0)
            receive(subscriber, b"qos-zero", qos=0)
            subscriber.sendall(b"\x40\x02" + first)
            second = receive(subscriber, b"second")
            subscriber.sendall(b"\x40\x02" + second)
            subscriber.sendall(b"\xe0\x00")
            subscriber.close()

            replay, _ = connect(port, b"receive-replay", 2)
            subscribe(replay)
            publish(publisher, b"replay-one", 3)
            publish(publisher, b"replay-two", 4)
            receive(replay, b"replay-one")
            receive(replay, b"replay-two")
            replay.close()
            publisher.close()
            stop(broker)
            broker = start(port, state)
            replay, present = connect(port, b"receive-replay", 1, clean=False)
            assert present
            first = receive(replay, b"replay-one")
            silence(replay)
            replay.sendall(b"\x40\x02" + first)
            second = receive(replay, b"replay-two")
            replay.sendall(b"\x40\x02" + second)
            replay.sendall(b"\xe0\x00")
            replay.close()

            client = subprocess.Popen([
                CLIENT, "sub", "--open-lab", "--protocol-version", "5",
                "--receive-maximum", "1", "--port", str(port), "--topic", "receive/check",
                "--client-id", "receive-client", "--count", "1", "--output", "jsonl",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                assert select.select([client.stderr], [], [], 5)[0]
                assert b"Assinatura ativa" in client.stderr.readline()
                publisher, _ = connect(port, b"receive-publisher-2", 2)
                publish(publisher, b"client-one", 5)
                publisher.close()
                out, err = client.communicate(timeout=7)
                assert client.returncode == 0 and json.loads(out)["payload_bytes"] == list(b"client-one"), (out, err)
            finally:
                if client.poll() is None:
                    client.kill()
                    client.wait(timeout=4)

            external = subprocess.Popen([
                "mosquitto_sub", "-d", "-V", "mqttv5", "-i", "receive-external",
                "-h", "127.0.0.1", "-p", str(port), "-t", "receive/check",
                "-C", "1", "-D", "connect", "receive-maximum", "1",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(0.5)
                assert external.poll() is None, external.stderr.read()
                publisher, _ = connect(port, b"receive-publisher-3", 2)
                publish(publisher, b"mosquitto-one", 6)
                publisher.close()
                out, err = external.communicate(timeout=7)
                assert external.returncode == 0 and b"mosquitto-one" in out, (out, err)
            finally:
                if external.poll() is None:
                    external.kill()
                    external.wait(timeout=4)
        finally:
            stop(broker)
    print("PASS: MQTT 5 Receive Maximum quota, QoS0, replay after restart, client C72 and Mosquitto")


if __name__ == "__main__":
    main()
