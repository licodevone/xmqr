#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P135: ESP32 QoS1 telemetry -> XMQR broker + subscriber in Ubuntu/WSL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import select
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import tomllib

TOPIC = "xmqr/teste/ambiente"
HOST = "192.168.0.100"
HOST_PORT = 28883
BROKER_PORT = 8883
REPO = Path(__file__).resolve().parents[2]
BROKER = REPO / "target/release/mqtt-broker"
CLIENT = REPO.parent / "xmqr-client/target/release/mqtt-client"


def wsl_path(path):
    resolved = Path(path).resolve(strict=True)
    return "/mnt/" + resolved.drive[0].lower() + resolved.as_posix()[2:]


def wsl(*args, **kwargs):
    return subprocess.run(["wsl", "-d", "Ubuntu-26.04", "--", *map(str, args)],
                          capture_output=True, timeout=20, **kwargs)


def prepare_wsl(private_dir):
    private = Path(private_dir).resolve(strict=True)
    case = json.loads((private / "p85-case.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"p85-case-[a-f0-9]{32}", case["case_directory"])
    base = (private / case["case_directory"]).resolve(strict=True)
    assert base.parent == private
    root = Path(tempfile.mkdtemp(prefix="xmqr-p135-", dir="/tmp"))
    os.chmod(root, 0o700)
    try:
        ca = private / "certs"
        validity = subprocess.run(["openssl", "x509", "-in", str(ca / "ca.crt"),
                                   "-noout", "-checkend", "3600"], capture_output=True)
        if validity.returncode:
            raise ValueError("laboratory CA expired or near expiry")
        for source, target in [
            (ca / "ca.crt", "ca.crt"),
            (base / "normal/users.toml", "users.toml"),
        ]:
            shutil.copyfile(source, root / target)
            (root / target).chmod(0o600)
        for name, purpose, san in (("server", "serverAuth", f"subjectAltName=IP:{HOST}\n"),
                                   ("observer", "clientAuth", "")):
            extension = root / f"{name}.ext"
            extension.write_text("basicConstraints=critical,CA:FALSE\n"
                                 "keyUsage=critical,digitalSignature,keyEncipherment\n"
                                 f"extendedKeyUsage={purpose}\n{san}", encoding="ascii")
            commands = [
                ["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-sha256",
                 "-subj", f"/CN=XMQR P135 {name}", "-keyout", str(root / f"{name}.key"),
                 "-out", str(root / f"{name}.csr")],
                ["openssl", "x509", "-req", "-in", str(root / f"{name}.csr"),
                 "-CA", str(ca / "ca.crt"), "-CAkey", str(ca / "ca.key"),
                 "-set_serial", str(secrets.randbits(128)), "-days", "1", "-sha256",
                 "-extfile", str(extension), "-out", str(root / f"{name}.crt")],
            ]
            for command in commands:
                if subprocess.run(command, capture_output=True, timeout=30).returncode:
                    raise ValueError("temporary lab certificate renewal failed")
            (root / f"{name}.key").chmod(0o600)
            (root / f"{name}.crt").chmod(0o600)
        users = tomllib.loads((root / "users.toml").read_text(encoding="ascii"))
        if not any(user.get("username") == "e01-board" for user in users["users"]):
            raise ValueError("board identity missing")
        if not any(user.get("username") == "e01-observer" for user in users["users"]):
            raise ValueError("observer identity missing")
        fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
            (root / "observer.crt").read_text(encoding="ascii"))).hexdigest()
        original = (root / "users.toml").read_text(encoding="ascii")
        blocks = original.split("[[users]]")
        for index, block in enumerate(blocks):
            if re.search(r'(?m)^username="e01-observer"$', block):
                blocks[index], count = re.subn(r'(?m)^cert_sha256="sha256:[a-f0-9]{64}"$',
                                               f'cert_sha256="sha256:{fingerprint}"', block)
                if count != 1:
                    raise ValueError("observer fingerprint update failed")
        (root / "users.toml").write_text("[[users]]".join(blocks), encoding="ascii")
        (root / "acl.toml").write_text(
            '[[rules]]\nusername="e01-board"\npublish=["xmqr/teste/ambiente"]\n'
            '[[rules]]\nusername="e01-observer"\nsubscribe=["xmqr/teste/ambiente"]\n',
            encoding="ascii")
        (root / "acl.toml").chmod(0o600)
        (root / "observer-password").write_text(case["password"] + "\n", encoding="utf-8")
        (root / "observer-password").chmod(0o600)
        (root / "state").mkdir(mode=0o700)
        print(root)
    except Exception:
        shutil.rmtree(root)
        raise


