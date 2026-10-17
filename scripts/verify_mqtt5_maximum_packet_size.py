#!/usr/bin/env python3
"""MQTT 5 Maximum Packet Size on a temporary local broker."""
import json
import select
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, packet, start, stop


TOPIC = b"size/check"


def connect(port, identity, maximum, clean=True):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    properties = b"\x11\xff\xff\xff\xff\x27" + maximum.to_bytes(4, "big") + b"\x21\x00\x01"
    body = (b"\x00\x04MQTT\x05" + bytes([2 if clean else 0]) + b"\x00\x1e"
            + bytes([len(properties)]) + properties
            + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20, (header, ack)
    if maximum < 7:
        assert ack == b"\x00\x95\x00", ack
        return stream
    assert ack[1] == 0 and b"\x2a\x00" in ack, ack
    assert len(ack) == (16 if maximum >= 18 else 13 if maximum >= 15 else 10 if maximum >= 12 else 8 if maximum >= 10 else 5), ack
    return stream


def subscribe(stream):
    body = b"\x00\x01\x00" + len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x01"
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00\x01")


def publish(stream, payload, packet_id, qos=1, retain=False):
    body = (len(TOPIC).to_bytes(2, "big") + TOPIC
            + (packet_id.to_bytes(2, "big") if qos else b"") + b"\x00" + payload)
    stream.sendall(bytes([0x30 | (qos << 1) | retain, len(body)]) + body)
    if qos:
        assert packet(stream) == (0x40 if qos == 1 else 0x50, packet_id.to_bytes(2, "big"))
        if qos == 2:
            stream.sendall(b"\x62\x02" + packet_id.to_bytes(2, "big"))
            assert packet(stream) == (0x70, packet_id.to_bytes(2, "big"))


def receive(stream, expected):
    header, body = packet(stream)
    assert header >> 4 == 3, (header, body)
    topic_size = int.from_bytes(body[:2], "big")
    position = 2 + topic_size
    packet_id = body[position:position + 2]
    assert body[position + 2] == 0 and body[position + 3:] == expected, body
    stream.sendall(b"\x40\x02" + packet_id)


def silence(stream):
    stream.settimeout(0.3)
    try:
        packet(stream)
        raise AssertionError("broker sent an oversized packet")
    except socket.timeout:
        pass
    finally:
        stream.settimeout(4)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-packet-max-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            for maximum in (5, 6):
                short = connect(port, b"small-connack", maximum)
                assert short.recv(1) == b"", "connection accepted without shared capability announcement"
                short.close()
            for maximum in (7, 12, 15, 18):
                accepted = connect(port, f"connack-{maximum}".encode(), maximum)
                accepted.close()

            subscriber = connect(port, b"packet-subscriber", 32)
            subscribe(subscriber)
            publisher = connect(port, b"packet-publisher", 65_536)
            publish(publisher, b"X" * 40, 1)
            silence(subscriber)
            publish(publisher, b"small", 2)
            receive(subscriber, b"small")
            publish(publisher, b"Y" * 40, 3, qos=2)
            silence(subscriber)
            publish(publisher, b"after", 4)
            receive(subscriber, b"after")
            publish(publisher, b"A" * 15, 13)
            receive(subscriber, b"A" * 15)  # 32 bytes in the complete PUBLISH.
            publish(publisher, b"B" * 16, 14)
            silence(subscriber)  # 33 bytes must be discarded.
            subscriber.close()

            publish(publisher, b"R" * 40, 7, retain=True)
            retained = connect(port, b"packet-retained", 32)
            subscribe(retained)
            silence(retained)
            publish(publisher, b"retained-small", 8)
            receive(retained, b"retained-small")
            retained.close()

            client = subprocess.Popen([
                CLIENT, "sub", "--open-lab", "--protocol-version", "5",
                "--maximum-packet-size", "32", "--port", str(port),
                "--topic", TOPIC.decode(), "--client-id", "size-client",
                "--count", "1", "--output", "jsonl",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                assert select.select([client.stderr], [], [], 5)[0]
                assert b"Assinatura ativa" in client.stderr.readline()
                publish(publisher, b"Z" * 40, 5)
                publish(publisher, b"client", 6)
                out, err = client.communicate(timeout=7)
                assert client.returncode == 0 and json.loads(out)["payload_bytes"] == list(b"client"), (out, err)
            finally:
                if client.poll() is None:
                    client.kill()
                    client.wait(timeout=4)

            external = subprocess.Popen([
                "mosquitto_sub", "-d", "-V", "mqttv5", "-i", "size-external",
                "-h", "127.0.0.1", "-p", str(port), "-t", TOPIC.decode(),
                "-C", "1", "-D", "connect", "maximum-packet-size", "32",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(0.4)
                assert external.poll() is None, external.stderr.read()
                publish(publisher, b"M" * 40, 9)
                publish(publisher, b"external", 10)
                out, err = external.communicate(timeout=7)
                assert external.returncode == 0 and b"\nexternal\n" in out, (out, err)
            finally:
                if external.poll() is None:
                    external.kill()
                    external.wait(timeout=4)
            replay = connect(port, b"packet-replay", 32)
            subscribe(replay)
            silence(replay)  # The oversized retained publication is discarded.
            replay.close()
            time.sleep(0.2)
            publish(publisher, b"Q" * 40, 11)
            publish(publisher, b"replay", 12)
            publisher.close()
            stop(broker)
            broker = start(port, state)
            replay = connect(port, b"packet-replay", 32, clean=False)
            receive(replay, b"replay")
            replay.close()
        finally:
            stop(broker)
    print("PASS: MQTT 5 Maximum Packet Size, discard, QoS1/2, retained/restart, small CONNACK, C73 and Mosquitto")


if __name__ == "__main__":
    main()
