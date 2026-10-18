#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent Paho2.1 enhanced PLAIN CONNECT over private TLS/mTLS."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import tempfile
from threading import Event

from paho.mqtt import client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from verify_multi_endpoint import free_port, hash_fixture, wait_port


def ready(event, label):
    assert event.wait(8), label + " timeout"


def peer(port, root, password, identity, *, mtls, method="PLAIN"):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=identity,
                         protocol=mqtt.MQTTv5, reconnect_on_failure=False)
    context = ssl.create_default_context(cafile=str(root / "ca.crt"))
    if mtls:
        context.load_cert_chain(str(root / "client.crt"), str(root / "client.key"))
    client.tls_set_context(context)
    properties = Properties(PacketTypes.CONNECT)
    properties.AuthenticationMethod = method
    properties.AuthenticationData = b"\x00fixture-device\x00" + password.encode()
    connected = Event()
    result = {}

    def on_connect(_client, _userdata, _flags, reason, connack):
        result.update(reason=reason.value, properties=connack)
        connected.set()

    client.on_connect = on_connect
    assert client.connect("127.0.0.1", port, clean_start=True,
                          properties=properties) == mqtt.MQTT_ERR_SUCCESS
    client.loop_start()
    try:
        ready(connected, "enhanced CONNECT")
    except BaseException:
        client.disconnect()
        client.loop_stop()
        raise
    return client, result


def stop(client):
    client.disconnect()
    client.loop_stop()


def exercise(binary, admin, root, fixture, mtls):
    fixture.certificates(root)
    password = secrets.token_urlsafe(24)
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
        (root / "client.crt").read_text())).hexdigest()
    users = "[[users]]\nusername='fixture-device'\n"
    users += f"password_hash='{hash_fixture(admin, password)}'\n"
    if mtls:
        users += f"cert_sha256='sha256:{fingerprint}'\n"
    (root / "users.toml").write_text(users)
    (root / "users.toml").chmod(0o600)
    (root / "acl.toml").write_text("[[rules]]\nusername='fixture-device'\n"
                                   "publish=['p227/paho-auth']\nsubscribe=['p227/paho-auth']\n")
    (root / "acl.toml").chmod(0o600)
    port = free_port()
    mode = "secure-mtls" if mtls else "tls-password"
    ca = 'client_ca="ca.crt"\n' if mtls else ""
    (root / "broker.toml").write_text(
        f'version=1\n[broker]\nmode="{mode}"\nbind="127.0.0.1:{port}"\nstate_dir="state"\n'
        '[tls]\nserver_cert="server.crt"\nserver_key="server.key"\n' + ca
        + '[security]\nusers_file="users.toml"\nacl_file="acl.toml"\n')
    environment = {key: value for key, value in os.environ.items() if not key.startswith("MQTT_")}
    environment["MQTT_CONFIG"] = str(root / "broker.toml")
    broker = subprocess.Popen([str(binary)], env=environment,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    clients = []
    try:
        wait_port(broker, port)
        receiver, result = peer(port, root, password, "p227-paho-sub", mtls=mtls)
        clients.append(receiver)
        assert result["reason"] == 0
        assert result["properties"].AuthenticationMethod == "PLAIN"
        subscribed = Event()
        received = Event()
        messages = []

        def on_subscribe(_client, _userdata, _identifier, reasons, _properties):
            if all(reason.value <= 2 for reason in reasons):
                subscribed.set()

        def on_message(_client, _userdata, message):
            messages.append((message.topic, bytes(message.payload), message.qos))
            received.set()

        receiver.on_subscribe = on_subscribe
        receiver.on_message = on_message
        assert receiver.subscribe("p227/paho-auth", qos=1)[0] == mqtt.MQTT_ERR_SUCCESS
        ready(subscribed, "SUBACK")
        sender, result = peer(port, root, password, "p227-paho-pub", mtls=mtls)
        clients.append(sender)
        assert result["reason"] == 0
        info = sender.publish("p227/paho-auth", b"public-fixture", qos=1)
        info.wait_for_publish(timeout=8)
        assert info.is_published()
        ready(received, "PUBLISH")
        assert messages == [("p227/paho-auth", b"public-fixture", 1)]
        for candidate, method, expected in (("wrong-fixture", "PLAIN", 0x86),
                                             (password, "UNSUPPORTED", 0x8c)):
            denied, result = peer(port, root, candidate, "p227-paho-denied", mtls=mtls, method=method)
            clients.append(denied)
            assert result["reason"] == expected and not denied.is_connected()
    finally:
        for client in clients:
            stop(client)
        if broker.poll() is None:
            broker.terminate()
            assert broker.wait(timeout=16) == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--admin", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "p227_certificates", root.parent / "xmqr-client/validation/C27-integration.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix="xmqr-p227-paho-auth-", dir="/var/tmp") as temporary:
        for mtls in (False, True):
            private = Path(temporary) / ("mtls" if mtls else "tls")
            private.mkdir(mode=0o700)
            exercise(args.broker.resolve(), args.admin.resolve(), private, fixture, mtls)
    print("P227_PAHO_AUTH_PASS initial PLAIN TLS/mTLS, pub/sub, bad password, unknown method; no AUTH reauthentication claim")


if __name__ == "__main__":
    main()
