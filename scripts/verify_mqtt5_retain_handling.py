#!/usr/bin/env python3
"""P147/C84: retained subscription modes over TCP, optionally with Mosquitto."""
import os
import select
import socket
import subprocess
import tempfile

from verify_mqtt5_connack_receive_maximum import start, stop
from verify_mqtt5_sessions import BROKER, CLIENT, packet


TOPIC = b"p147/retained"


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def connect(port, identity, clean=True, persistent=False):
    stream = socket.create_connection(("127.0.0.1", port), timeout=5)
    stream.settimeout(5)
    properties = b"\x11\xff\xff\xff\xff" if persistent else b""
    body = (b"\x00\x04MQTT\x05" + bytes([2 if clean else 0]) + b"\x00\x1e"
            + bytes([len(properties)]) + properties
            + len(identity).to_bytes(2, "big") + identity)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == 0, ack
    return stream, bool(ack[0] & 1)


def publish(port, payload, retained=False):
    stream, _ = connect(port, b"p147-raw-publisher")
    body = len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00" + payload
    stream.sendall(bytes([0x31 if retained else 0x30, len(body)]) + body)
    stream.sendall(b"\xe0\x00")
    stream.close()


def subscribe(stream, handling, expect_retained):
    body = b"\x00\x01\x00" + len(TOPIC).to_bytes(2, "big") + TOPIC + bytes([handling << 4])
    stream.sendall(bytes([0x82, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x90 and ack[-1] == 0, ack
    if expect_retained:
        header, message = packet(stream)
        assert header == 0x31 and message.endswith(b"\x00snapshot"), (header, message)
    else:
        ready, _, _ = select.select([stream], [], [], 0.25)
        assert not ready, "retained delivery not suppressed"


def raw_contract(port, label):
    publish(port, b"snapshot", retained=True)
    stream, present = connect(port, f"p147-{label}".encode(), persistent=True)
    assert not present
    subscribe(stream, 2, False)
    subscribe(stream, 1, False)
    subscribe(stream, 0, True)
    stream.close()


def client_case(port, handling, expected):
    command = [str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
               "--port", str(port), "--topic", TOPIC.decode(), "--count", "1",
               "--retain-handling", str(handling), "--client-id", f"c84-{port}-{handling}"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if handling == 2:
        ready, _, _ = select.select([process.stdout], [], [], 5)
        assert ready, "C84 SUBACK timeout"
        assert b"Assinatura ativa" in process.stdout.readline()
        publish(port, b"live")
    output, errors = process.communicate(timeout=8)
    assert process.returncode == 0, errors
    assert expected in output and (b"snapshot" not in output if handling == 2 else True), output


def exercise(port, label):
    raw_contract(port, label)
    for handling, expected in [(0, b"snapshot"), (1, b"snapshot"), (2, b"live")]:
        client_case(port, handling, expected)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p147-retain-") as state:
        port = free_port()
        broker = start(port, state, 32)
        try:
            publish(port, b"snapshot", retained=True)
            stream, present = connect(port, b"p147-persistent", persistent=True)
            assert not present
            subscribe(stream, 2, False)
            subscribe(stream, 1, False)
            stream.close()
        finally:
            stop(broker)
        broker = start(port, state, 32)
        try:
            stream, present = connect(port, b"p147-persistent", clean=False, persistent=True)
            assert present
            subscribe(stream, 1, False)
            subscribe(stream, 0, True)
            stream.close()
            exercise(port, "xmqr")
        finally:
            stop(broker)
    external = os.environ.get("P147_MOSQUITTO_PORT")
    if external:
        exercise(int(external), "mosquitto")
    print("PASS: P147/C84 retain handling 0/1/2, persisted session/restart, XMQR"
          + (" and Mosquitto" if external else ""))


if __name__ == "__main__":
    main()
