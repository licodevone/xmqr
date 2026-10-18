#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite MQTT5 crash/replay campaign against one explicitly supplied ELF."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import packet


def integer(value):
    result = bytearray()
    while True:
        digit = value % 128
        value //= 128
        result.append(digit | (128 if value else 0))
        if not value:
            return bytes(result)


def field(value):
    return len(value).to_bytes(2, "big") + value


def send(stream, header, body):
    stream.sendall(bytes([header]) + integer(len(body)) + body)


def free_port():
    with socket.socket() as stream:
        stream.bind(("127.0.0.1", 0))
        return stream.getsockname()[1]


@contextmanager
def server(binary, state, port):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("MQTT_")}
    environment.update(MQTT_MODE="open-lab", MQTT_STATE_DIR=str(state),
                       MQTT_BIND=f"127.0.0.1:{port}")
    process = subprocess.Popen([str(binary)], env=environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 8
        while True:
            assert process.poll() is None, "private broker exited during startup"
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.1):
                    break
            except OSError:
                assert time.monotonic() < deadline, "private broker startup timeout"
                time.sleep(.02)
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
            assert process.wait(timeout=16) == 0, "private broker shutdown failed"


def kill(process):
    process.kill()
    assert process.wait(timeout=5) != 0, "SIGKILL unexpectedly reported success"


def connect(port, identity, clean=False, will=False):
    stream = socket.create_connection(("127.0.0.1", port), timeout=5)
    stream.settimeout(5)
    properties = b"\x11\x00\x00\x00\x3c"
    flags = (2 if clean else 0) | (0x24 if will else 0)
    body = b"\x00\x04MQTT\x05" + bytes([flags]) + b"\x00\x1e"
    body += integer(len(properties)) + properties + field(identity)
    if will:
        properties = b"\x18\x00\x00\x00\x02\x02\x00\x00\x00\x01"
        body += integer(len(properties)) + properties
        body += field(b"p227/will") + field(b"will-fixture")
    send(stream, 0x10, body)
    header, reply = packet(stream)
    assert header == 0x20 and reply[1] == 0, "MQTT5 CONNECT refused"
    return stream, bool(reply[0] & 1)


def subscribe(stream, topic, qos):
    send(stream, 0x82, b"\x00\x01\x00" + field(topic) + bytes([qos]))
    header, body = packet(stream)
    assert header == 0x90 and body[-1] == qos, "MQTT5 SUBACK mismatch"


def publish(stream, topic, payload, qos, identifier, *, ttl=None, retain=False):
    properties = b"\x26\x00\x04test\x00\x06phase6"
    if ttl is not None:
        properties += b"\x02" + ttl.to_bytes(4, "big")
    body = field(topic) + (identifier.to_bytes(2, "big") if qos else b"")
    body += integer(len(properties)) + properties + payload
    send(stream, 0x30 | (qos << 1) | int(retain), body)
    if qos:
        header, ack = packet(stream)
        assert header == (0x40 if qos == 1 else 0x50)
        assert ack[:2] == identifier.to_bytes(2, "big")
        assert len(ack) < 3 or ack[2] < 128, "publish was refused"


def delivery(stream, topic, payload, qos, *, dup=None):
    header, body = packet(stream)
    assert header >> 4 == 3 and (header >> 1) & 3 == qos
    if dup is not None:
        assert bool(header & 8) == dup, "replay DUP mismatch"
    size = int.from_bytes(body[:2], "big")
    assert body[2:2 + size] == topic, "replay topic mismatch"
    position = 2 + size
    identifier = int.from_bytes(body[position:position + 2], "big") if qos else 0
    position += 2 if qos else 0
    length = 0
    multiplier = 1
    while True:
        digit = body[position]
        position += 1
        length += (digit & 127) * multiplier
        if not digit & 128:
            break
        multiplier *= 128
    properties = body[position:position + length]
    assert body[position + length:] == payload, "replay payload mismatch"
    return identifier, properties


def silent(stream, seconds=.25):
    stream.settimeout(seconds)
    try:
        observed = stream.recv(1)
    except socket.timeout:
        observed = None
    finally:
        stream.settimeout(5)
    assert observed is None, "unexpected delivery or disconnect"


