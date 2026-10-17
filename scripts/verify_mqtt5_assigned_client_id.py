#!/usr/bin/env python3
"""Exercise server-assigned MQTT 5 Client IDs with the independent CLI."""
import json
import select
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, start, stop


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
        finally:
            if subscriber is not None and subscriber.poll() is None:
                subscriber.kill()
                subscriber.wait(timeout=4)
            if broker.poll() is None:
                stop(broker)
    print("P166_C97_ASSIGNED_ID_PASS unique CONNACK IDs, pub/sub, diagnostics")


if __name__ == "__main__":
    main()
