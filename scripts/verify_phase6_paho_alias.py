#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Paho MQTT5 wire/property interoperability with an explicit app alias adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
import tempfile
from threading import Event
import time

import paho.mqtt
from paho.mqtt import client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from verify_phase6_crash_matrix import free_port, server


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Peer:
    def __init__(self, port, identity, *, subscriber=False):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=identity,
                                  protocol=mqtt.MQTTv5, reconnect_on_failure=False)
        self.connected = Event()
        self.subscribed = Event()
        self.messages = Queue(maxsize=16)
        self.aliases = {}
        self.failure = None

        def on_connect(_client, _data, _flags, reason, properties):
            if reason.value != 0 or getattr(properties, "TopicAliasMaximum", 0) < 1:
                self.failure = "CONNECT or alias negotiation failed"
            self.connected.set()

        def on_subscribe(_client, _data, _mid, reasons, _properties):
            if len(reasons) != 1 or reasons[0].value != 2:
                self.failure = "SUBACK mismatch"
            self.subscribed.set()

        def on_message(_client, _data, message):
            # Paho decodes the wire and owns QoS ACKs. Its callback exposes raw
            # empty topic/alias metadata; resolution here is application logic.
            try:
                raw_topic = message.topic
                alias = getattr(message.properties, "TopicAlias", None)
                if alias is not None:
                    assert alias == 1
                    if raw_topic:
                        self.aliases[alias] = raw_topic
                    else:
                        assert alias in self.aliases, "alias was used before establish"
                resolved = raw_topic or self.aliases.get(alias)
                assert resolved
                self.messages.put_nowait((resolved, bytes(message.payload), message.qos,
                                          bool(message.retain), raw_topic, alias))
            except (AssertionError, ValueError) as error:
                self.failure = type(error).__name__

        self.client.on_connect = on_connect
        self.client.on_subscribe = on_subscribe
        self.client.on_message = on_message
        properties = Properties(PacketTypes.CONNECT)
        properties.TopicAliasMaximum = 1 if subscriber else 0
        assert self.client.connect("127.0.0.1", port, clean_start=True, properties=properties) == 0
        self.client.loop_start()
        assert self.connected.wait(5) and self.failure is None, "CONNECT not accepted"
        if subscriber:
            assert self.client.subscribe("p227g/#", qos=2)[0] == 0
            assert self.subscribed.wait(5) and self.failure is None, "subscription not accepted"

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()

    def publish(self, topic, payload, qos, *, retain=False):
        properties = Properties(PacketTypes.PUBLISH)
        properties.TopicAlias = 1
        result = self.client.publish(topic, payload, qos, retain, properties)
        assert result.rc == 0
        result.wait_for_publish(timeout=5)
        assert result.is_published(), "Paho publish did not complete"

    def expect(self, topic, payload, qos, *, compact=None, retained=None):
        item = self.messages.get(timeout=5)
        assert self.failure is None
        assert item[:3] == (topic, payload, qos), "resolved publication mismatch"
        if compact is not None:
            assert (item[4] == "") == compact, "wire alias compaction mismatch"
            assert item[5] == 1
        if retained is not None:
            assert item[3] == retained


def exercise(binary, directory):
    port = free_port()
    with server(binary, directory, port):
        receiver = source = None
        try:
            receiver = Peer(port, "p227g-receiver", subscriber=True)
            source = Peer(port, "p227g-source")
            source.publish("p227g/one", b"establish", 0)
            receiver.expect("p227g/one", b"establish", 0, compact=False)
            for qos in (0, 1, 2):
                data = bytes([qos, 0, 255])
                source.publish("", data, qos)
                receiver.expect("p227g/one", data, qos, compact=True)
            source.publish("p227g/two", b"rebind", 1)
            receiver.expect("p227g/two", b"rebind", 1)
            source.publish("", b"rebound", 2)
            receiver.expect("p227g/two", b"rebound", 2)
            source.publish("p227g/one", b"retained", 1, retain=True)
            receiver.expect("p227g/one", b"retained", 1, compact=True, retained=False)
            receiver.close()
            receiver = None
            receiver = Peer(port, "p227g-new-connection", subscriber=True)
            receiver.expect("p227g/one", b"retained", 1, compact=False, retained=True)
            source.publish("", b"after-reset", 2)
            receiver.expect("p227g/one", b"after-reset", 2, compact=True)
        finally:
            if receiver is not None:
                receiver.close()
            if source is not None:
                source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if os.name != "posix" or sys.flags.optimize or args.report.exists():
        parser.error("Linux/WSL assertions and a new report are required")
    binary = args.broker.resolve(strict=True)
    report = {"broker_sha256": digest(binary), "harness_sha256": digest(Path(__file__)),
              "broker_version": subprocess.check_output([binary, "--version"], text=True).strip(),
              "paho_version": paho.mqtt.__version__,
              "paho_client_sha256": digest(Path(mqtt.__file__)),
              "receiver_topic_resolution": "explicit fixture application adapter, not native Paho substitution",
              "mosquitto_reception": "not homologated by this Paho test"}
    began = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="xmqr-p227g-", dir="/var/tmp") as directory:
            exercise(binary, Path(directory))
        report.update(status="PASS", cleanup="PASS")
    except Exception as error:
        report.update(status="FAIL", error_type=type(error).__name__)
    report["binary_unchanged"] = digest(binary) == report["broker_sha256"]
    if not report["binary_unchanged"]:
        report["status"] = "FAIL"
    report["elapsed_seconds"] = round(time.monotonic() - began, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("P227_PAHO_ALIAS_" + report["status"], flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