def cleanup_wsl(raw):
    root = Path(raw).resolve(strict=True)
    if root.parent != Path("/tmp") or not re.fullmatch(r"xmqr-p135-[A-Za-z0-9_]+", root.name):
        raise ValueError("unexpected WSL test directory")
    shutil.rmtree(root)


class Relay(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = True


class RelayHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with socket.create_connection(self.server.upstream, timeout=5) as upstream:
                sockets = (self.request, upstream)
                while True:
                    ready, _, _ = select.select(sockets, [], [], 180)
                    if not ready:
                        return
                    for source in ready:
                        data = source.recv(4096)
                        if not data:
                            return
                        (upstream if source is self.request else self.request).sendall(data)
        except OSError:
            return


def read_lines(stream, events, kind):
    for line in iter(stream.readline, b""):
        if kind == "stdout":
            try:
                sample = sample_from_line(line)
                print(f"P135_SUB_RECEIVED seq={sample['seq']} "
                      f"temperature_c={sample['temperature_c']:.1f} "
                      f"humidity_pct={sample['humidity_pct']:.1f} "
                      f"source=simulated", flush=True)
            except (ValueError, KeyError, TypeError, UnicodeError):
                pass
        events.put((kind, line[:1024]))


def checked_backups(directory):
    names = ["firmware-original-20261013-esptool.bin", "firmware-original-20261013-verify.bin"]
    paths = [Path(directory) / name for name in names]
    if not all(path.is_file() and path.stat().st_size == 4194304 for path in paths):
        raise ValueError("two complete 4 MiB backups required")
    digest = lambda path: hashlib.sha256(path.read_bytes()).digest()
    if digest(paths[0]) != digest(paths[1]):
        raise ValueError("original flash backups do not match")


def command(args, timeout=30):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError("physical test prerequisite failed (private diagnostics suppressed)")
    return result.stdout


def flash(port, private, temporary):
    info = command([sys.executable, "-m", "esptool", "--chip", "esp32", "--port", port,
                    "flash_id"])
    if b"ESP32-D0WD-V3" not in info or b"4MB" not in info:
        raise ValueError("COM4 does not match backed-up ESP32")
    firmware = private / "target/xtensa-esp32-espidf/release/xmqr-esp32-e01"
    sdk = list((private / "target/xtensa-esp32-espidf/release/build").glob("esp-idf-sys-*/out/build"))
    if not firmware.is_file() or len(sdk) != 1:
        raise ValueError("unambiguous telemetry build artifacts required")
    app = temporary / "p135-app.bin"
    command([sys.executable, "-m", "esptool", "--chip", "esp32", "elf2image",
             "--flash_mode", "dio", "--flash_freq", "40m", "--flash_size", "4MB",
             "--elf-sha256-offset", "0xb0", "--output", str(app), str(firmware)], timeout=60)
    if app.stat().st_size > 1048576:
        raise ValueError("telemetry app exceeds factory partition")
    command([sys.executable, "-m", "esptool", "--chip", "esp32", "--port", port,
             "--baud", "115200", "write_flash", "--flash_mode", "dio",
             "--flash_freq", "40m", "--flash_size", "4MB",
             "0x1000", str(sdk[0] / "bootloader/bootloader.bin"),
             "0x8000", str(sdk[0] / "partition_table/partition-table.bin"),
             "0x10000", str(app)], timeout=240)
    print("P135_FLASH_VERIFIED", flush=True)


def serial_markers(port):
    import serial
    expected = (["P135_BOOT fixture=0.1.0 source=simulated", "P135_MTLS_CONNECTED"]
                + [f"P135_PUBACK seq={index}" for index in range(1, 6)]
                + ["P135_PUBLISH_PASS count=5 source=simulated", "P135_STOP"])
    seen = []
    total = 0
    with serial.Serial(port, 115200, timeout=.2) as uart:
        uart.dtr = False
        uart.rts = True
        time.sleep(.1)
        uart.rts = False
        deadline = time.monotonic() + 130
        while time.monotonic() < deadline and len(seen) < len(expected):
            raw = uart.readline()
            total += len(raw)
            if total > 65536 or len(raw) > 512:
                raise ValueError("serial transcript budget exceeded")
            try:
                line = raw.decode("ascii").strip()
            except UnicodeDecodeError:
                continue
            if re.fullmatch(r"P135_FAIL stage=[A-Z0-9_]{1,40}", line):
                raise ValueError(line)
            if line == expected[len(seen)]:
                seen.append(line)
                print(line, flush=True)
    if seen != expected:
        raise ValueError("incomplete ESP32 telemetry transcript")


def sample_from_line(raw):
    envelope = json.loads(raw)
    payload = json.loads(bytes(envelope["payload_bytes"]))
    if (envelope["event"] != "publish" or envelope["topic"] != TOPIC
            or envelope["qos"] != 1 or envelope["retain"]
            or payload["source"] != "simulated"
            or type(payload["run_id"]) is not int
            or not 0 <= payload["run_id"] < 2**32
            or type(payload["seq"]) is not int
            or type(payload["temperature_c"]) not in (int, float)
            or type(payload["humidity_pct"]) not in (int, float)
            or not 20.0 <= payload["temperature_c"] < 30.0
            or not 40.0 <= payload["humidity_pct"] < 70.0):
        raise ValueError("invalid simulated telemetry")
    return payload


def verify_messages(lines):
    if len(lines) != 5:
        raise ValueError(f"subscriber received {len(lines)} of 5 messages")
    run_id = None
    values = set()
    for index, raw in enumerate(lines):
        payload = sample_from_line(raw)
        if payload["seq"] != index + 1 or (run_id is not None and payload["run_id"] != run_id):
            raise ValueError("subscriber message/topic/sequence mismatch")
        run_id = payload["run_id"]
        values.add((payload["temperature_c"], payload["humidity_pct"]))
    if len(values) < 2:
        raise ValueError("telemetry values did not vary")


def exercise(args):
    private = args.private_dir.resolve(strict=True)
    if private.is_relative_to(REPO) or args.serial_port != "COM4":
        raise ValueError("private laboratory and COM4 required")
    checked_backups(args.backup_dir.resolve(strict=True))
    config = json.loads((private / "firmware-config.json").read_text(encoding="utf-8"))
    if config["mqtt_url"] != f"mqtts://{HOST}:{HOST_PORT}":
        raise ValueError("firmware target differs from isolated bridge")
    if not BROKER.is_file() or not CLIENT.is_file():
        raise ValueError("build broker and client in WSL before the physical test")
    setup = wsl("python3", wsl_path(Path(__file__)), "--prepare-wsl",
                "--private-dir", wsl_path(private))
    if setup.returncode:
        raise ValueError("private WSL fixture setup failed")
    lab = setup.stdout.decode().strip()
    broker = subscriber = relay = relay_thread = None
    try:
        ip_result = wsl("hostname", "-I")
        if ip_result.returncode:
            raise ValueError("WSL address unavailable")
        ip = next((value for value in ip_result.stdout.decode().split()
                   if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", value)), None)
        if ip is None:
            raise ValueError("WSL IPv4 address unavailable")
        paths = {name: f"{lab}/{name}" for name in ("server.crt", "server.key", "ca.crt",
                                                       "users.toml", "acl.toml", "state")}
        env = ["MQTT_MODE=secure-mtls", f"MQTT_BIND=0.0.0.0:{BROKER_PORT}",
               f"MQTT_STATE_DIR={paths['state']}", f"MQTT_SERVER_CERT={paths['server.crt']}",
               f"MQTT_SERVER_KEY={paths['server.key']}", f"MQTT_CLIENT_CA={paths['ca.crt']}",
               f"MQTT_USERS_FILE={paths['users.toml']}", f"MQTT_ACL_FILE={paths['acl.toml']}",
               "RUST_LOG=error"]
        broker = subprocess.Popen(["wsl", "-d", "Ubuntu-26.04", "--", "env", *env,
                                   wsl_path(BROKER)], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if broker.poll() is not None:
                raise ValueError("isolated broker exited during startup")
            try:
                with socket.create_connection((ip, BROKER_PORT), timeout=.3):
                    break
            except OSError:
                time.sleep(.2)
        else:
            raise ValueError("isolated WSL broker did not listen")
        relay = Relay((HOST, HOST_PORT), RelayHandler)
        relay.upstream = (ip, BROKER_PORT)
        relay_thread = threading.Thread(target=relay.serve_forever, daemon=True)
        relay_thread.start()
        context = ssl.create_default_context(cafile=str(private / "certs/ca.crt"))
        context.load_cert_chain(str(private / "certs/board.crt"), str(private / "certs/board.key"))
        with socket.create_connection((HOST, HOST_PORT), timeout=3) as stream:
            with context.wrap_socket(stream, server_hostname=HOST):
                pass
        print("P135_WSL_BROKER_MTLS_READY", flush=True)
        command_line = ["wsl", "-d", "Ubuntu-26.04", "--", wsl_path(CLIENT), "sub",
                        "--host", HOST, "--port", str(HOST_PORT), "--topic", TOPIC,
                        "--qos", "1", "--count", "5", "--output", "jsonl",
                        "--username", "e01-observer", "--password-file", f"{lab}/observer-password",
                        "--ca", paths["ca.crt"], "--cert", f"{lab}/observer.crt",
                        "--key", f"{lab}/observer.key", "--client-id", "p135-wsl-subscriber"]
        subscriber = subprocess.Popen(command_line, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        events = queue.Queue()
        readers = []
        for kind, stream in (("stdout", subscriber.stdout), ("stderr", subscriber.stderr)):
            reader = threading.Thread(target=read_lines, args=(stream, events, kind), daemon=True)
            reader.start()
            readers.append(reader)
        deadline = time.monotonic() + 12
        lines = []
        while time.monotonic() < deadline:
            if subscriber.poll() is not None:
                raise ValueError("subscriber exited before SUBACK")
            try:
                kind, line = events.get(timeout=.3)
            except queue.Empty:
                continue
            if kind == "stdout":
                lines.append(line)
            elif b"Assinatura ativa" in line:
                print("P135_WSL_SUBSCRIBED", flush=True)
                break
        else:
            raise ValueError("subscriber did not confirm SUBACK")
        if args.preflight:
            print("P135_PREFLIGHT_PASS", flush=True)
            return
        if args.flash:
            with tempfile.TemporaryDirectory(prefix="p135-flash-", dir=private) as temporary:
                flash(args.serial_port, private, Path(temporary))
        serial_markers(args.serial_port)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline and (subscriber.poll() is None or not events.empty()):
            try:
                kind, line = events.get(timeout=.2)
            except queue.Empty:
                continue
            if kind == "stdout":
                lines.append(line)
        if subscriber.poll() is None:
            raise ValueError("subscriber did not finish after five messages")
        if subscriber.returncode != 0:
            raise ValueError("subscriber exited with error")
        for reader in readers:
            reader.join(timeout=2)
        while not events.empty():
            kind, line = events.get_nowait()
            if kind == "stdout":
                lines.append(line)
        print(f"P135_SUB_CAPTURED count={len(lines)}", flush=True)
        verify_messages(lines)
        print("P135_PASS_PHYSICAL_WSL_TELEMETRY", flush=True)
    finally:
        if subscriber is not None and subscriber.poll() is None:
            subscriber.kill()
            subscriber.wait(timeout=5)
        if relay is not None:
            relay.shutdown()
            relay.server_close()
            relay_thread.join(timeout=3)
        if broker is not None and broker.poll() is None:
            broker.terminate()
            try:
                broker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                broker.kill()
                broker.wait(timeout=5)
        clean = wsl("python3", wsl_path(Path(__file__)), "--cleanup-wsl", lab)
        if clean.returncode:
            print("P135_CLEANUP_FAILED", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--serial-port", default="COM4")
    parser.add_argument("--flash", action="store_true")
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--prepare-wsl", action="store_true")
    parser.add_argument("--cleanup-wsl")
    args = parser.parse_args()
    try:
        if args.prepare_wsl:
            prepare_wsl(args.private_dir)
        elif args.cleanup_wsl:
            cleanup_wsl(args.cleanup_wsl)
        elif sum((args.flash, args.observe, args.preflight)) == 1 and args.private_dir and args.backup_dir:
            exercise(args)
        else:
            parser.error("select --flash, --observe or --preflight with private and backup directories")
    except Exception as error:
        message = str(error)
        if not re.fullmatch(r"P135_FAIL stage=[A-Z0-9_]{1,40}", message):
            message = "P135_FAIL (private details suppressed)"
        print(message, file=sys.stderr, flush=True)
        sys.exit(1)
