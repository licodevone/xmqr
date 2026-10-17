#!/usr/bin/env python3
"""P159: bounded SASL PLAIN initial authentication on an isolated TLS listener."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import tempfile

from verify_mqtt5_sessions import packet
from verify_multi_endpoint import free_port, hash_fixture, wait_port, wait_subscription


ROOT = Path(__file__).resolve().parents[1]


def connect(port, ca, identity, password, maximum=None, method=b"PLAIN", cert=None,
            client_id=b"p159-device", will=None):
    context = ssl.create_default_context(cafile=str(ca))
    if cert:
        context.load_cert_chain(str(cert[0]), str(cert[1]))
    stream = context.wrap_socket(socket.create_connection(("127.0.0.1", port), timeout=4),
                                 server_hostname="127.0.0.1")
    stream.settimeout(4)
    data = b"\0" + identity + b"\0" + password
    properties = (b"\x15" + len(method).to_bytes(2, "big") + method
                  + b"\x16" + len(data).to_bytes(2, "big") + data)
    if maximum is not None:
        properties += b"\x27" + maximum.to_bytes(4, "big")
    flags = 0x06 if will else 0x02
    body = (b"\x00\x04MQTT\x05" + bytes([flags]) + b"\x00\x1e"
            + bytes([len(properties)]) + properties
            + len(client_id).to_bytes(2, "big") + client_id)
    if will:
        topic, payload = will
        body += (b"\x00" + len(topic).to_bytes(2, "big") + topic
                 + len(payload).to_bytes(2, "big") + payload)
    assert len(body) < 128
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20, (header, ack)
    return stream, ack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--admin", type=Path, required=True)
    parser.add_argument("--client", type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "cert_fixture", ROOT.parent / "xmqr-client/validation/C27-integration.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix="xmqr-p159-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        fixture.certificates(root)
        secret = secrets.token_urlsafe(24)
        (root / "users.toml").write_text(
            "[[users]]\nusername='fixture-device'\n"
            f"password_hash='{hash_fixture(args.admin, secret)}'\n")
        (root / "acl.toml").write_text(
            "[[rules]]\nusername='fixture-device'\n"
            "publish=['p159/value']\nsubscribe=['p159/value']\n")
        port = free_port()
        (root / "broker.toml").write_text(
            'version=1\n[broker]\nmode="tls-password"\n'
            f'bind="127.0.0.1:{port}"\nstate_dir="state"\n'
            '[tls]\nserver_cert="server.crt"\nserver_key="server.key"\n'
            '[security]\nusers_file="users.toml"\nacl_file="acl.toml"\n')
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MQTT_")}
        environment["MQTT_CONFIG"] = str(root / "broker.toml")
        with (root / "broker.log").open("wb") as log:
            broker = subprocess.Popen([str(args.broker)], env=environment,
                                      stdout=log, stderr=log)
            try:
                try:
                    wait_port(broker, port)
                except AssertionError as error:
                    raise AssertionError((root / "broker.log").read_text(errors="replace")[:2000]) from error
                stream, ack = connect(port, root / "ca.crt", b"fixture-device", secret.encode())
                with stream:
                    assert ack[1] == 0 and b"\x15\x00\x05PLAIN" in ack, ack
                    stream.sendall(b"\xc0\x00")
                    assert packet(stream) == (0xd0, b"")
                    stream.sendall(b"\xe0\x00")
                for candidate, maximum, reason in (
                    (b"wrong-password", None, 0x86),
                    (secret.encode(), 14, 0x95),
                ):
                    stream, ack = connect(port, root / "ca.crt", b"fixture-device",
                                          candidate, maximum)
                    with stream:
                        assert ack[1] == reason, (reason, ack)
                stream, ack = connect(port, root / "ca.crt", b"fixture-device",
                                      secret.encode(), 15)
                with stream:
                    assert ack[1] == 0 and b"\x15\x00\x05PLAIN" in ack and len(ack) == 13, ack
                for identity, password, method, reason in (
                    (b"", secret.encode(), b"PLAIN", 0x86),
                    (b"fixture-device", secret.encode(), b"OTHER", 0x8c),
                ):
                    stream, ack = connect(port, root / "ca.crt", identity, password, method=method)
                    with stream:
                        assert ack[1] == reason, (reason, ack)
                if args.client:
                    password_file = root / "password"
                    password_file.write_text(secret + "\n")
                    password_file.chmod(0o600)
                    common = [str(args.client), "--tls-password", "--protocol-version", "5",
                              "--auth-method", "plain", "--host", "127.0.0.1",
                              "--port", str(port), "--ca", str(root / "ca.crt"),
                              "--username", "fixture-device", "--password-file",
                              str(password_file)]
                    subscriber = subprocess.Popen([common[0], "sub", *common[1:], "--topic",
                                                   "p159/value", "--count", "1", "--output", "jsonl"],
                                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                  text=True)
                    try:
                        wait_subscription(subscriber)
                        published = subprocess.run([common[0], "pub", *common[1:], "--topic",
                                                    "p159/value", "--message", "plain-ok"],
                                                   capture_output=True, text=True, timeout=12)
                        assert published.returncode == 0, published.stderr
                        output, errors = subscriber.communicate(timeout=12)
                        assert subscriber.returncode == 0, errors
                        event = json.loads(output.strip())
                        assert bytes(event["payload_bytes"]) == b"plain-ok", event
                    finally:
                        if subscriber.poll() is None:
                            subscriber.terminate()
                            subscriber.wait(timeout=5)
                    password_file.write_text("wrong-password\n")
                    rejected = subprocess.run([common[0], "pub", *common[1:], "--topic",
                                               "p159/value", "--message", "hidden"],
                                              capture_output=True, text=True, timeout=12)
                    assert rejected.returncode != 0 and "wrong-password" not in rejected.stderr, rejected
            finally:
                if broker.poll() is None:
                    broker.terminate()
                    assert broker.wait(timeout=12) == 0
        der = ssl.PEM_cert_to_DER_cert((root / "client.crt").read_text())
        fingerprint = hashlib.sha256(der).hexdigest()
        (root / "users.toml").write_text(
            "[[users]]\nusername='fixture-device'\n"
            f"password_hash='{hash_fixture(args.admin, secret)}'\n"
            f"cert_sha256='sha256:{fingerprint}'\n")
        mtls_port = free_port()
        (root / "broker.toml").write_text(
            'version=1\n[broker]\nmode="secure-mtls"\n'
            f'bind="127.0.0.1:{mtls_port}"\nstate_dir="state-mtls"\n'
            '[tls]\nserver_cert="server.crt"\nserver_key="server.key"\nclient_ca="ca.crt"\n'
            '[security]\nusers_file="users.toml"\nacl_file="acl.toml"\n')
        with (root / "broker-mtls.log").open("wb") as log:
            broker = subprocess.Popen([str(args.broker)], env=environment, stdout=log, stderr=log)
            try:
                wait_port(broker, mtls_port)
                cert = (root / "client.crt", root / "client.key")
                stream, ack = connect(mtls_port, root / "ca.crt", b"fixture-device",
                                      secret.encode(), cert=cert)
                with stream:
                    assert ack[1] == 0 and b"\x15\x00\x05PLAIN" in ack, ack
                stream, ack = connect(mtls_port, root / "ca.crt", b"fixture-device",
                                      b"wrong-password", cert=cert)
                with stream:
                    assert ack[1] == 0x86, ack
            finally:
                if broker.poll() is None:
                    broker.terminate()
                    assert broker.wait(timeout=12) == 0
    scope = " and client interop" if args.client else ""
    print(f"P159_TLS_PASS initial PLAIN, bad password, packet budget, TLS, mTLS{scope}")


if __name__ == "__main__":
    main()
