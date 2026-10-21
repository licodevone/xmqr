#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native Windows TLS MQTT/private-output and authenticated admin interoperability.

Only creates private test fixtures and child processes; no SCM/MSI/store changes.
Requires PowerShell 7 and the test-only windows-validation-fixture hash helper.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import threading
import time

from verify_windows_broker_runtime import field, receive, send

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal(path):
    text = str(path)
    if "'" in text:
        raise ValueError("Fixture paths must not contain a single quote")
    return "'" + text + "'"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for component in ("broker", "client", "admin", "hash-fixture", "output"):
        parser.add_argument("--" + component, type=Path, required=True)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Native Windows required")
    binaries = {key: getattr(args, key).resolve(strict=True) for key in ("broker", "client", "admin")}
    helper = args.hash_fixture.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "binary_sha256": {k: digest(v) for k, v in binaries.items()},
              "checks": [], "scm_lifecycle": "NOT_RUN", "msi_installation": "NOT_RUN"}
    children = []
    logs = []
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("MQTT_", "XMQR_"))}

    def record(check):
        report["checks"].append(check)
        print("PASS " + check, flush=True)

    def launch(binary, arguments, name, extra=None):
        log = (output / (name + ".log")).open("wb")
        logs.append(log)
        child = subprocess.Popen([str(binary), *map(str, arguments)], stdout=log, stderr=log,
                                 env=dict(env, **(extra or {})),
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        children.append(child)
        return child

    def wait_port(child, port):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError("Child exited during startup; inspect its log")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    return
            except OSError:
                time.sleep(.05)
        raise RuntimeError("Loopback listener startup deadline expired")

    def stop(child):
        if child.poll() is None:
            child.send_signal(signal.CTRL_BREAK_EVENT)
        assert child.wait(timeout=20) == 0, "Child did not stop cooperatively"

    def client_run(arguments, expected_success=True):
        result = subprocess.run([str(binaries["client"]), *map(str, arguments)], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=35)
        with (output / "client-results.log").open("ab") as log:
            log.write(result.stdout + result.stderr)
        assert (result.returncode == 0) == expected_success, "Unexpected client exit; inspect client-results.log"
        return result

    def request(port, method, path, payload=None, token=None, cookie=None):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if cookie:
            headers["Cookie"] = cookie
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            headers.update({"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"})
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(65537)
            assert len(raw) <= 65536
            return response.status, dict(response.getheaders()), json.loads(raw) if raw else None
        finally:
            connection.close()

    try:
        secrets = output / "private"
        subprocess.run(["pwsh", "-NoLogo", "-NoProfile", "-File", str(ROOT / "scripts/windows_test_certificates.ps1"),
                        "-OutputDirectory", str(secrets)], check=True, timeout=35,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        password = b"P242TestOnly-Password-not-for-production"
        password_path = secrets / "password"
        password_path.write_bytes(password)
        wrong_password = secrets / "wrong-password"
        wrong_password.write_bytes(b"P242-Wrong-Test-Password")
        password_hash = subprocess.run([str(helper)], input=password, capture_output=True, check=True, timeout=15).stdout.decode().strip()
        der = ssl.PEM_cert_to_DER_cert((secrets / "client.crt").read_text(encoding="utf-8"))
        fingerprint = hashlib.sha256(der).hexdigest()
        (secrets / "users.toml").write_text("[[users]]\nusername='fixture'\ncert_sha256='sha256:"
                                          + fingerprint + "'\npassword_hash='" + password_hash + "'\n", encoding="utf-8")
        topics = [f"p242/case-{i}" for i in range(5)]
        (secrets / "acl.toml").write_text("[[rules]]\nusername='fixture'\npublish=" + json.dumps(topics)
                                        + "\nsubscribe=" + json.dumps(topics) + "\n", encoding="utf-8")
        state = secrets / "broker-state"
        state.mkdir()
        mqtt_port, monitor_port, admin_port = free_port(), free_port(), free_port()
        broker_config = secrets / "broker.toml"

        def configure_broker(server):
            broker_config.write_text('version=1\n[broker]\nmode="secure-mtls"\nbind="127.0.0.1:' + str(mqtt_port)
                                     + '"\nstate_dir="broker-state"\n[tls]\nserver_cert="' + server + '.crt"\nserver_key="'
                                     + server + '.key"\nclient_ca="ca.crt"\n[security]\nusers_file="users.toml"\nacl_file="acl.toml"'
                                     + '\n[monitor]\nenabled=true\nbind="127.0.0.1:' + str(monitor_port) + '"\n', encoding="utf-8")
        configure_broker("server")
        broker = launch(binaries["broker"], [], "broker", {"MQTT_CONFIG": str(broker_config), "RUST_LOG": "info"})
        wait_port(broker, mqtt_port)
        wait_port(broker, monitor_port)
        common = ["--host", "127.0.0.1", "--port", str(mqtt_port), "--username", "fixture", "--ca", str(secrets / "ca.crt"),
                  "--cert", str(secrets / "client.crt"), "--key", str(secrets / "client.key"), "--password-file", str(password_path),
                  "--output", "jsonl"]
        for i, (protocol, qos) in enumerate((("3.1.1", "1"), ("3.1.1", "2"), ("5", "1"), ("5", "2"))):
            message = secrets / f"message-{i}"
            payload = f"p242-{protocol}-qos{qos}".encode()
            message.write_bytes(payload)
            client_run(["pub", *common, "--topic", topics[i], "--message-file", str(message), "--qos", qos,
                        "--retain", "true", "--protocol-version", protocol])
            sink = secrets / f"received-{i}.ndjson"
            sink.write_bytes(b"")
            config = secrets / f"client-{i}.toml"
            arguments = ["sub", *common, "--topic", topics[i], "--qos", qos, "--protocol-version", protocol,
                         "--count", "1", "--total-timeout-seconds", "20"]
            config.write_text("version=1\narguments=" + json.dumps(arguments) + "\noutput_file=" + literal(sink)
                              + "\noutput_max_bytes=8388608\n", encoding="utf-8")
            client_run(["--service-config", str(config)])
            rows = [json.loads(line) for line in sink.read_text(encoding="utf-8").splitlines()]
            assert len(rows) == 1 and rows[0]["topic"] == topics[i] and bytes(rows[0]["payload_bytes"]) == payload
            record(f"mtls-{protocol}-qos{qos}-private-service-output")
        pub_config = secrets / "client-pub.toml"
        pub_config.write_text("version=1\narguments=" + json.dumps([
            "pub", *common, "--topic", topics[4], "--message-file", str(secrets / "message-0"),
            "--retain", "true", "--qos", "1"]) + "\n", encoding="utf-8")
        client_run(["--service-config", str(pub_config)])
        background_sink = secrets / "background.ndjson"
        background_sink.write_bytes(b"")
        background_config = secrets / "client-background.toml"
        background_config.write_text("version=1\narguments=" + json.dumps([
            "sub", *common, "--topic", topics[4], "--qos", "1", "--total-timeout-seconds", "30"])
            + "\noutput_file=" + literal(background_sink) + "\n", encoding="utf-8")
        subscriber = launch(binaries["client"], ["--service-config", background_config], "client-background")
        deadline = time.monotonic() + 10
        while background_sink.stat().st_size == 0:
            assert subscriber.poll() is None, "Background subscriber exited before persisting a message"
            if time.monotonic() >= deadline:
                raise RuntimeError("Background subscriber output deadline")
            time.sleep(.05)
        stop(subscriber)
        assert bytes(json.loads(background_sink.read_text(encoding="utf-8").splitlines()[0])["payload_bytes"]) == (secrets / "message-0").read_bytes()
        record("service-config-publisher-and-background-subscriber-graceful-stop")
        full_sink = secrets / "capacity.ndjson"
        full_sink.write_bytes(b" " * 4094 + b"\n")
        full_config = secrets / "client-capacity.toml"
        full_config.write_text("version=1\narguments=" + json.dumps([
            "sub", *common, "--topic", topics[4], "--qos", "1", "--count", "1", "--total-timeout-seconds", "20"])
            + "\noutput_file=" + literal(full_sink) + "\noutput_max_bytes=4096\n", encoding="utf-8")
        before = full_sink.read_bytes()
        client_run(["--service-config", str(full_config)], False)
        assert full_sink.read_bytes() == before, "Full output must not truncate existing records"
        record("full-private-output-refuses-new-record-without-truncating")
        # A controlled mTLS peer verifies the negative at the wire boundary:
        # the message reached the subscriber, but a full sink must not PUBACK.
        peer = socket.socket()
        peer.bind(("127.0.0.1", 0))
        peer.listen(1)
        peer.settimeout(10)
        wire_port = peer.getsockname()[1]
        observed = {"publish_sent": False, "acks": [], "error": None}
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(secrets / "server.crt", secrets / "server.key")
        server_context.load_verify_locations(secrets / "ca.crt")
        server_context.verify_mode = ssl.CERT_REQUIRED

        def wire_peer():
            try:
                raw, _ = peer.accept()
                raw.settimeout(8)
                with server_context.wrap_socket(raw, server_side=True) as stream:
                    assert receive(stream)[0] == 0x10
                    send(stream, 0x20, b"\x00\x00")
                    header, body = receive(stream)
                    assert header == 0x82
                    send(stream, 0x90, body[:2] + b"\x01")
                    send(stream, 0x32, field(topics[4].encode()) + b"\x01\x01" + b"must-not-ack-full-output")
                    observed["publish_sent"] = True
                    while True:
                        try:
                            header, _ = receive(stream)
                        except (OSError, RuntimeError):
                            break
                        if header >> 4 in (4, 5):
                            observed["acks"].append(header)
            except Exception as error:
                observed["error"] = type(error).__name__ + ": " + str(error)
            finally:
                peer.close()

        wire_args = ["sub", *common, "--topic", topics[4], "--qos", "1", "--count", "1", "--total-timeout-seconds", "20"]
        wire_args[wire_args.index("--port") + 1] = str(wire_port)
        full_config.write_text("version=1\narguments=" + json.dumps(wire_args) + "\noutput_file=" + literal(full_sink)
                               + "\noutput_max_bytes=4096\n", encoding="utf-8")
        worker = threading.Thread(target=wire_peer, daemon=True)
        worker.start()
        client_run(["--service-config", str(full_config)], False)
        worker.join(timeout=12)
        assert not worker.is_alive() and not observed["error"], observed
        assert observed["publish_sent"] and not observed["acks"], observed
        assert full_sink.read_bytes() == before
        record("wire-mtls-qos1-full-output-no-puback")
        negative_args = ["pub", *common, "--topic", topics[0], "--message-file", str(secrets / "message-0"), "--qos", "1"]
        bad = list(negative_args)
        bad[bad.index("--password-file") + 1] = str(wrong_password)
        client_run(bad, False)
        record("wrong-password-rejected")
        bad = list(negative_args)
        bad[bad.index("--ca") + 1] = str(secrets / "client.crt")
        client_run(bad, False)
        record("untrusted-ca-rejected")

        token_path = secrets / "token"
        subprocess.run([str(binaries["admin"]), "token-init", "--file", str(token_path)], check=True,
                       env=env, capture_output=True, timeout=10)
        token = token_path.read_text(encoding="utf-8").strip()
        admin_config = secrets / "admin.toml"
        base_admin = 'version=1\nbind="127.0.0.1:' + str(admin_port) + '"\nmonitor="127.0.0.1:' + str(monitor_port) + '"\ntoken_file="token"\n'
        admin_config.write_text(base_admin, encoding="utf-8")
        admin = launch(binaries["admin"], ["serve", "--config", admin_config], "admin-token")
        wait_port(admin, admin_port)
        assert request(admin_port, "GET", "/api/status")[0] == 401
        assert request(admin_port, "GET", "/api/status", token="0" * 64)[0] == 401
        code, _, value = request(admin_port, "GET", "/api/status", token=token)
        assert code == 200 and value["reachable"] and value["ready"]
        stop(admin)
        record("admin-private-token-authenticated-broker-status")
        admin_config.write_text(base_admin + 'users_file="web-users.json"\n', encoding="utf-8")
        admin = launch(binaries["admin"], ["serve", "--config", admin_config], "admin-users")
        wait_port(admin, admin_port)
        assert request(admin_port, "GET", "/api/auth/config")[2]["setup_required"]
        web_password = "P242-Only-Local-Test-Password"
        code, headers, _ = request(admin_port, "POST", "/api/auth/setup", {
            "bootstrap_token": token, "username": "fixture-admin", "display_name": "P242 Test Admin", "password": web_password})
        assert code == 200
        cookie = headers["set-cookie"].split(";", 1)[0]
        assert request(admin_port, "GET", "/api/status", cookie=cookie)[0] == 200
        assert request(admin_port, "POST", "/api/auth/login", {"username": "fixture-admin", "password": "wrong-password"})[0] == 401
        stop(admin)
        admin = launch(binaries["admin"], ["serve", "--config", admin_config], "admin-users-restart")
        wait_port(admin, admin_port)
        assert not request(admin_port, "GET", "/api/auth/config")[2]["setup_required"]
        code, headers, _ = request(admin_port, "POST", "/api/auth/login", {"username": "fixture-admin", "password": web_password})
        assert code == 200
        assert request(admin_port, "GET", "/api/status", cookie=headers["set-cookie"].split(";", 1)[0])[0] == 200
        stop(admin)
        record("admin-web-bootstrap-login-private-users-persist-after-restart")
        stop(broker)
        configure_broker("wrong-server")
        broker = launch(binaries["broker"], [], "broker-wrong-san", {"MQTT_CONFIG": str(broker_config)})
        wait_port(broker, mqtt_port)
        client_run(negative_args, False)
        stop(broker)
        record("wrong-server-san-rejected")
        report["result"] = "PASS"
    except Exception as error:
        report.update(result="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.kill()  # Bounded cleanup of this runner's own child only.
                child.wait(timeout=5)
        for log in logs:
            log.close()
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
