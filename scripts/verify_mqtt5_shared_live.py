#!/usr/bin/env python3
"""P153/C89: live shared MQTT 5 routing against an isolated broker."""
import select
import subprocess
import tempfile
import time
from pathlib import Path

from verify_mqtt5_sessions import packet, start, stop
from verify_mqtt5_subscribe_options import connect, free_port


CLIENT = Path(__file__).resolve().parents[2] / "xmqr-client/target/release/mqtt-client"
TOPIC = b"p153/value"
SHARED = b"$share/workers/p153/value"
OTHER = b"$share/other/p153/value"


def subscribe(stream, topic, qos=0, identifier=0, packet_id=1):
    properties = b"\x0b" + bytes([identifier]) if identifier else b""
    body = (packet_id.to_bytes(2, "big") + bytes([len(properties)]) + properties
            + len(topic).to_bytes(2, "big") + topic + bytes([qos]))
    stream.sendall(bytes([0x82, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x90 and ack[-1] == qos, (header, ack)


def publish(stream, payload, qos=0, packet_id=1, retain=False):
    body = len(TOPIC).to_bytes(2, "big") + TOPIC
    if qos:
        body += packet_id.to_bytes(2, "big")
    body += b"\x00" + payload
    stream.sendall(bytes([0x30 | (qos << 1) | int(retain), len(body)]) + body)
    if qos:
        header, ack = packet(stream)
        assert header == (0x40 if qos == 1 else 0x50) and ack[:2] == packet_id.to_bytes(2, "big"), (header, ack)
        if qos == 2:
            stream.sendall(b"\x62\x04" + packet_id.to_bytes(2, "big") + b"\x00\x00")
            header, ack = packet(stream)
            assert header == 0x70 and ack[:2] == packet_id.to_bytes(2, "big"), (header, ack)


def receive(stream, payload, qos, identifier):
    header, body = packet(stream)
    assert header >> 4 == 3 and (header >> 1) & 3 == qos, (header, body)
    topic_len = int.from_bytes(body[:2], "big")
    assert body[2:2 + topic_len] == TOPIC
    cursor = 2 + topic_len
    packet_id = b""
    if qos:
        packet_id = body[cursor:cursor + 2]
        cursor += 2
    property_len = body[cursor]
    cursor += 1
    assert body[cursor:cursor + property_len] == b"\x0b" + bytes([identifier])
    cursor += property_len
    assert body[cursor:] == payload, body
    if qos == 1:
        stream.sendall(b"\x40\x04" + packet_id + b"\x00\x00")
    elif qos == 2:
        stream.sendall(b"\x50\x04" + packet_id + b"\x00\x00")
        assert packet(stream)[0] == 0x62
        stream.sendall(b"\x70\x04" + packet_id + b"\x00\x00")


def quiet(stream):
    assert not select.select([stream], [], [], 0.2)[0], "unexpected shared copy or initial retained"


def main():
    assert CLIENT.is_file(), "build Linux client C89 release binary first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p153-") as state:
        port = free_port()
        broker = start(port, state)
        try:
            with connect(port, b"publisher")[0] as publisher:
                publish(publisher, b"retained", retain=True)
                first, _ = connect(port, b"worker-one")
                second, _ = connect(port, b"worker-two")
                other, _ = connect(port, b"other-group")
                normal, _ = connect(port, b"normal")
                try:
                    for stream in (first, second):
                        subscribe(stream, SHARED, qos=2, identifier=7)
                        quiet(stream)
                    subscribe(other, OTHER, qos=2, identifier=8)
                    quiet(other)
                    subscribe(normal, TOPIC, qos=2, identifier=9)
                    receive(normal, b"retained", 0, 9)
                    counts = [0, 0]
                    for qos in (0, 1, 2, 0, 1, 2):
                        payload = f"live-{qos}-{sum(counts)}".encode()
                        publish(publisher, payload, qos, sum(counts) + 1)
                        ready, _, _ = select.select([first, second], [], [], 3)
                        assert len(ready) == 1, "expected exactly one worker in shared group"
                        winner = first if ready[0] is first else second
                        counts[0 if winner is first else 1] += 1
                        receive(winner, payload, qos, 7)
                        receive(other, payload, qos, 8)
                        receive(normal, payload, qos, 9)
                        quiet(first if winner is second else second)
                    assert counts == [3, 3], counts
                    body = b"\x00\x30\x00" + len(SHARED).to_bytes(2, "big") + SHARED
                    first.sendall(bytes([0xa2, len(body)]) + body)
                    assert packet(first) == (0xb0, b"\x00\x30\x00\x00")
                    publish(publisher, b"after-unsub")
                    receive(second, b"after-unsub", 0, 7)
                    receive(other, b"after-unsub", 0, 8)
                    receive(normal, b"after-unsub", 0, 9)
                    quiet(first)
                finally:
                    for stream in (first, second, other, normal):
                        stream.close()
                with connect(port, b"durable", persistent=True)[0] as persistent:
                    body = b"\x00\x01\x00" + len(SHARED).to_bytes(2, "big") + SHARED + b"\x01"
                    persistent.sendall(bytes([0x82, len(body)]) + body)
                    assert packet(persistent) == (0x90, b"\x00\x01\x00\x01")
        finally:
            stop(broker)
        broker = start(port, state)
        try:
            resumed, present = connect(port, b"worker-two", clean=False)
            assert not present, "temporary shared session survived restart"
            with resumed:
                with connect(port, b"restart-publisher")[0] as publisher:
                    publish(publisher, b"after-restart")
                quiet(resumed)
            client = subprocess.Popen(
                [str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
                 "--port", str(port), "--topic", SHARED.decode(), "--count", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            try:
                time.sleep(0.4)
                with connect(port, b"client-publisher")[0] as publisher:
                    publish(publisher, b"client-interop")
                output, error = client.communicate(timeout=6)
                assert client.returncode == 0 and b"client-interop" in output, (output, error)
            finally:
                if client.poll() is None:
                    client.kill()
                    client.wait()
        finally:
            stop(broker)
    print("P153_C89_PASS two groups, QoS0/1/2, retained, unsubscribe, restart, client")


if __name__ == "__main__":
    main()
