#!/usr/bin/env python3
"""Run both MQTT 5 directions through the broker and independent client."""
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import tempfile
import time


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def ready(port, process):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("broker exited before opening its listener")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError("broker did not open its listener")


def subscription_ready(process):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("subscriber exited before SUBACK")
        readable, _, _ = select.select([process.stderr], [], [], 0.1)
        if readable and "Assinatura ativa" in process.stderr.readline():
            return
    raise TimeoutError("subscriber did not receive SUBACK")


def main():
    root = Path(__file__).resolve().parents[1]
    broker_binary = root / "target/debug/mqtt-broker"
    client_binary = root.parent / "xmqr-client/target/debug/mqtt-client"
    if not broker_binary.is_file() or not client_binary.is_file():
        raise RuntimeError("build both Linux binaries before running the cross-check")
    with tempfile.TemporaryDirectory(prefix="xmqr-mqtt5-cross-") as state:
        port = free_port()
        env = dict(os.environ, MQTT_MODE="open-lab", MQTT_STATE_DIR=state,
                   MQTT_BIND=f"127.0.0.1:{port}")
        with open(Path(state) / "broker.log", "wb") as log:
            broker = subprocess.Popen([broker_binary], env=env, stdout=log, stderr=log)
            subscriber = None
            try:
                ready(port, broker)
                subscriber = subprocess.Popen(
                    [client_binary, "sub", "--open-lab", "--port", str(port),
                     "--topic", "x", "--count", "2", "--output", "jsonl",
                     "--client-id", "cross-sub"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                subscription_ready(subscriber)
                for qos, message in [(0, "one"), (1, "two")]:
                    result = subprocess.run(
                        [client_binary, "pub", "--open-lab", "--protocol-version", "5",
                         "--port", str(port), "--topic", "x", "--message", message,
                         "--qos", str(qos), "--client-id", f"cross-pub-{qos}"],
                        capture_output=True, text=True, timeout=8)
                    if result.returncode != 0:
                        raise RuntimeError(f"MQTT 5 QoS {qos} publish failed: {result.stderr}")
                output, errors = subscriber.communicate(timeout=8)
                if subscriber.returncode != 0:
                    raise RuntimeError(f"MQTT 3.1.1 subscriber failed: {errors}")
                publications = [json.loads(line) for line in output.splitlines()]
                if [item.get("payload_bytes") for item in publications] != [[111, 110, 101], [116, 119, 111]]:
                    raise AssertionError(f"unexpected cross-protocol deliveries: {publications}")
                print("PASS: MQTT 5 QoS 0/1 -> MQTT 3.1.1 subscriber (two deliveries)")
                retained = subprocess.run(
                    [client_binary, "pub", "--open-lab", "--port", str(port),
                     "--topic", "y", "--message", "retained", "--qos", "1",
                     "--retain", "true", "--client-id", "cross-retained"],
                    capture_output=True, text=True, timeout=8)
                if retained.returncode != 0:
                    raise RuntimeError(f"retained setup failed: {retained.stderr}")
                subscriber = subprocess.Popen(
                    [client_binary, "sub", "--open-lab", "--protocol-version", "5",
                     "--port", str(port), "--topic", "y", "--qos", "1",
                     "--count", "2", "--output", "jsonl", "--client-id", "cross-v5-sub"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                subscription_ready(subscriber)
                live = subprocess.run(
                    [client_binary, "pub", "--open-lab", "--port", str(port),
                     "--topic", "y", "--message", "live", "--qos", "1",
                     "--client-id", "cross-v311-pub"],
                    capture_output=True, text=True, timeout=8)
                if live.returncode != 0:
                    raise RuntimeError(f"live MQTT 3.1.1 publication failed: {live.stderr}")
                output, errors = subscriber.communicate(timeout=8)
                if subscriber.returncode != 0:
                    raise RuntimeError(f"MQTT 5 subscriber failed: {errors}")
                publications = [json.loads(line) for line in output.splitlines()]
                if [bytes(item.get("payload_bytes", [])).decode() for item in publications] != ["retained", "live"]:
                    raise AssertionError(f"unexpected MQTT 5 deliveries: {publications}")
                print("PASS: MQTT 3.1.1 -> MQTT 5 subscriber (retained and live QoS 1)")
            finally:
                if subscriber is not None and subscriber.poll() is None:
                    subscriber.terminate()
                    subscriber.wait(timeout=5)
                broker.terminate()
                broker.wait(timeout=5)


if __name__ == "__main__":
    main()
