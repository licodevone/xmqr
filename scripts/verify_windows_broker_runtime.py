#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native loopback MQTT recovery proof; operates only on its own child broker/state.

Run from a Windows console for graceful CTRL_BREAK shutdown. Forced termination
is used only in the explicitly recorded process-crash recovery scenario.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time


def field(data):
    return len(data).to_bytes(2, "big") + data


def send(stream, header, body):
    length = len(body)
    encoded = bytearray()
    while True:
        digit = length % 128
        length //= 128
        encoded.append(digit | (128 if length else 0))
        if not length:
            break
    stream.sendall(bytes([header]) + encoded + body)


def receive(stream):
    def exact(count):
        data = bytearray()
        while len(data) < count:
            part = stream.recv(count - len(data))
            if not part:
                raise RuntimeError("Broker closed before completing MQTT packet")
            data.extend(part)
        return bytes(data)
    header = exact(1)[0]
    size = 0
    for index in range(4):
        digit = exact(1)[0]
        size += (digit & 127) << (7 * index)
        if not digit & 128:
            if size > 1024 * 1024:
                raise RuntimeError("Unexpectedly large proof packet")
            return header, exact(size)
    raise RuntimeError("Malformed MQTT remaining length")


def connect(port, identity):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    send(stream, 0x10, field(b"MQTT") + b"\x04\x02\x00\x1e" + field(identity))
    if receive(stream) != (0x20, b"\x00\x00"):
        stream.close()
        raise RuntimeError("MQTT 3.1.1 CONNECT rejected")
    return stream


def publish(port, payload):
    with connect(port, b"p241-publisher") as stream:
        send(stream, 0x33, field(b"p241/retained") + b"\x00\x01" + payload)
        assert receive(stream) == (0x40, b"\x00\x01"), "Durable PUBACK missing"
        send(stream, 0xE0, b"")


def retained(port, payload):
    with connect(port, b"p241-subscriber") as stream:
        send(stream, 0x82, b"\x00\x01" + field(b"p241/retained") + b"\x01")
        assert receive(stream) == (0x90, b"\x00\x01\x01"), "SUBACK mismatch"
        header, body = receive(stream)
        assert header == 0x33, "Expected retained QoS 1 PUBLISH"
        topic_len = int.from_bytes(body[:2], "big")
        assert body[2:2 + topic_len] == b"p241/retained"
        identifier = body[2 + topic_len:4 + topic_len]
        assert body[4 + topic_len:] == payload, "Recovered retained value mismatch"
        send(stream, 0x40, identifier)
        send(stream, 0xE0, b"")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New proof directory")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Requires native Windows")
    binary = args.broker.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    state = output / "state"
    state.mkdir()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = output / "broker.toml"
    config.write_text(
        'version=1\n[broker]\nmode="open-lab"\nbind="127.0.0.1:'
        + str(port) + '"\nstate_dir="state"\n[monitor]\nenabled=false\n', encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("MQTT_")}
    env.update(MQTT_CONFIG=str(config), RUST_LOG="info")
    report = {"schema": 1, "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
              "checks": [], "scm_lifecycle": "NOT_RUN", "power_loss": "NOT_RUN"}
    process = None
    log = None

    def start(cycle):
        nonlocal process, log
        log = (output / f"broker-{cycle}.log").open("wb")
        process = subprocess.Popen([str(binary)], env=env, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Broker exited at startup ({process.returncode}); inspect broker-{cycle}.log")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    return
            except OSError:
                time.sleep(.05)
        raise RuntimeError("Loopback broker startup timed out")

    def stop(graceful):
        if graceful:
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.kill()  # Only the child owned by this proof, for crash recovery.
        code = process.wait(timeout=20)
        log.close()
        if graceful:
            assert code == 0, f"Graceful broker exit failed: {code}"
        else:
            assert code != 0, "Crash scenario unexpectedly exited cleanly"

    try:
        start(1)
        publish(port, b"confirmed-before-graceful-stop")
        retained(port, b"confirmed-before-graceful-stop")
        stop(True)
        report["checks"].append("qos1-retained-and-graceful-stop")
        start(2)
        retained(port, b"confirmed-before-graceful-stop")
        report["checks"].append("retained-recovered-after-graceful-restart")
        publish(port, b"confirmed-before-process-crash")
        stop(False)
        start(3)
        retained(port, b"confirmed-before-process-crash")
        report["checks"].append("puback-confirmed-retained-recovered-after-process-crash")
        stop(True)
        report["result"] = "PASS"
    except Exception as error:
        report.update(result="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        if process is not None and process.poll() is None:
            process.kill()  # Bound cleanup of this proof's child on test failure.
            process.wait(timeout=5)
        if log is not None:
            log.close()
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