def qos1_replay(binary, state, port):
    topic = b"p227/qos1"
    with server(binary, state, port) as broker:
        subscriber, present = connect(port, b"p227-qos1", clean=True)
        assert not present
        subscribe(subscriber, topic, 1)
        publisher, _ = connect(port, b"p227-publisher", clean=True)
        publish(publisher, topic, b"qos1-fixture", 1, 7)
        identifier, properties = delivery(subscriber, topic, b"qos1-fixture", 1, dup=False)
        assert b"\x26\x00\x04test\x00\x06phase6" in properties
        kill(broker)
        subscriber.close()
        publisher.close()
    with server(binary, state, port):
        subscriber, present = connect(port, b"p227-qos1")
        with subscriber:
            assert present
            replay, properties = delivery(subscriber, topic, b"qos1-fixture", 1, dup=True)
            assert replay == identifier and b"phase6" in properties
            send(subscriber, 0x40, replay.to_bytes(2, "big"))


def qos2_replay(binary, state, port):
    topic = b"p227/qos2"
    with server(binary, state, port) as broker:
        subscriber, _ = connect(port, b"p227-qos2-sub", clean=True)
        subscribe(subscriber, topic, 2)
        publisher, _ = connect(port, b"p227-qos2-pub", clean=True)
        publish(publisher, topic, b"qos2-fixture", 2, 9)
        silent(subscriber)
        kill(broker)
        subscriber.close()
        publisher.close()
    with server(binary, state, port) as broker:
        subscriber, present = connect(port, b"p227-qos2-sub")
        assert present
        publisher, present = connect(port, b"p227-qos2-pub")
        assert present
        send(publisher, 0x62, b"\x00\x09")
        assert packet(publisher)[0] == 0x70
        identifier, properties = delivery(subscriber, topic, b"qos2-fixture", 2)
        assert b"phase6" in properties
        send(subscriber, 0x50, identifier.to_bytes(2, "big"))
        assert packet(subscriber)[0] == 0x62
        kill(broker)
        subscriber.close()
        publisher.close()
    with server(binary, state, port):
        subscriber, present = connect(port, b"p227-qos2-sub")
        with subscriber:
            assert present
            header, body = packet(subscriber)
            assert header == 0x62 and body[:2] == identifier.to_bytes(2, "big")
            send(subscriber, 0x70, identifier.to_bytes(2, "big"))
            silent(subscriber)


def expiry_crash(binary, state, port):
    topic = b"p227/expired"
    with server(binary, state, port) as broker:
        publisher, _ = connect(port, b"p227-ttl", clean=True)
        publish(publisher, topic, b"expiry-fixture", 1, 11, ttl=1, retain=True)
        kill(broker)
        publisher.close()
    time.sleep(1.2)
    with server(binary, state, port):
        subscriber, _ = connect(port, b"p227-expiry-sub", clean=True)
        with subscriber:
            subscribe(subscriber, topic, 1)
            silent(subscriber)


def will_crash(binary, state, port):
    with server(binary, state, port) as broker:
        source, _ = connect(port, b"p227-will", clean=True, will=True)
        kill(broker)
        source.close()
    with server(binary, state, port):
        subscriber, _ = connect(port, b"p227-will-sub", clean=True)
        with subscriber:
            subscribe(subscriber, b"p227/will", 0)
            silent(subscriber)
            delivery(subscriber, b"p227/will", b"will-fixture", 0)
            silent(subscriber)
        time.sleep(1.2)
        retained, _ = connect(port, b"p227-will-retained", clean=True)
        with retained:
            subscribe(retained, b"p227/will", 0)
            silent(retained)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, choices=range(1, 4), default=3)
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("native Linux/WSL required; no host services are used")
    if args.report.exists():
        parser.error("report already exists; do not overwrite evidence")
    binary = args.broker.resolve(strict=True)
    before = hashlib.sha256(binary.read_bytes()).hexdigest()
    version = subprocess.check_output([str(binary), "--version"], text=True).strip()
    report = {"schema_version": 1, "status": "RUNNING", "broker_version": version,
              "broker_sha256": before, "repetitions": args.repetitions, "scenarios": [],
              "scope": "SIGKILL of private processes; not physical power loss"}
    started = time.monotonic()
    try:
        for repetition in range(1, args.repetitions + 1):
            for exercise in (qos1_replay, qos2_replay, expiry_crash, will_crash):
                row = {"case": exercise.__name__, "repetition": repetition, "status": "RUNNING"}
                report["scenarios"].append(row)
                began = time.monotonic()
                try:
                    with tempfile.TemporaryDirectory(prefix="xmqr-p227-crash-", dir="/var/tmp") as directory:
                        exercise(binary, Path(directory), free_port())
                    row["status"] = "PASS"
                except Exception as error:
                    row.update(status="FAIL", error_type=type(error).__name__)
                    raise
                finally:
                    row["elapsed_seconds"] = round(time.monotonic() - began, 3)
        assert hashlib.sha256(binary.read_bytes()).hexdigest() == before, "binary changed during campaign"
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error_type=type(error).__name__)
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print("P227_CRASH_MATRIX_" + report["status"])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
