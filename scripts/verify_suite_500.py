# SPDX-License-Identifier: MIT
"""Isolated Broker + Client + Admin smoke at 500 or 1000 MQTT connections."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from benchmark_pressure import Broker, Client, disconnect, f, unused_port, wait_for

TOPIC = "p272/suite"
PAYLOAD = b"p272-qos1-at-capacity"


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def require_running(process, label):
    if process.poll() is not None:
        raise AssertionError(f"{label} exited before its readiness check: {process.returncode}")


def check_saturation(broker):
    metric = 'xmqr_rejections_total{reason="admission"}'
    before = broker.metrics().get(metric, 0)
    with socket.create_connection(("127.0.0.1", broker.port), timeout=5) as extra:
        try:
            if extra.recv(1) != b"":
                raise AssertionError("broker left the excess MQTT socket open")
        except ConnectionResetError:
            pass
    wait_for(lambda: broker.metrics().get(metric, 0) == before + 1)


def run(args, root):
    limit = args.connections
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("MQTT_", "XMQR_ADMIN_"))}
    env["RUST_LOG"] = "warn"
    opener = build_opener(ProxyHandler({}))

    with ExitStack() as stack:
        broker = Broker(root, args.broker, None, connections=limit)
        stack.callback(broker.shutdown)
        broker.start()

        port = unused_port()
        token = secrets.token_hex(32)
        token_file = root / "web.token"
        token_file.touch(mode=0o600, exist_ok=False)
        token_file.write_text(token, encoding="ascii")
        admin = subprocess.Popen(
            [str(args.admin), "serve"],
            env=dict(env, XMQR_ADMIN_BIND=f"127.0.0.1:{port}",
                     XMQR_ADMIN_MONITOR_BIND=f"127.0.0.1:{broker.monitor}",
                     XMQR_ADMIN_TOKEN_FILE=str(token_file)),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        stack.callback(stop, admin)
        url = f"http://127.0.0.1:{port}/api/status"
        authorized = Request(url, headers={"Authorization": f"Bearer {token}"})

        def admin_ready():
            require_running(admin, "Admin")
            try:
                with opener.open(authorized, timeout=5) as response:
                    return json.load(response)["ready"] is True
            except (OSError, ValueError):
                return False

        wait_for(admin_ready)
        try:
            with opener.open(url, timeout=5):
                raise AssertionError("Admin status exposed without authentication")
        except HTTPError as error:
            with error:
                if error.code != 401:
                    raise

        clients = []
        for index in range(limit - 1):
            client = Client(broker, f"p272-{index:03}", keepalive=0)
            stack.callback(disconnect, client)
            clients.append(client)

        client_log = root / "subscriber.log"
        with client_log.open("wb") as stderr:
            subscriber = subprocess.Popen(
                [str(args.client), "sub", "--open-lab", "--host", "127.0.0.1",
                 "--port", str(broker.port), "--topic", TOPIC, "--qos", "1",
                 "--client-id", "p272-subscriber", "--clean-session", "true",
                 "--count", "1", "--output", "raw", "--total-timeout-seconds", "30"],
                env=env, stdout=subprocess.PIPE, stderr=stderr,
            )
        stack.callback(subscriber.stdout.close)
        stack.callback(stop, subscriber)

        def subscribed():
            require_running(subscriber, "Client")
            return b"Assinatura ativa." in client_log.read_bytes()

        wait_for(subscribed)
        check_saturation(broker)
        with opener.open(authorized, timeout=5) as response:
            status = json.load(response)
        metrics = status["metrics"]
        if not (status["ready"] and metrics["xmqr_connections_active"] == limit
                and metrics["xmqr_sessions"] == limit):
            raise AssertionError(f"Admin did not observe a ready broker with {limit} sessions")

        publisher = clients[0]
        publisher.send(0x32, f.text(TOPIC) + b"\0\1" + PAYLOAD)
        if publisher.receive() != (0x40, b"\0\1"):
            raise AssertionError("publisher did not receive QoS 1 PUBACK")
        delivered, _ = subscriber.communicate(timeout=10)
        if subscriber.returncode != 0 or delivered != PAYLOAD:
            raise AssertionError("Client did not deliver the exact publication")
        wait_for(lambda: broker.metrics()["xmqr_connections_active"] == limit - 1)
        with Client(broker, "p272-replacement") as replacement:
            replacement.ping()
            wait_for(lambda: broker.metrics()["xmqr_connections_active"] == limit)

    return {"mqtt_connections": limit, "admin_connections": metrics["xmqr_connections_active"],
            "admin_sessions": metrics["xmqr_sessions"], "admin_anonymous_denied": True,
            "excess_denied": True, "qos1_delivery": True, "slot_reused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connections", type=int, choices=(500, 1000), default=500)
    for name in ("broker", "client", "admin", "state-root"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux" or not args.state_root.is_dir():
        parser.error("Linux and an existing native state-root are required")
    binaries = {}
    for name in ("broker", "client", "admin"):
        binary = getattr(args, name).resolve(strict=True)
        if not binary.is_file() or not os.access(binary, os.X_OK):
            parser.error(f"{name} executable required")
        setattr(args, name, binary)
        binaries[name] = {
            "version": subprocess.check_output([binary, "--version"], text=True, timeout=5).strip(),
            "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        }
    with tempfile.TemporaryDirectory(prefix="xmqr-p272-", dir=args.state_root) as directory:
        evidence = run(args, Path(directory).resolve(strict=True))
    print(json.dumps({"status": "PASS", "profile": "open-lab", "binaries": binaries, **evidence}))


if __name__ == "__main__":
    main()
