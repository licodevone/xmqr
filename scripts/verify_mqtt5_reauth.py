#!/usr/bin/env python3
"""P160: bounded MQTT 5 PLAIN re-authentication over isolated TLS/mTLS."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import tempfile

from verify_mqtt5_plain_auth import connect
from verify_mqtt5_sessions import packet
from verify_multi_endpoint import free_port, hash_fixture, wait_port


ROOT = Path(__file__).resolve().parents[1]


def auth(data, method=b"PLAIN", reason=0x19):
    properties = b"\x15" + len(method).to_bytes(2, "big") + method
    if data is not None:
        properties += b"\x16" + len(data).to_bytes(2, "big") + data
    body = bytes([reason, len(properties)]) + properties
    assert len(body) < 128
    return bytes([0xf0, len(body)]) + body


def conventional(port, ca, username, password):
    context = ssl.create_default_context(cafile=str(ca))
    stream = context.wrap_socket(socket.create_connection(("127.0.0.1", port), timeout=4),
                                 server_hostname="127.0.0.1")
    stream.settimeout(4)
    identity = b"p160-legacy"
    body = (b"\x00\x04MQTT\x05\xc2\x00\x1e\x00"
            + len(identity).to_bytes(2, "big") + identity
            + len(username).to_bytes(2, "big") + username
            + len(password).to_bytes(2, "big") + password)
    stream.sendall(bytes([0x10, len(body)]) + body)
    header, ack = packet(stream)
    assert header == 0x20 and ack[1] == 0 and b"PLAIN" not in ack, ack
    return stream


def expect_close(stream):
    try:
        assert stream.recv(1) == b""
    except (ConnectionResetError, ssl.SSLError):
        pass


def exercise(port, ca, secret, other_secret, cert):
    kwargs = {"cert": cert} if cert else {}
    stream, ack = connect(port, ca, b"fixture-device", secret, **kwargs)
    with stream:
        assert ack[1] == 0
        stream.sendall(auth(b"\0fixture-device\0" + secret))
        assert packet(stream) == (0xf0, b"\x00\x08\x15\x00\x05PLAIN")
        stream.sendall(b"\xc0\x00")
        assert packet(stream) == (0xd0, b"")
        topic = b"p160/value"
        subscribe = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x00"
        stream.sendall(bytes([0x82, len(subscribe)]) + subscribe)
        assert packet(stream) == (0x90, b"\x00\x01\x00\x00")
        publish = len(topic).to_bytes(2, "big") + topic + b"\x00after-reauth"
        stream.sendall(bytes([0x30, len(publish)]) + publish)
        assert packet(stream) == (0x30, publish)
    stream, ack = connect(port, ca, b"fixture-device", secret, **kwargs)
    with stream:
        assert ack[1] == 0
        stream.sendall(auth(b"\0fixture-device\0wrong-password"))
        assert packet(stream) == (0xe0, b"\x86\x00")
        expect_close(stream)
    if other_secret:
        stream, ack = connect(port, ca, b"fixture-device", secret, **kwargs)
        with stream:
            assert ack[1] == 0
            stream.sendall(auth(b"\0other-device\0" + other_secret))
            assert packet(stream) == (0xe0, b"\x86\x00")
            expect_close(stream)
    for frame in (auth(b"\0fixture-device\0" + secret, b"OTHER"),
                  auth(None), auth(b"\0fixture-device\0" + secret, reason=0x18)):
        stream, ack = connect(port, ca, b"fixture-device", secret, **kwargs)
        with stream:
            assert ack[1] == 0
            stream.sendall(frame)
            expect_close(stream)
    if cert is None:
        with conventional(port, ca, b"fixture-device", secret) as stream:
            stream.sendall(auth(b"\0fixture-device\0" + secret))
            expect_close(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    parser.add_argument("--admin", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "cert_fixture", ROOT.parent / "xmqr-client/validation/C27-integration.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix="xmqr-p160-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        fixture.certificates(root)
        secret = secrets.token_urlsafe(24).encode()
        other_secret = secrets.token_urlsafe(24).encode()
        password_hash = hash_fixture(args.admin, secret.decode())
        other_hash = hash_fixture(args.admin, other_secret.decode())
        der = ssl.PEM_cert_to_DER_cert((root / "client.crt").read_text())
        fingerprint = hashlib.sha256(der).hexdigest()
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MQTT_")}
        environment["MQTT_CONFIG"] = str(root / "broker.toml")
        for mode in ("tls-password", "secure-mtls"):
            other_acl = ("[[rules]]\nusername='other-device'\n"
                         "publish=['p160/other']\nsubscribe=['p160/other']\n") if mode == "tls-password" else ""
            (root / "acl.toml").write_text(
                "[[rules]]\nusername='fixture-device'\n"
                "publish=['p160/value']\nsubscribe=['p160/value']\n"
                f"{other_acl}")
            cert_line = f"cert_sha256='sha256:{fingerprint}'\n" if mode == "secure-mtls" else ""
            other_record = ("[[users]]\nusername='other-device'\n"
                            f"password_hash='{other_hash}'\n") if mode == "tls-password" else ""
            (root / "users.toml").write_text(
                "[[users]]\nusername='fixture-device'\n"
                f"password_hash='{password_hash}'\n{cert_line}"
                f"{other_record}")
            port = free_port()
            client_ca = 'client_ca="ca.crt"\n' if mode == "secure-mtls" else ""
            (root / "broker.toml").write_text(
                f'version=1\n[broker]\nmode="{mode}"\n'
                f'bind="127.0.0.1:{port}"\nstate_dir="state-{mode}"\n'
                '[tls]\nserver_cert="server.crt"\nserver_key="server.key"\n'
                f'{client_ca}[security]\nusers_file="users.toml"\nacl_file="acl.toml"\n')
            cert = (root / "client.crt", root / "client.key") if mode == "secure-mtls" else None
            with (root / f"broker-{mode}.log").open("wb") as log:
                broker = subprocess.Popen([str(args.broker)], env=environment,
                                          stdout=log, stderr=log)
                try:
                    try:
                        wait_port(broker, port)
                    except AssertionError as error:
                        raise AssertionError((root / f"broker-{mode}.log").read_text(errors="replace")[:2000]) from error
                    exercise(port, root / "ca.crt", secret,
                             other_secret if mode == "tls-password" else None, cert)
                finally:
                    if broker.poll() is None:
                        broker.terminate()
                        assert broker.wait(timeout=12) == 0
    print("P160_REAUTH_PASS TLS, mTLS, success, denial, identity, method, data and conventional session")


if __name__ == "__main__":
    main()
