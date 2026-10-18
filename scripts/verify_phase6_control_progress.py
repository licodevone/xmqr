#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite same-peer MQTT5 control progress at Receive Maximum one."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

from verify_phase6_crash_matrix import (
    connect, delivery, field, free_port, publish, send, server, silent, subscribe,
)
from verify_mqtt5_sessions import packet


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def limited_subscriber(port):
    stream = socket.create_connection(("127.0.0.1", port), timeout=5)
    stream.settimeout(5)
    properties = b"\x21\x00\x01"
    send(stream, 0x10, b"\x00\x04MQTT\x05\x02\x00\x1e"
         + bytes([len(properties)]) + properties + field(b"p227f-receiver"))
    header, reply = packet(stream)
    assert header == 0x20 and reply[1] == 0, "CONNECT refused"
    return stream


def acknowledged_publish(stream, qos, payload, identifier):
    publish(stream, b"p227f/data", payload, qos, identifier)
    if qos == 2:
        send(stream, 0x62, identifier.to_bytes(2, "big"))
        header, ack = packet(stream)
        assert header == 0x70 and ack[:2] == identifier.to_bytes(2, "big")


def scenario(binary, state, qos):
    port = free_port()
    with server(binary, state, port):
        receiver = limited_subscriber(port)
        source, _ = connect(port, b"p227f-source", clean=True)
        try:
            subscribe(receiver, b"p227f/data", qos)
            acknowledged_publish(source, qos, b"first", 1)
            first, _ = delivery(receiver, b"p227f/data", b"first", qos)
            if qos == 2:
                send(receiver, 0x50, first.to_bytes(2, "big"))
                assert packet(receiver) == (0x62, first.to_bytes(2, "big"))
            acknowledged_publish(source, qos, b"second", 2)
            silent(receiver, .1)
            send(receiver, 0xc0, b"")
            assert packet(receiver) == (0xd0, b""), "PINGRESP blocked by send quota"
            subscribe(receiver, b"p227f/temporary", 0)
            send(receiver, 0xa2, b"\x00\x02\x00" + field(b"p227f/temporary"))
            assert packet(receiver) == (0xb0, b"\x00\x02\x00\x00"), "UNSUBACK blocked"
            publish(source, b"p227f/data", b"zero", 0, 0)
            delivery(receiver, b"p227f/data", b"zero", 0)
            silent(receiver, .1)
            send(receiver, 0x40 if qos == 1 else 0x70, first.to_bytes(2, "big"))
            second, _ = delivery(receiver, b"p227f/data", b"second", qos)
            if qos == 2:
                send(receiver, 0x50, second.to_bytes(2, "big"))
                assert packet(receiver) == (0x62, second.to_bytes(2, "big"))
            send(receiver, 0x40 if qos == 1 else 0x70, second.to_bytes(2, "big"))
            send(receiver, 0xc0, b"")
            assert packet(receiver) == (0xd0, b"")
            silent(receiver, .1)
        finally:
            source.close()
            receiver.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if os.name != "posix" or sys.flags.optimize or args.report.exists():
        parser.error("Linux/WSL assertions and a new report are required")
    binary = args.broker.resolve(strict=True)
    report = {"broker_sha256": digest(binary),
              "broker_version": subprocess.check_output([binary, "--version"], text=True).strip(),
              "harness_sha256": digest(Path(__file__)),
              "helpers_sha256": {name: digest(Path(__file__).with_name(name)) for name in
                                 ("verify_phase6_crash_matrix.py", "verify_mqtt5_sessions.py")},
              "scenarios": []}
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="xmqr-p227f-", dir="/var/tmp") as directory:
        for qos in (1, 2):
            start = time.monotonic()
            try:
                scenario(binary, Path(directory) / str(qos), qos)
                result = {"qos": qos, "status": "PASS", "cleanup": "PASS"}
            except (AssertionError, OSError, subprocess.SubprocessError) as error:
                result = {"qos": qos, "status": "FAIL", "error_type": type(error).__name__}
            result["elapsed_seconds"] = round(time.monotonic() - start, 3)
            report["scenarios"].append(result)
    report["binary_unchanged"] = digest(binary) == report["broker_sha256"]
    report["status"] = "PASS" if report["binary_unchanged"] and all(
        row["status"] == "PASS" for row in report["scenarios"]) else "FAIL"
    report["elapsed_seconds"] = round(time.monotonic() - began, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("P227_CONTROL_PROGRESS_" + report["status"], flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
