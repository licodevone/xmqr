#!/usr/bin/env python3
"""Exercise server-assigned MQTT 5 Client IDs with the independent CLI."""
import json
import select
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, packet, start, stop


def await_subscription(process):
    assigned = None
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        assert process.poll() is None, "subscriber stopped before SUBACK"
        ready, _, _ = select.select([process.stderr], [], [], 0.5)
        if not ready:
            continue
        line = process.stderr.readline().decode("utf-8")
        if "Client Identifier atribuido: " in line:
            assigned = line.split("Client Identifier atribuido: ", 1)[1].strip()
        if "Assinatura ativa" in line:
            assert assigned and assigned.startswith("xmqr-"), line
            return assigned
    raise AssertionError("subscriber did not receive assigned ID and SUBACK")


def persistent_assigned_id(port):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    body = b"\x00\x04MQTT\x05\x02\x00\x1e\x05\x11\x00\x00\x00\x3c\x00\x00"
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == 0, (header, ack)
    properties = ack[3:3 + ack[2]]
    at = properties.index(0x12)
    size = int.from_bytes(properties[at + 1:at + 3], "big")
    identity = properties[at + 3:at + 3 + size].decode("ascii")
    assert len(identity) == 37, identity
    stream.sendall(b"\xe0\x00")
    stream.close()
    return identity


def assert_session_present(port, identity):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    encoded_id = identity.encode("ascii")
    body = (b"\x00\x04MQTT\x05\x00\x00\x1e\x05\x11\x00\x00\x00\x3c"
            + len(encoded_id).to_bytes(2, "big") + encoded_id)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[:2] == b"\x01\x00", (header, ack)
    stream.sendall(b"\xe0\x00")
    stream.close()


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-assigned-id-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        subscriber = None
        try:
            subscriber = subprocess.Popen([
                str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
                "--server-assigned-client-id", "--port", str(port),
                "--topic", "assigned/probe", "--count", "1", "--output", "jsonl",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            first_id = await_subscription(subscriber)
            publisher = subprocess.run([
                str(CLIENT), "pub", "--open-lab", "--protocol-version", "5",
                "--server-assigned-client-id", "--port", str(port),
                "--topic", "assigned/probe", "--message", "assigned-probe",
                "--qos", "1",
            ], capture_output=True, timeout=8, check=True)
            diagnostic = publisher.stderr.decode("utf-8")
            assert "Client Identifier atribuido: " in diagnostic, diagnostic
            second_id = diagnostic.split("Client Identifier atribuido: ", 1)[1].splitlines()[0]
            assert first_id != second_id, (first_id, second_id)
            output, errors = subscriber.communicate(timeout=8)
            assert subscriber.returncode == 0, errors
            received = json.loads(output)
            assert received["topic"] == "assigned/probe", received
            assert bytes(received["payload_bytes"]) == b"assigned-probe", received

            reusable = persistent_assigned_id(port)
            assert_session_present(port, reusable)
            resumed = subprocess.Popen([
                str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
                "--client-id", reusable, "--clean-start", "false",
                "--session-expiry-seconds", "60", "--port", str(port),
                "--topic", "assigned/resume", "--count", "1", "--output", "jsonl",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subscriber = resumed
            assert b"Assinatura ativa" in resumed.stderr.readline(), "long ID reconnect failed"
            subprocess.run([
                str(CLIENT), "pub", "--open-lab", "--protocol-version", "5",
                "--port", str(port), "--topic", "assigned/resume",
                "--message", "reused-id",
            ], capture_output=True, timeout=8, check=True)
            output, errors = resumed.communicate(timeout=8)
            assert resumed.returncode == 0, errors
            assert bytes(json.loads(output)["payload_bytes"]) == b"reused-id", output
        finally:
            if subscriber is not None and subscriber.poll() is None:
                subscriber.kill()
                subscriber.wait(timeout=4)
            if broker.poll() is None:
                stop(broker)
    print("P166_C97_C98_ASSIGNED_ID_PASS unique CONNACK IDs, pub/sub, diagnostics, long-ID reconnect")


if __name__ == "__main__":
    main()
