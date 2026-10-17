#!/usr/bin/env python3
"""Independent Eclipse Paho MQTT 5 interop against a disposable XMQR broker."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from threading import Event
import time

from paho.mqtt import client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties


def wait(event, label):
    if not event.wait(8):
        raise AssertionError(f"timeout waiting for {label}")


def session_properties():
    properties = Properties(PacketTypes.CONNECT)
    properties.SessionExpiryInterval = 60
    return properties


def make_client(identity, protocol=mqtt.MQTTv5):
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=identity,
                       protocol=protocol, reconnect_on_failure=False)


def connect(client, port, *, clean_start=True, properties=None):
    ready = Event()
    result = {}

    def on_connect(_client, _userdata, flags, reason, connack):
        result.update(reason=reason, flags=flags, properties=connack)
        ready.set()

    client.on_connect = on_connect
    assert client.connect("127.0.0.1", port, clean_start=clean_start,
                          properties=properties) == mqtt.MQTT_ERR_SUCCESS
    client.loop_start()
    wait(ready, "CONNACK")
    return result


def success(result):
    assert result["reason"].value == 0, result["reason"]


def publish(client, topic, data, qos, *, retain=False):
    info = client.publish(topic, data, qos=qos, retain=retain)
    assert info.rc == mqtt.MQTT_ERR_SUCCESS, info.rc
    info.wait_for_publish(timeout=8)
    assert info.is_published(), (topic, qos)


def stop(client):
    client.disconnect()
    client.loop_stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    args = parser.parse_args()
    assert args.broker.is_file(), args.broker
    with tempfile.TemporaryDirectory(prefix="xmqr-paho-mqtt5-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        env = dict(os.environ, MQTT_MODE="open-lab", MQTT_STATE_DIR=state,
                   MQTT_BIND=f"127.0.0.1:{port}")
        with open(Path(state) / "broker.log", "wb") as log:
            broker = subprocess.Popen([args.broker], env=env, stdout=log, stderr=log)
            clients = []
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    assert broker.poll() is None, "broker exited before listening"
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                            break
                    except OSError:
                        time.sleep(0.05)
                else:
                    raise AssertionError("broker did not listen")

                subscriber = make_client("")
                clients.append(subscriber)
                initial = connect(subscriber, port, properties=session_properties())
                success(initial)
                identity = getattr(initial["properties"], "AssignedClientIdentifier", None)
                assert isinstance(identity, str) and len(identity) == 37
                assert identity.startswith("xmqr-"), identity
                assert not initial["flags"].session_present

                subscribed = Event()
                messages = []
                received = Event()

                def on_subscribe(_client, _userdata, _mid, reasons, _properties):
                    assert all(reason.value <= 2 for reason in reasons), reasons
                    subscribed.set()

                def on_message(_client, _userdata, message):
                    messages.append((message.topic, bytes(message.payload), message.qos,
                                     message.retain))
                    received.set()

                subscriber.on_subscribe = on_subscribe
                subscriber.on_message = on_message
                code, _mid = subscriber.subscribe("paho/#", qos=2)
                assert code == mqtt.MQTT_ERR_SUCCESS
                wait(subscribed, "SUBACK")

                publisher = make_client("paho-publisher")
                clients.append(publisher)
                success(connect(publisher, port))
                for qos in (0, 1, 2):
                    received.clear()
                    publish(publisher, f"paho/qos{qos}", f"payload-{qos}".encode(), qos)
                    wait(received, f"PUBLISH QoS{qos}")
                assert [(topic, payload) for topic, payload, _, _ in messages] == [
                    (f"paho/qos{qos}", f"payload-{qos}".encode()) for qos in (0, 1, 2)
                ], messages

                publish(publisher, "paho/retained", b"retained", 1, retain=True)
                retained = make_client("paho-retained")
                clients.append(retained)
                retain_ready = Event()
                retained_messages = []
                retained.on_message = lambda _client, _userdata, message: (
                    retained_messages.append((message.topic, bytes(message.payload), message.qos,
                                              message.retain)), retain_ready.set())
                success(connect(retained, port))
                code, _mid = retained.subscribe("paho/retained", qos=1)
                assert code == mqtt.MQTT_ERR_SUCCESS
                wait(retain_ready, "retained delivery")
                assert retained_messages == [("paho/retained", b"retained", 1, True)], retained_messages

                stop(subscriber)
                clients.remove(subscriber)
                publish(publisher, "paho/offline", b"queued", 1)
                resumed = make_client(identity)
                clients.append(resumed)
                offline = Event()
                resumed.on_message = lambda _client, _userdata, message: (
                    messages.append((message.topic, bytes(message.payload), message.qos,
                                     message.retain)), offline.set())
                again = connect(resumed, port, clean_start=False,
                                properties=session_properties())
                success(again)
                assert again["flags"].session_present, again["flags"]
                wait(offline, "offline QoS1 after session resume")
                assert messages[-1][:2] == ("paho/offline", b"queued"), messages[-1]

                legacy = make_client("", protocol=mqtt.MQTTv311)
                clients.append(legacy)
                rejected = Event()
                refusal = {}
                def on_legacy_connect(_client, _userdata, _flags, reason, _properties):
                    refusal["reason"] = reason.value
                    rejected.set()
                def on_legacy_disconnect(_client, _userdata, _flags, reason, _properties):
                    refusal["disconnect"] = reason.value
                    rejected.set()
                legacy.on_connect = on_legacy_connect
                legacy.on_disconnect = on_legacy_disconnect
                # Paho 2.1.0 sends an empty identifier for MQTT 3.1.1.
                assert legacy.connect("127.0.0.1", port) == mqtt.MQTT_ERR_SUCCESS
                legacy.loop_start()
                wait(rejected, "MQTT 3.1.1 empty-ID refusal")
                assert refusal.get("reason") != 0 and not legacy.is_connected(), refusal
            finally:
                for client in clients:
                    stop(client)
                broker.terminate()
                broker.wait(timeout=8)
    print("P168_PAHO_MQTT5_PASS assigned ID, session present, QoS0/1/2, retained, offline, MQTT311 refusal")


if __name__ == "__main__":
    main()
