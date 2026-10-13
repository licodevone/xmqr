#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Explicit first physical slice. Requires matching private backups before flash."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import time

import serial

REPO = Path(__file__).resolve().parents[2]
BROKER_IMAGE = "lepinheiro100/xmqr-broker:0.11.4@sha256:379439bd82f03c6c237d1e1f2f9a452e20fa62e24538200b97a06af6dae394bd"
NAME = "xmqr-e01-p81-20261013"
VOLUME = NAME + "-state"


def command(args, timeout=60):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("test operation failed (private diagnostics suppressed)")
    return result.stdout


def verified_backups(directory):
    files = [directory / "firmware-original-20261013-esptool.bin",
             directory / "firmware-original-20261013-verify.bin"]
    if not all(p.is_file() and p.stat().st_size == 4194304 for p in files):
        raise ValueError("two full 4MiB backups required")
    digests = [hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
    if digests[0] != digests[1]:
        raise ValueError("backup mismatch: refusing flash")
    return digests[0]


def source_digest():
    digest = hashlib.sha256()
    root = Path(__file__).resolve().parent
    for relative in ["Cargo.toml", "Cargo.lock", "build.rs", "src/main.rs", "sdkconfig.defaults", ".cargo/config.toml"]:
        digest.update(relative.encode())
        digest.update((root / relative).read_bytes())
    return digest.hexdigest()


def exercise(args):
    root = args.private_dir.resolve(strict=True)
    backup_dir = args.backup_dir.resolve(strict=True)
    if root.is_relative_to(REPO) or backup_dir.is_relative_to(REPO):
        raise ValueError("private directories must stay outside Git")
    backup_sha = verified_backups(backup_dir)
    firmware = root / "target/xtensa-esp32-espidf/release/xmqr-esp32-e01"
    if not firmware.is_file():
        raise ValueError("compiled firmware required")
    config = json.loads((root / "firmware-config.json").read_text(encoding="utf-8"))
    from urllib.parse import urlparse
    url = urlparse(config["mqtt_url"])
    if url.scheme != "mqtts" or url.username or url.password:
        raise ValueError("mTLS endpoint required")
    host, port = url.hostname, url.port
    with socket.socket() as probe:
        probe.bind((host, port))
    for resource in [NAME, VOLUME]:
        kind = "container" if resource == NAME else "volume"
        exists = subprocess.run(["docker", kind, "inspect", resource], capture_output=True)
        if exists.returncode == 0:
            raise ValueError("refusing existing lab resource")
    certs = root / "certs"
    report = {"schema": 1, "prompt": "P81", "started_utc": datetime.now(timezone.utc).isoformat(),
              "broker": "0.11.4", "fixture": "0.1.0", "port": args.serial_port,
              "source_sha256": source_digest(), "backup_sha256": backup_sha,
              "backup_bytes": 4194304, "markers": [], "phase2_closed": False,
              "result": "FAIL_PRECHECK", "flashed": False,
              "remaining": ["retained", "Will", "reconnection", "physical negatives", "heap", "independent observer"]}
    volume_created = False
    container_created = False
    try:
        command(["docker", "volume", "create", VOLUME])
        volume_created = True
        command(["docker", "run", "--rm", "--user", "0:0", "--network", "none",
                 "--mount", f"type=volume,source={VOLUME},target=/var/lib/xmqr",
                 "--entrypoint", "/bin/sh", BROKER_IMAGE, "-c", "chown 10001:10001 /var/lib/xmqr"])
        command(["docker", "create", "--name", NAME, "--read-only", "--cap-drop", "ALL",
                 "--security-opt", "no-new-privileges", "--pids-limit", "64", "--memory", "256m",
                 "--publish", f"{host}:{port}:8883",
                 "--mount", f"type=bind,source={certs},target=/run/e01,readonly",
                 "--mount", f"type=volume,source={VOLUME},target=/var/lib/xmqr",
                 "--env", "MQTT_SERVER_CERT=/run/e01/server.crt",
                 "--env", "MQTT_SERVER_KEY=/run/e01/server.key",
                 "--env", "MQTT_CLIENT_CA=/run/e01/ca.crt",
                 "--env", "MQTT_USERS_FILE=/run/e01/users.toml",
                 "--env", "MQTT_ACL_FILE=/run/e01/acl.toml",
                 "--env", "MQTT_MAX_CONNECTIONS=8", "--env", "RUST_LOG=error", BROKER_IMAGE])
        container_created = True
        command(["docker", "start", NAME])
        context = ssl.create_default_context(cafile=str(certs / "ca.crt"))
        context.load_cert_chain(certs / "board.crt", certs / "board.key")
        until = time.monotonic() + 15
        ready = False
        while time.monotonic() < until:
            try:
                with socket.create_connection((host, port), timeout=1) as tcp:
                    with context.wrap_socket(tcp, server_hostname=host):
                        ready = True
                        break
            except (OSError, ssl.SSLError):
                time.sleep(.2)
        if not ready:
            raise RuntimeError("test mTLS broker not ready: refusing flash")
        print("E01_HOST_MTLS_READY", flush=True)
        if not args.flash:
            report["result"] = "HOST_PRECHECK_ONLY"
            return report
        outputs = list((root / "target/xtensa-esp32-espidf/release/build").glob("esp-idf-sys-*/out"))
        candidates = [p for p in outputs if (p / "build/bootloader/bootloader.bin").is_file()]
        if len(candidates) != 1:
            raise ValueError("ambiguous SDK bootloader")
        sdk = candidates[0]
        # Convert ELF only; flash the actual SDK partition table/bootloader, not defaults.
        app_bin = root / "e01-app.bin"
        command([sys.executable, "-m", "esptool", "--chip", "esp32", "elf2image",
                 "--flash_mode", "dio", "--flash_freq", "40m", "--flash_size", "4MB",
                 "--elf-sha256-offset", "0xb0", "--output", str(app_bin), str(firmware)])
        if app_bin.stat().st_size > 1048576:
            raise ValueError("app exceeds configured factory partition: refusing flash")
        command([sys.executable, "-m", "esptool", "--chip", "esp32", "--port", args.serial_port,
                 "--baud", "115200", "write_flash", "--flash_mode", "dio", "--flash_freq", "40m",
                 "--flash_size", "4MB", "0x1000", str(sdk / "build/bootloader/bootloader.bin"),
                 "0x8000", str(sdk / "build/partition_table/partition-table.bin"),
                 "0x10000", str(app_bin)], timeout=240)
        report["flashed"] = True
        print("E01_FLASH_VERIFIED", flush=True)
        with serial.Serial(args.serial_port, 115200, timeout=.2) as uart:
            # Reset normally after opening; do not leave the board in ROM download mode.
            uart.dtr = False
            uart.rts = True
            time.sleep(.1)
            uart.rts = False
            until = time.monotonic() + 180
            while time.monotonic() < until:
                line = uart.readline(512).decode("ascii", errors="ignore").strip()
                if re.fullmatch(r"E01_[A-Z_]+(?: [A-Za-z0-9_= .-]+)?", line):
                    report["markers"].append(line)
                    print(line, flush=True)
                    if line == "E01_STOP":
                        break
        required = ["E01_WIFI_UP", "E01_SNTP_SYNC", "E01_MTLS_CONNECTED",
                    *(f"E01_LOOPBACK_PASS qos={q} bytes=1024" for q in range(3)),
                    "E01_INITIAL_SLICE_PASS", "E01_STOP"]
        report["result"] = "PASS_INITIAL_SLICE" if all(x in report["markers"] for x in required) else "FAIL_INITIAL_SLICE"
        return report
    finally:
        report["ended_utc"] = datetime.now(timezone.utc).isoformat()
        (root / "initial-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if container_created:
            command(["docker", "stop", "--time", "10", NAME], timeout=25)
            command(["docker", "rm", NAME])
        if volume_created:
            command(["docker", "volume", "rm", VOLUME])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--serial-port", default="COM4")
    parser.add_argument("--flash", action="store_true", help="explicitly replace the backed-up firmware")
    args = parser.parse_args()
    try:
        result = exercise(args)
        print("E01_RESULT " + result["result"], flush=True)
        sys.exit(0 if result["result"] in ("PASS_INITIAL_SLICE", "HOST_PRECHECK_ONLY") else 1)
    except Exception:
        print("E01_RUN_FAILED (private diagnostics suppressed)", file=sys.stderr)
        sys.exit(1)
