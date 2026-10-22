#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Isolated native Windows web console proof; never opens installed state or SCM.

Secrets and child logs stay in a newly created ACL-private test fixture. Only
synthetic loopback MQTT traffic is generated. The JSON report contains no secrets.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import signal
import ssl
import subprocess
import time

from verify_windows_client_admin_runtime import ROOT, digest, free_port, literal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("broker", "client", "admin", "hash-fixture", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-admin-sha256", required=True)
    parser.add_argument("--expected-client-sha256", required=True)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Native Windows required")
    binaries = {name: getattr(args, name).resolve(strict=True) for name in ("broker", "client", "admin")}
    helper = args.hash_fixture.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "purpose": "P252 isolated A28 console interoperability",
              "binary_sha256": {name: digest(path) for name, path in binaries.items()},
              "checks": [], "result": "FAIL", "scm_lifecycle": "NOT_RUN",
              "installed_configuration": "NOT_READ", "msi_installation": "NOT_RUN"}
    children, logs = [], []
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(("MQTT_", "XMQR_"))}

    def record(name):
        report["checks"].append(name)
        print("PASS " + name, flush=True)

    def launch(name, arguments, extra=None):
        log = (private / (name + ".log")).open("wb")
        logs.append(log)
        process = subprocess.Popen([str(binaries[name]), *map(str, arguments)],
                                   env=dict(env, **(extra or {})), stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        children.append(process)
        return process

    def wait_port(process, port):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert process.poll() is None, "Own child exited during startup; private log available"
            try:
                with __import__("socket").create_connection(("127.0.0.1", port), timeout=.2):
                    return
            except OSError:
                time.sleep(.05)
        raise AssertionError("Own loopback listener startup timed out")

    def request(method, path, payload=None, cookie=None, csrf=None):
        headers, body = {}, None
        if cookie:
            headers["Cookie"] = cookie
        if csrf:
            headers["x-xmqr-csrf"] = csrf
        if payload is not None:
            body = json.dumps(payload).encode()
            headers.update({"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{admin_port}"})
        connection = http.client.HTTPConnection("127.0.0.1", admin_port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(65537)
            assert len(raw) <= 65536, "HTTP response exceeded proof bound"
            return response.status, {k.lower(): v for k, v in response.getheaders()}, json.loads(raw) if raw else None
        finally:
            connection.close()

    def poll_snapshot(predicate, label):
        deadline = time.monotonic() + 18
        while time.monotonic() < deadline:
            status, _, snapshot = request("GET", "/api/mqtt", cookie=cookie)
            assert status == 200, "Authenticated console snapshot failed"
            if predicate(snapshot):
                return snapshot
            assert not snapshot.get("error"), label + "; console reported error (private logs available)"
            time.sleep(.1)
        raise AssertionError(label + "; polling timed out")

    try:
        assert report["binary_sha256"]["admin"] == args.expected_admin_sha256.lower(), "A28 Admin binary hash mismatch"
        assert report["binary_sha256"]["client"] == args.expected_client_sha256.lower(), "P248 Client binary hash mismatch"
        record("expected-A28-admin-and-P248-client-binaries")
        private = output / "private"
        subprocess.run(["pwsh", "-NoLogo", "-NoProfile", "-File",
                        str(ROOT / "scripts/windows_test_certificates.ps1"), "-OutputDirectory", str(private)],
                       env=env, check=True, timeout=40, capture_output=True)
        password = secrets.token_hex(32).encode()
        (private / "password").write_bytes(password)
        password_hash = subprocess.run([str(helper)], input=password, env=env, capture_output=True,
                                       check=True, timeout=15).stdout.decode().strip()
        assert password_hash.startswith("$argon2id$"), "Fixture password hashing failed"
        fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert((private / "client.crt").read_text())).hexdigest()
        (private / "users.toml").write_text("[[users]]\nusername='fixture'\ncert_sha256='sha256:"
                                            + fingerprint + "'\npassword_hash='" + password_hash + "'\n", encoding="utf-8")
        topic = "p252/console/" + secrets.token_hex(8)
        (private / "acl.toml").write_text("[[rules]]\nusername='fixture'\npublish=" + json.dumps([topic])
                                          + "\nsubscribe=" + json.dumps([topic]) + "\n", encoding="utf-8")
        (private / "broker-state").mkdir()
        mqtt_port, monitor_port, admin_port = free_port(), free_port(), free_port()
        assert len({mqtt_port, monitor_port, admin_port}) == 3, "Fixture ports collided"
        assert not {mqtt_port, monitor_port, admin_port}.intersection({8883, 9080, 9090}), "Production port excluded"
        broker_config = private / "broker.toml"
        broker_config.write_text('version=1\n[broker]\nmode="secure-mtls"\nbind="127.0.0.1:' + str(mqtt_port)
                                 + '"\nstate_dir="broker-state"\n[tls]\nserver_cert="server.crt"\nserver_key="server.key"'
                                 + '\nclient_ca="ca.crt"\n[security]\nusers_file="users.toml"\nacl_file="acl.toml"'
                                 + '\n[monitor]\nenabled=true\nbind="127.0.0.1:' + str(monitor_port) + '"\n', encoding="utf-8")
        profile = 'version=1\n[connection]\nhost="127.0.0.1"\nport=' + str(mqtt_port) + '\nusername="fixture"\nprotocol_version="3.1.1"\n'
        for name, file in (("ca", "ca.crt"), ("cert", "client.crt"), ("key", "client.key"), ("password_file", "password")):
            profile += name + "=" + literal(private / file) + "\n"
        for name in ("sub", "pub"):
            (private / (name + ".toml")).write_text(profile, encoding="utf-8")
        token_path = private / "token"
        subprocess.run([str(binaries["admin"]), "token-init", "--file", str(token_path)],
                       env=env, capture_output=True, check=True, timeout=15)
        token = token_path.read_text().strip()
        admin_config = private / "admin.toml"
        admin_config.write_text('version=1\nbind="127.0.0.1:' + str(admin_port) + '"\nmonitor="127.0.0.1:'
                                + str(monitor_port) + '"\ntoken_file="token"\nusers_file="web-users.json"\n[mqtt_console]\n'
                                + "client_bin=" + literal(binaries["client"]) + "\nsub_profile=" + literal(private / "sub.toml")
                                + "\npub_profile=" + literal(private / "pub.toml") + '\nlabel="P252 isolated console"\n', encoding="utf-8")
        broker = launch("broker", [], {"MQTT_CONFIG": str(broker_config), "RUST_LOG": "info"})
        wait_port(broker, mqtt_port)
        wait_port(broker, monitor_port)
        admin = launch("admin", ["serve", "--config", admin_config])
        wait_port(admin, admin_port)
        record("private-fixture-mtls-broker-and-A28-admin-loopback-start")
        status, _, _ = request("GET", "/api/mqtt")
        assert status == 401, "Console snapshot allowed unauthenticated access"
        status, _, _ = request("POST", "/api/mqtt/connect", {"topic": topic, "qos": 1})
        assert status in (401, 403), "Console connect allowed unauthenticated access"
        record("console-read-and-write-deny-unauthenticated-requests")
        web_password = secrets.token_hex(24)
        status, _, value = request("GET", "/api/auth/config")
        assert status == 200 and value["setup_required"], "Fresh fixture did not require bootstrap"
        status, headers, value = request("POST", "/api/auth/setup", {"bootstrap_token": token,
                                        "username": "fixture-admin", "display_name": "P252 Test Admin", "password": web_password})
        assert status == 200, "Fixture web bootstrap failed"
        cookie = headers["set-cookie"].split(";", 1)[0]
        csrf = value["csrf_token"]
        status, _, _ = request("POST", "/api/auth/logout", {}, cookie, csrf)
        assert status == 200, "Fixture logout failed"
        status, headers, value = request("POST", "/api/auth/login", {"username": "fixture-admin", "password": web_password})
        assert status == 200, "Fixture cookie login failed"
        cookie, csrf = headers["set-cookie"].split(";", 1)[0], value["csrf_token"]
        record("web-bootstrap-logout-login-with-session-cookie-and-csrf")
        status, _, value = request("GET", "/api/mqtt", cookie=cookie)
        assert status == 200 and value["enabled"], "A28 file configuration did not enable console"
        status, _, _ = request("POST", "/api/mqtt/connect", {"topic": topic, "qos": 1}, cookie)
        assert status == 403, "Authenticated write accepted missing CSRF"
        record("A28-console-enabled-and-cookie-writes-require-csrf")
        status, _, _ = request("POST", "/api/mqtt/connect", {"topic": topic, "qos": 1}, cookie, csrf)
        assert status == 200, "Console subscribe request failed"
        poll_snapshot(lambda snapshot: snapshot["status"] == "connected", "Console mTLS subscription failed")
        record("web-console-connected-mtls-subscription-qos1")
        marker = "synthetic-p252-" + secrets.token_hex(16)
        status, _, _ = request("POST", "/api/mqtt/publish", {"topic": topic, "payload": marker, "qos": 1, "retain": False}, cookie, csrf)
        assert status == 200, "Console QoS1 publish failed"
        snapshot = poll_snapshot(lambda snapshot: any(message.get("topic") == topic and message.get("payload") == marker
                                 and message.get("direction") == "received" for message in snapshot["messages"]),
                                 "Console did not receive synthetic published message")
        assert snapshot["received_total"] >= 1 and snapshot["published_total"] >= 1, "Console counters did not advance"
        record("web-console-publish-qos1-and-receive-identical-synthetic-marker")
        status, _, value = request("POST", "/api/mqtt/disconnect", {}, cookie, csrf)
        assert status == 200 and value["status"] == "disconnected", "Console disconnect failed"
        record("web-console-disconnect")
        for process in reversed(children):
            if process.poll() is None:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            assert process.wait(timeout=20) == 0, "Own child did not stop cooperatively"
        record("own-admin-and-broker-children-stop-cooperatively")
        report["result"] = "PASS"
    except Exception as error:
        # Exception messages here are bounded labels, never captured child output.
        report["error_type"] = type(error).__name__
        report["error"] = str(error) if isinstance(error, AssertionError) else "Operation failed; inspect private fixture logs"
        print("FAIL " + report["error"], flush=True)
    finally:
        for process in reversed(children):
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        for log in logs:
            log.close()
        report["own_children_exited"] = all(process.poll() is not None for process in children)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
