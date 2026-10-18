#!/usr/bin/env python3
"""P212: isolated mTLS WebSocket MQTT wire and security checks."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import select
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_multi_endpoint import free_port, hash_fixture, wait_port, wait_subscription
from verify_websocket_lab import exact, mqtt_packet, send_frame, tcp_packet


def openssl(root, *args):
    subprocess.run(["openssl", *map(str, args)], cwd=root, check=True,
                   capture_output=True, timeout=15)


def certificates(root):
    openssl(root, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
            "-keyout", "ca.key", "-out", "ca.crt", "-subj", "/CN=P212-test-CA",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    for serial, name, san, usage in ((2, "server", "IP:127.0.0.1", "serverAuth"),
                                    (3, "client", "DNS:client.fixture", "clientAuth")):
        openssl(root, "req", "-new", "-newkey", "rsa:2048", "-nodes",
                "-keyout", f"{name}.key", "-out", f"{name}.csr",
                "-subj", f"/CN={name}")
        (root / f"{name}.ext").write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            f"extendedKeyUsage={usage}\nsubjectAltName={san}\n")
        openssl(root, "x509", "-req", "-in", f"{name}.csr",
                "-CA", "ca.crt", "-CAkey", "ca.key", "-set_serial", str(serial),
                "-days", "1", "-extfile", f"{name}.ext", "-out", f"{name}.crt")
    openssl(root, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
            "-keyout", "other.key", "-out", "other.crt",
            "-subj", "/CN=P212-other-CA",
            "-addext", "basicConstraints=critical,CA:TRUE")


def connect_packet(version, client_id, username, password):
    def field(value):
        return len(value).to_bytes(2, "big") + value
    body = b"\x00\x04MQTT" + bytes([version, 0xc2, 0, 30])
    if version == 5:
        body += b"\x00"
    body += field(client_id) + field(username) + field(password)
    assert len(body) < 128
    return b"\x10" + bytes([len(body)]) + body


def secure_socket(root, port, *, certificate=True, ca="ca.crt", hostname="127.0.0.1"):
    context = ssl.create_default_context(cafile=str(root / ca))
    if certificate:
        context.load_cert_chain(str(root / "client.crt"), str(root / "client.key"))
    raw = socket.create_connection(("127.0.0.1", port), timeout=4)
    raw.settimeout(4)
    return context.wrap_socket(raw, server_hostname=hostname)


def handshake(stream, port, *, path="/mqtt", protocol="mqtt", origin=None):
    request = (f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
               "Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {base64.b64encode(os.urandom(16)).decode()}\r\n"
               "Sec-WebSocket-Version: 13\r\n"
               f"Sec-WebSocket-Protocol: {protocol}\r\n"
               + (f"Origin: {origin}\r\n" if origin else "") + "\r\n")
    stream.sendall(request.encode())
    response = bytearray()
    while not response.endswith(b"\r\n\r\n"):
        response.extend(exact(stream, 1))
        assert len(response) < 4096
    return bytes(response)


def authenticated_ws(root, port, version, password, client_id, *, origin=None):
    stream = secure_socket(root, port)
    assert handshake(stream, port, origin=origin).startswith(b"HTTP/1.1 101")
    send_frame(stream, 2, connect_packet(version, client_id, b"device", password))
    reply = mqtt_packet(stream, bytearray())
    assert reply[0] == 0x20 and reply[2:4] == b"\x00\x00", reply
    return stream


def check_mqtt(root, port, tcp_port, password):
    topic = b"p212/allowed"
    for version in (4, 5):
        subscriber = authenticated_ws(root, port, version, password, b"p212-sub")
        publisher = authenticated_ws(root, port, version, password, b"p212-pub")
        try:
            subscribe = b"\x00\x01" + (b"\x00" if version == 5 else b"")
            subscribe += len(topic).to_bytes(2, "big") + topic + b"\x00"
            send_frame(subscriber, 2, b"\x82" + bytes([len(subscribe)]) + subscribe)
            suback = mqtt_packet(subscriber, bytearray())
            assert suback[0] == 0x90 and suback[-1] == 0, suback
            payload = b"wss-" + str(version).encode()
            body = len(topic).to_bytes(2, "big") + topic
            if version == 5:
                body += b"\x00"
            body += payload
            send_frame(publisher, 2, b"\x30" + bytes([len(body)]) + body)
            delivered = mqtt_packet(subscriber, bytearray())
            assert delivered[0] == 0x30 and delivered.endswith(payload), delivered
            with secure_socket(root, tcp_port) as tcp:
                tcp.sendall(connect_packet(version, b"p212-tcp", b"device", password))
                assert tcp_packet(tcp)[0] == 0x20
                cross = b"tcp-to-wss"
                body = len(topic).to_bytes(2, "big") + topic
                if version == 5:
                    body += b"\x00"
                body += cross
                tcp.sendall(b"\x30" + bytes([len(body)]) + body)
                assert mqtt_packet(subscriber, bytearray()).endswith(cross)
        finally:
            subscriber.close()
            publisher.close()

    denied = authenticated_ws(root, port, 5, password, b"p212-denied")
    try:
        blocked = b"p212/denied"
        subscribe = b"\x00\x02\x00" + len(blocked).to_bytes(2, "big") + blocked + b"\x00"
        send_frame(denied, 2, b"\x82" + bytes([len(subscribe)]) + subscribe)
        suback = mqtt_packet(denied, bytearray())
        assert suback[0] == 0x90 and suback[-1] == 0x87, suback
        body = len(blocked).to_bytes(2, "big") + blocked + b"\x00\x03\x00" + b"no"
        send_frame(denied, 2, b"\x32" + bytes([len(body)]) + body)
        puback = mqtt_packet(denied, bytearray())
        assert puback[0] == 0x40 and puback[4] == 0x87, puback
    finally:
        denied.close()


def rotate_certificate(root, broker, log_path, port, password):
    with secure_socket(root, port) as stream:
        original = stream.getpeercert(binary_form=True)
    held = authenticated_ws(root, port, 5, password, b"p212-held-rotation")
    topic = b"p212/allowed"
    subscribe = b"\x00\x04\x00" + len(topic).to_bytes(2, "big") + topic + b"\x00"
    send_frame(held, 2, b"\x82" + bytes([len(subscribe)]) + subscribe)
    assert mqtt_packet(held, bytearray())[-1] == 0
    openssl(root, "req", "-new", "-newkey", "rsa:2048", "-nodes",
            "-keyout", "server-next.key", "-out", "server-next.csr",
            "-subj", "/CN=server-next")
    (root / "server-next.ext").write_text(
        "basicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\nsubjectAltName=IP:127.0.0.1\n")
    openssl(root, "x509", "-req", "-in", "server-next.csr",
            "-CA", "ca.crt", "-CAkey", "ca.key", "-set_serial", "5",
            "-days", "1", "-extfile", "server-next.ext",
            "-out", "server-next.crt")
    shutil.copyfile(root / "server-next.crt", root / "server.crt")
    shutil.copyfile(root / "server-next.key", root / "server.key")
    previous = log_path.stat().st_size
    broker.send_signal(signal.SIGUSR1)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if "TLS rotation committed" in log_path.read_bytes()[previous:].decode(errors="replace"):
            break
        assert broker.poll() is None
        time.sleep(.05)
    else:
        raise AssertionError("WSS did not observe committed TLS rotation")
    with secure_socket(root, port) as stream:
        updated = stream.getpeercert(binary_form=True)
    assert updated != original
    try:
        with authenticated_ws(root, port, 5, password, b"p212-new-rotation") as publisher:
            payload = b"after-rotation"
            body = len(topic).to_bytes(2, "big") + topic + b"\x00" + payload
            send_frame(publisher, 2, b"\x30" + bytes([len(body)]) + body)
            assert mqtt_packet(held, bytearray()).endswith(payload)
    finally:
        held.close()


def check_rejections(root, port, password):
    for kwargs in ({"path": "/bad"}, {"protocol": "other"},
                   {"origin": "https://example.invalid"}):
        with secure_socket(root, port) as stream:
            assert handshake(stream, port, **kwargs).startswith(b"HTTP/1.1 400")
    with secure_socket(root, port) as stream:
        assert handshake(stream, port).startswith(b"HTTP/1.1 101")
        send_frame(stream, 1, b"text is not MQTT")
        try:
            assert stream.recv(1) in (b"", b"\x88")
        except (ConnectionResetError, ssl.SSLError):
            pass
    for kwargs in ({"certificate": False}, {"ca": "other.crt"},
                   {"hostname": "wrong.invalid"}):
        try:
            with secure_socket(root, port, **kwargs) as stream:
                handshake(stream, port)
                send_frame(stream, 2, connect_packet(4, b"invalid", b"device", password))
                reply = mqtt_packet(stream, bytearray())
                raise AssertionError(f"invalid TLS client accepted: {kwargs}, {reply!r}")
        except (ssl.SSLError, OSError, EOFError):
            pass


def check_browser_origin(root, port, password):
    allowed = "https://browser.example"
    for origin in ("https://other.example", "https://browser.example/", "null"):
        with secure_socket(root, port) as stream:
            assert handshake(stream, port, origin=origin).startswith(b"HTTP/1.1 400")
    for version in (4, 5):
        subscriber = authenticated_ws(root, port, version, password,
                                      b"p216-browser-sub", origin=allowed)
        publisher = authenticated_ws(root, port, version, password,
                                     b"p216-browser-pub", origin=allowed)
        try:
            topic = b"p212/allowed"
            subscribe = b"\x00\x01" + (b"\x00" if version == 5 else b"")
            subscribe += len(topic).to_bytes(2, "big") + topic + b"\x00"
            send_frame(subscriber, 2, b"\x82" + bytes([len(subscribe)]) + subscribe)
            assert mqtt_packet(subscriber, bytearray())[-1] == 0
            payload = b"browser-origin-" + str(version).encode()
            body = len(topic).to_bytes(2, "big") + topic
            if version == 5:
                body += b"\x00"
            body += payload
            send_frame(publisher, 2, b"\x30" + bytes([len(body)]) + body)
            assert mqtt_packet(subscriber, bytearray()).endswith(payload)
        finally:
            subscriber.close()
            publisher.close()
    denied = authenticated_ws(root, port, 5, password,
                              b"p216-browser-acl", origin=allowed)
    try:
        topic = b"p212/denied"
        subscribe = b"\x00\x02\x00" + len(topic).to_bytes(2, "big") + topic + b"\x00"
        send_frame(denied, 2, b"\x82" + bytes([len(subscribe)]) + subscribe)
        assert mqtt_packet(denied, bytearray())[-1] == 0x87
    finally:
        denied.close()
    with secure_socket(root, port) as stream:
        assert handshake(stream, port, origin=allowed).startswith(b"HTTP/1.1 101")
        send_frame(stream, 2, connect_packet(5, b"p216-wrong-password",
                                              b"device", b"wrong-password"))
        try:
            reply = mqtt_packet(stream, bytearray())
            assert not (reply[0] == 0x20 and reply[2:4] == b"\x00\x00"), reply
        except (ssl.SSLError, OSError, EOFError):
            pass
    try:
        with secure_socket(root, port, certificate=False) as stream:
            handshake(stream, port, origin=allowed)
            raise AssertionError("allowed Origin bypassed client certificate")
    except (ssl.SSLError, OSError, EOFError):
        pass


def check_admission(root, port, tcp_port, password):
    deadline = time.monotonic() + 5
    while True:
        try:
            held = authenticated_ws(root, port, 4, password, b"p212-held")
            break
        except (ssl.SSLError, OSError, EOFError, AssertionError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(.05)
    try:
        try:
            with secure_socket(root, tcp_port) as unexpected:
                unexpected.sendall(connect_packet(4, b"p212-extra", b"device", password))
                reply = tcp_packet(unexpected)
                raise AssertionError(f"shared admission was bypassed: {reply!r}")
        except (ssl.SSLError, OSError, EOFError):
            pass
    finally:
        send_frame(held, 2, b"\xe0\x00")
        held.close()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with secure_socket(root, tcp_port) as recovered:
                recovered.sendall(connect_packet(4, b"p212-recovered", b"device", password))
                assert tcp_packet(recovered)[0] == 0x20
                return
        except (ssl.SSLError, OSError, EOFError):
            time.sleep(.05)
    raise AssertionError("shared admission slot did not recover")


def check_client(root, port, tcp_port, client, password, profile_client=False):
    secret_file = root / "client-password"
    secret_file.write_bytes(password + b"\n")
    secret_file.chmod(0o600)
    common = ["--topic", "p212/allowed", "--username", "device",
              "--ca", str(root / "ca.crt"), "--cert", str(root / "client.crt"),
              "--key", str(root / "client.key"), "--password-file", str(secret_file)]
    for version in ("3.1.1", "5"):
        for pub_wss in (True, False):
            source = (["--ws-url", f"wss://127.0.0.1:{port}/mqtt"] if pub_wss
                      else ["--port", str(tcp_port)])
            destination = (["--port", str(tcp_port)] if pub_wss
                           else ["--ws-url", f"wss://127.0.0.1:{port}/mqtt"])
            payload = f"c114-{version}-{'wss' if pub_wss else 'tcp'}"
            publish = subprocess.run(
                [str(client), "pub", *common, *source, "--protocol-version", version,
                 "--client-id", "c114-pub", "--message", payload,
                 "--qos", "1", "--retain", "true"],
                capture_output=True, timeout=12)
            assert publish.returncode == 0, publish.stderr.decode(errors="replace")
            received = subprocess.run(
                [str(client), "sub", *common, *destination, "--protocol-version", version,
                 "--client-id", "c114-sub", "--count", "1"],
                capture_output=True, timeout=12)
            assert received.returncode == 0, received.stderr.decode(errors="replace")
            assert payload.encode() in received.stdout, received.stdout
        if profile_client:
            profile = root / "c116-connection.toml"
            profile.write_text(
                "version=1\n[connection]\n"
                f"ws_url={json.dumps(f'wss://127.0.0.1:{port}/mqtt')}\n"
                "username=\"device\"\n"
                f"ca={json.dumps(str(root / 'ca.crt'))}\n"
                f"cert={json.dumps(str(root / 'client.crt'))}\n"
                f"key={json.dumps(str(root / 'client.key'))}\n"
                f"password_file={json.dumps(str(secret_file))}\n")
            payload = f"c116-profile-{version}"
            publish = subprocess.run(
                [str(client), "pub", "--profile", str(profile),
                 "--protocol-version", version, "--client-id", "c116-profile-pub",
                 "--topic", "p212/allowed", "--message", payload,
                 "--qos", "1", "--retain", "true"],
                capture_output=True, timeout=12)
            assert publish.returncode == 0, publish.stderr.decode(errors="replace")
            received = subprocess.run(
                [str(client), "sub", "--profile", str(profile),
                 "--protocol-version", version, "--client-id", "c116-profile-sub",
                 "--topic", "p212/allowed", "--count", "1"],
                capture_output=True, timeout=12)
            assert received.returncode == 0, received.stderr.decode(errors="replace")
            assert payload.encode() in received.stdout, received.stdout
    endpoint = ["--ws-url", f"wss://127.0.0.1:{port}/mqtt"]
    wrong_password = root / "wrong-password"
    wrong_password.write_text("wrong-secret\n")
    wrong_password.chmod(0o600)
    for changed in (
        ["--topic", "p212/denied", "--username", "device",
         "--ca", str(root / "ca.crt"), "--cert", str(root / "client.crt"),
         "--key", str(root / "client.key"), "--password-file", str(secret_file)],
        ["--topic", "p212/allowed", "--username", "device",
         "--ca", str(root / "ca.crt"), "--cert", str(root / "client.crt"),
         "--key", str(root / "client.key"), "--password-file", str(wrong_password)],
        ["--topic", "p212/allowed", "--username", "device",
         "--ca", str(root / "other.crt"), "--cert", str(root / "client.crt"),
         "--key", str(root / "client.key"), "--password-file", str(secret_file)],
    ):
        rejected = subprocess.run(
            [str(client), "pub", *changed, *endpoint, "--protocol-version", "5",
             "--client-id", "c114-denied", "--message", "denied", "--qos", "1"],
            capture_output=True, timeout=12)
        assert rejected.returncode != 0, rejected.stdout


def check_client_qos1_outbox(root, port, client, password):
    secret_file = root / "client-password"
    secret_file.write_bytes(password + b"\n")
    secret_file.chmod(0o600)
    outbox = root / "c119-wss-outbox"
    outbox.mkdir(mode=0o700)
    common = ["--ws-url", f"wss://127.0.0.1:{port}/mqtt",
              "--username", "device", "--ca", str(root / "ca.crt"),
              "--cert", str(root / "client.crt"), "--key", str(root / "client.key"),
              "--password-file", str(secret_file), "--protocol-version", "5",
              "--client-id", "c119-wss-pub", "--topic", "p212/allowed"]
    result = subprocess.run(
        [str(client), "pub", *common, "--message", "c119-durable-wss",
         "--qos", "1", "--retain", "true", "--clean-start", "false",
         "--session-expiry-seconds", "60", "--outbox-dir", str(outbox)],
        capture_output=True, timeout=12)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert not (outbox / "pending.json").exists()
    result = subprocess.run(
        [str(client), "sub", *common[:-4], "--client-id", "c119-wss-sub",
         "--topic", "p212/allowed", "--count", "1"],
        capture_output=True, timeout=12)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert b"c119-durable-wss" in result.stdout, result.stdout


def check_client_qos2_outbox(root, port, client, password):
    secret_file = root / "client-password"
    outbox = root / "c122-wss-outbox"
    outbox.mkdir(mode=0o700)
    common = ["--ws-url", f"wss://127.0.0.1:{port}/mqtt",
              "--username", "device", "--ca", str(root / "ca.crt"),
              "--cert", str(root / "client.crt"), "--key", str(root / "client.key"),
              "--password-file", str(secret_file), "--protocol-version", "5",
              "--client-id", "c122-wss-pub", "--topic", "p212/allowed"]
    result = subprocess.run(
        [str(client), "pub", *common, "--message", "c122-durable-qos2-wss",
         "--qos", "2", "--retain", "true", "--clean-start", "false",
         "--session-expiry-seconds", "60", "--outbox-dir", str(outbox)],
        capture_output=True, timeout=12)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert not (outbox / "pending-qos2.json").exists()
    result = subprocess.run(
        [str(client), "sub", *common[:-4], "--client-id", "c122-wss-sub",
         "--topic", "p212/allowed", "--count", "1"],
        capture_output=True, timeout=12)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert b"c122-durable-qos2-wss" in result.stdout, result.stdout


def check_client_durable_subscription(root, port, client, password):
    secret_file = root / "client-password"
    secret_file.write_bytes(password + b"\n")
    secret_file.chmod(0o600)
    state = root / "c123-wss-subscription"
    state.mkdir(mode=0o700)
    common = ["--ws-url", f"wss://127.0.0.1:{port}/mqtt",
              "--username", "device", "--ca", str(root / "ca.crt"),
              "--cert", str(root / "client.crt"), "--key", str(root / "client.key"),
              "--password-file", str(secret_file), "--protocol-version", "5"]
    subscription = [str(client), "sub", *common, "--topic", "p212/allowed",
                    "--qos", "1", "--client-id", "c123-wss-sub",
                    "--clean-start", "false", "--session-expiry-seconds", "60",
                    "--subscription-state-dir", str(state), "--output", "jsonl"]
    first = subprocess.Popen(subscription, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True)
    try:
        wait_subscription(first)
        manifest = state / "subscription.json"
        assert json.loads(manifest.read_text())["pending"]["stage"] == "Active"
        first.kill()
        first.communicate(timeout=5)
        before = manifest.read_bytes()
        wrong = [f"wss://127.0.0.1:{port + 1}/mqtt" if arg == common[1] else arg
                 for arg in subscription]
        rejected = subprocess.run(wrong, capture_output=True, timeout=8)
        assert rejected.returncode != 0 and b"manifesto" in rejected.stderr.lower()
        assert manifest.read_bytes() == before
        time.sleep(.2)
        published = subprocess.run(
            [str(client), "pub", *common, "--topic", "p212/allowed",
             "--message", "c123-offline-wss", "--qos", "1",
             "--client-id", "c123-wss-pub"], capture_output=True, timeout=12)
        assert published.returncode == 0, published.stderr.decode(errors="replace")
        resumed = subprocess.Popen(subscription, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0)
        try:
            lines = []
            for _ in range(4):
                ready, _, _ = select.select([resumed.stdout], [], [], 8)
                assert ready, ("offline WSS publication not delivered", lines)
                lines.append(resumed.stdout.readline())
                if bytes(json.loads(lines[-1])["payload_bytes"]) == b"c123-offline-wss":
                    break
            assert any(bytes(json.loads(line)["payload_bytes"]) == b"c123-offline-wss"
                       for line in lines), lines
            assert manifest.read_bytes() == before
        finally:
            if resumed.poll() is None:
                resumed.kill()
            resumed.communicate(timeout=5)
    finally:
        if first.poll() is None:
            first.kill()
            first.communicate(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path)
    parser.add_argument("--profile-client", action="store_true")
    parser.add_argument("--outbox-client", action="store_true")
    parser.add_argument("--durable-sub-client", action="store_true")
    args = parser.parse_args()
    if (args.profile_client or args.outbox_client or args.durable_sub_client) and not args.client:
        parser.error("--profile-client/--outbox-client/--durable-sub-client exige --client")
    broker_bin = ROOT / "target/debug/mqtt-broker"
    admin_bin = ROOT / "target/debug/mqtt-admin"
    assert broker_bin.is_file() and admin_bin.is_file()
    with tempfile.TemporaryDirectory(prefix="xmqr-p212-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        certificates(root)
        password = secrets.token_urlsafe(18).encode()
        fingerprint = hashlib.sha256(
            ssl.PEM_cert_to_DER_cert((root / "client.crt").read_text())).hexdigest()
        digest = hash_fixture(admin_bin, password.decode())
        (root / "users.toml").write_text(
            f'[[users]]\nusername="device"\npassword_hash="{digest}"\n'
            f'cert_sha256="sha256:{fingerprint}"\n')
        (root / "acl.toml").write_text(
            '[[rules]]\nusername="device"\npublish=["p212/allowed"]\n'
            'subscribe=["p212/allowed"]\n')
        tcp_port, port = free_port(), free_port()
        assert tcp_port != port
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MQTT_")}
        environment.update(MQTT_MODE="secure-mtls", MQTT_BIND=f"127.0.0.1:{tcp_port}",
                           MQTT_WSS_BIND=f"127.0.0.1:{port}", MQTT_STATE_DIR=str(root / "state"),
                           MQTT_SERVER_CERT=str(root / "server.crt"),
                           MQTT_SERVER_KEY=str(root / "server.key"),
                           MQTT_CLIENT_CA=str(root / "ca.crt"),
                           MQTT_USERS_FILE=str(root / "users.toml"),
                           MQTT_ACL_FILE=str(root / "acl.toml"),
                           RUST_LOG="info")
        for override in (
            {"MQTT_MODE": "open-lab"}, {"MQTT_WSS_BIND": f"0.0.0.0:{port}"},
            {"MQTT_WSS_BIND": f"127.0.0.1:{tcp_port}"},
            {"MQTT_WSS_BIND": "127.0.0.1:0"},
            {"MQTT_WSS_REMOTE_ENABLED": "true"},
            {"MQTT_WSS_REMOTE_ENABLED": "1"},
            {"MQTT_WSS_BIND": f"0.0.0.0:{port}", "MQTT_WSS_REMOTE_ENABLED": "false"},
            {"MQTT_WSS_BIND": f"0.0.0.0:{port}", "MQTT_WSS_REMOTE_ENABLED": "true",
             "MQTT_MODE": "open-lab"},
            {"MQTT_WSS_ALLOWED_ORIGINS": "http://browser.example"},
            {"MQTT_WSS_ALLOWED_ORIGINS": "https://*.example"},
            {"MQTT_WSS_ALLOWED_ORIGINS": "https://browser.example/"},
            {"MQTT_WSS_ALLOWED_ORIGINS": "https://browser.example,https://browser.example"},
        ):
            rejected = subprocess.run([str(broker_bin)], env=dict(environment, **override),
                                      capture_output=True, timeout=5)
            assert rejected.returncode != 0, override
        no_remote_bind = dict(environment, MQTT_WSS_REMOTE_ENABLED="true")
        no_remote_bind.pop("MQTT_WSS_BIND")
        assert subprocess.run([str(broker_bin)], env=no_remote_bind,
                              capture_output=True, timeout=5).returncode != 0
        no_wss_origin = dict(environment, MQTT_WSS_ALLOWED_ORIGINS="https://browser.example")
        no_wss_origin.pop("MQTT_WSS_BIND")
        assert subprocess.run([str(broker_bin)], env=no_wss_origin,
                              capture_output=True, timeout=5).returncode != 0
        log_path = root / "broker.log"
        with log_path.open("wb") as log:
            broker = subprocess.Popen([str(broker_bin)], env=environment,
                                      stdout=log, stderr=log)
            try:
                wait_port(broker, port)
                check_mqtt(root, port, tcp_port, password)
                check_rejections(root, port, password)
                rotate_certificate(root, broker, log_path, port, password)
                check_mqtt(root, port, tcp_port, password)
                if args.client:
                    check_client(root, port, tcp_port, args.client, password,
                                 profile_client=args.profile_client)
                    if args.outbox_client:
                        check_client_qos1_outbox(root, port, args.client, password)
                        check_client_qos2_outbox(root, port, args.client, password)
                    if args.durable_sub_client:
                        check_client_durable_subscription(root, port, args.client, password)
                broker.send_signal(signal.SIGTERM)
                assert broker.wait(timeout=8) == 0
            finally:
                if broker.poll() is None:
                    broker.kill()
                    broker.wait(timeout=8)
        (root / "broker.toml").write_text(
            'version=1\n[broker]\n'
            f'wss_bind="127.0.0.1:{port}"\n')
        admission_env = dict(environment, MQTT_CONFIG=str(root / "broker.toml"),
                             MQTT_MAX_CONNECTIONS="1")
        admission_env.pop("MQTT_WSS_BIND")
        with log_path.open("ab") as log:
            broker = subprocess.Popen([str(broker_bin)], env=admission_env,
                                      stdout=log, stderr=log)
            try:
                wait_port(broker, port)
                check_admission(root, port, tcp_port, password)
                broker.send_signal(signal.SIGTERM)
                assert broker.wait(timeout=8) == 0
            finally:
                if broker.poll() is None:
                    broker.kill()
                    broker.wait(timeout=8)
        remote_env = dict(environment, MQTT_STATE_DIR=str(root / "remote-state"),
                          MQTT_WSS_BIND=f"0.0.0.0:{port}",
                          MQTT_WSS_REMOTE_ENABLED="true")
        with log_path.open("ab") as log:
            broker = subprocess.Popen([str(broker_bin)], env=remote_env,
                                      stdout=log, stderr=log)
            try:
                try:
                    wait_port(broker, port)
                except AssertionError as error:
                    raise AssertionError(log_path.read_text(errors="replace")[-1000:]) from error
                check_mqtt(root, port, tcp_port, password)
                broker.send_signal(signal.SIGTERM)
                assert broker.wait(timeout=8) == 0
            finally:
                if broker.poll() is None:
                    broker.kill()
                    broker.wait(timeout=8)
        browser_env = dict(environment, MQTT_STATE_DIR=str(root / "browser-state"),
                           MQTT_WSS_ALLOWED_ORIGINS="https://browser.example")
        with log_path.open("ab") as log:
            broker = subprocess.Popen([str(broker_bin)], env=browser_env,
                                      stdout=log, stderr=log)
            try:
                wait_port(broker, port)
                check_browser_origin(root, port, password)
                check_mqtt(root, port, tcp_port, password)
                broker.send_signal(signal.SIGTERM)
                assert broker.wait(timeout=8) == 0
            finally:
                if broker.poll() is None:
                    broker.kill()
                    broker.wait(timeout=8)
        (root / "browser.toml").write_text(
            'version=1\n[broker]\n'
            f'wss_bind="127.0.0.1:{port}"\n'
            'wss_allowed_origins=["https://browser.example"]\n')
        toml_env = dict(environment, MQTT_CONFIG=str(root / "browser.toml"),
                        MQTT_STATE_DIR=str(root / "browser-toml-state"))
        toml_env.pop("MQTT_WSS_BIND")
        with log_path.open("ab") as log:
            broker = subprocess.Popen([str(broker_bin)], env=toml_env,
                                      stdout=log, stderr=log)
            try:
                wait_port(broker, port)
                with authenticated_ws(root, port, 5, password,
                                      b"p216-toml", origin="https://browser.example"):
                    pass
                broker.send_signal(signal.SIGTERM)
                assert broker.wait(timeout=8) == 0
            finally:
                if broker.poll() is None:
                    broker.kill()
                    broker.wait(timeout=8)
    print("P212_WSS_MTLS_WIRE_PASS" +
          (" C114_CLIENT_CROSS_PASS" if args.client else "") +
          (" C116_PROFILE_BROKER_PASS" if args.profile_client else "") +
          (" C119_WSS_QOS1_BROKER_PASS C122_WSS_QOS2_BROKER_PASS"
           if args.outbox_client else "") +
          (" C123_WSS_DURABLE_SUB_BROKER_PASS" if args.durable_sub_client else "") +
          " P214_REMOTE_OPT_IN_PASS P216_BROWSER_ORIGIN_PASS")


if __name__ == "__main__":
    main()
