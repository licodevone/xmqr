#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Explicit physical E01 campaign, scoped resources and sanitized evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import ssl
import struct
import subprocess
import sys
import time
from urllib.parse import urlsplit

import serial
from evidence import CAMPAIGN_MILESTONES, collect
from prepare_phase2 import MOSQUITTO, load
from retained_observer import Peer, field
from run_initial import BROKER_IMAGE, command, save_report, verified_backups
from sync_wifi import REPO, private_file, read_bounded

NAME = "xmqr-e01-p85-20261013"
VOLUME = NAME + "-state"
NETWORK = NAME + "-net"
TOPIC = b"e01/board/bytes"
RETAINED = b"e01/board/retained"
WILL = b"e01/board/will"
CONTROL = b"e01/board/control"


def payload(sequence):
    return bytes([sequence]) + bytes(i % 251 for i in range(1, 1024))


def validate_message(message, topic, sequence, retained=False, qos=1):
    expected = b"" if sequence is None else payload(sequence)
    if message != (topic, qos, retained, expected):
        raise ValueError("physical wire message mismatch")


def validate_external(output):
    # Only known DATA lines can be compared; never copy output into public logs.
    lines = output.decode("ascii").splitlines()
    if lines != [f"DATA|2|1|{payload(11).hex()}"]:
        raise ValueError("external QoS2/retained/bytes mismatch")


def metrics(markers):
    memory, timing = {}, {}
    for line in markers:
        found = re.fullmatch(r"P85_MEMORY stage=(idle|wifi|restart|final) largest_probe=([0-9]+)", line)
        if found:
            if found[1] in memory:
                raise ValueError("duplicate memory metric")
            memory[found[1]] = int(found[2])
        found = re.fullmatch(r"P85_TIME kind=(wifi|broker) milliseconds=([0-9]+)", line)
        if found:
            if found[1] in timing:
                raise ValueError("duplicate timing metric")
            timing[found[1]] = int(found[2])
    if set(memory) != {"idle", "wifi", "restart", "final"} or set(timing) != {"wifi", "broker"}:
        raise ValueError("missing physical metrics")
    if any(n < 8192 or n > 196608 or n % 4096 for n in memory.values()) or memory["idle"] - memory["final"] > 32768:
        raise ValueError("memory budget failed")
    if any(n > 60000 for n in timing.values()):
        raise ValueError("reconnection deadline failed")
    return dict(largest_rust_allocation_probe=memory, reconnection_ms=timing,
                total_free_heap_measured=False, long_leak_test=False)


class Lab:
    def __init__(self, root, host, port, case):
        self.root, self.host, self.port, self.case = root, host, port, case
        self.container = self.volume = self.network = False
        self.jobs = set()

    def start(self):
        for kind, name in (("container", NAME), ("volume", VOLUME), ("network", NETWORK)):
            result = subprocess.run(["docker", kind, "inspect", name], capture_output=True, timeout=15)
            if result.returncode == 0:
                raise ValueError("existing lab resource refused")
        command(["docker", "image", "inspect", BROKER_IMAGE])
        command(["docker", "image", "inspect", MOSQUITTO])
        command(["docker", "network", "create", NETWORK]); self.network = True
        command(["docker", "volume", "create", VOLUME]); self.volume = True
        command(["docker", "run", "--rm", "--user", "0:0", "--network", "none",
                 "--mount", f"type=volume,source={VOLUME},target=/var/lib/xmqr",
                 "--entrypoint", "/bin/sh", BROKER_IMAGE, "-c", "chown 10001:10001 /var/lib/xmqr"])
        self.create("normal")

    def create(self, profile):
        certs = self.case / profile
        command(["docker", "create", "--name", NAME, "--network", NETWORK, "--network-alias", "e01-broker",
                 "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                 "--pids-limit", "64", "--memory", "256m", "--publish", f"{self.host}:{self.port}:8883",
                 "--mount", f"type=bind,source={certs},target=/run/e01,readonly",
                 "--mount", f"type=volume,source={VOLUME},target=/var/lib/xmqr",
                 "--env", "MQTT_SERVER_CERT=/run/e01/server.crt", "--env", "MQTT_SERVER_KEY=/run/e01/server.key",
                 "--env", "MQTT_CLIENT_CA=/run/e01/ca.crt", "--env", "MQTT_USERS_FILE=/run/e01/users.toml",
                 "--env", "MQTT_ACL_FILE=/run/e01/acl.toml", "--env", "MQTT_MAX_CONNECTIONS=8",
                 "--env", "RUST_LOG=error", BROKER_IMAGE])
        self.container = True
        command(["docker", "start", NAME])
        self.ready(profile)

    def ready(self, profile):
        context = ssl.create_default_context(cafile=str(self.case / "normal/ca.crt"))
        context.load_cert_chain(self.root / "certs/board.crt", self.root / "certs/board.key")
        until = time.monotonic() + 15
        while time.monotonic() < until:
            try:
                with socket.create_connection((self.host, self.port), timeout=.5) as tcp:
                    with context.wrap_socket(tcp, server_hostname="e01-broker" if profile == "san" else self.host):
                        return
            except (OSError, ssl.SSLError):
                time.sleep(.1)
        raise ValueError("lab mTLS not ready")

    def restart(self):
        command(["docker", "stop", "--time", "10", NAME], timeout=20)
        command(["docker", "start", NAME])
        self.ready("normal")

    def replace(self, profile):
        began = time.monotonic()
        command(["docker", "stop", "--time", "10", NAME], timeout=20)
        command(["docker", "rm", NAME]); self.container = False
        self.create(profile)
        if time.monotonic() - began > 6:
            raise ValueError("SAN coordination budget exceeded")

    def external(self, program):
        name = NAME + "-" + program
        exists = subprocess.run(["docker", "container", "inspect", name], capture_output=True, timeout=10)
        if exists.returncode == 0:
            raise ValueError("existing external client refused")
        args = ["-h", "e01-broker", "-p", "8883", "-V", "mqttv311", "-q", "2", "-i", "e01-external-" + program]
        if program == "sub":
            args += ["-t", RETAINED.decode(), "-C", "1", "-W", "6", "-F", "DATA|%q|%r|%x"]
        else:
            args += ["-t", TOPIC.decode(), "-f", "/run/test/payload-12.bin"]
        command(["docker", "create", "--name", name, "--network", NETWORK, "--read-only",
                 "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "32", "--memory", "64m",
                 "--mount", f"type=bind,source={self.case / 'external'},target=/run/test,readonly",
                 "--env", "XDG_CONFIG_HOME=/run/test", "--entrypoint", "mosquitto_" + program, MOSQUITTO, *args])
        self.jobs.add(name)
        try:
            output = command(["docker", "start", "--attach", name], timeout=15)
            # docker start -a may not propagate container's process exit.
            code = command(["docker", "inspect", "--format", "{{.State.ExitCode}}", name]).strip()
            if code != b"0":
                raise ValueError("external client failed")
            return output
        finally:
            command(["docker", "rm", "--force", name]); self.jobs.remove(name)

    def cleanup(self):
        failures = []
        operations = [("CLIENT_REMOVE", ["docker", "rm", "--force", n]) for n in sorted(self.jobs)]
        if self.container:
            operations += [("CONTAINER_STOP", ["docker", "stop", "--time", "10", NAME]),
                           ("CONTAINER_REMOVE", ["docker", "rm", NAME])]
        if self.volume:
            operations += [("VOLUME_REMOVE", ["docker", "volume", "rm", VOLUME])]
        if self.network:
            operations += [("NETWORK_REMOVE", ["docker", "network", "rm", NETWORK])]
        for code, args in operations:
            try:
                command(args, timeout=25)
            except Exception:
                failures.append(code)
        return failures


class Supervisor:
    def __init__(self, lab, config):
        self.lab, self.config = lab, config
        self.base = None
        self.results = []
        self.deadline = time.monotonic() + 180
        self.open()

    def open(self):
        self.base = Peer(self.lab.host, self.lab.port, self.lab.case / "observer", self.config["username"],
                         self.config["password"], "e01-p85-observer", deadline=self.deadline)
        for topic in (TOPIC, WILL, RETAINED):
            self.base.subscribe(topic)

    def control(self, sequence, retained=False):
        identifier = self.base.next_id()
        self.base.send(0x33 if retained else 0x32, field(CONTROL) + identifier + bytes([sequence]))
        self.base.await_packet(0x40, identifier)

    def expect(self, topic, sequence, retained=False, timeout=3):
        if self.base.pending:
            message = self.base.message()
        else:
            header, body = self.base.receive(min(self.deadline, time.monotonic() + timeout))
            message = self.base.decode(header, body)
        validate_message(message, topic, sequence, retained)

    def close_base(self):
        base, self.base = self.base, None
        if base is not None:
            base.close()

    def event(self, line):
        if line == "P85_CONNECTED":
            self.expect(TOPIC, 6); self.results.append("BASELINE_BYTES_PASS")
        elif line == "P85_WILL_READY":
            self.expect(WILL, 6, timeout=20); self.results.append("WILL_LINK_LOSS_PASS")
        elif line == "P85_WIFI_RECONNECT_PASS":
            self.expect(TOPIC, 7); self.results.append("WIFI_RECONNECT_BYTES_PASS")
        elif line == "P85_RESTART_READY":
            self.expect(RETAINED, 8); self.close_base(); self.lab.restart(); self.open()
            self.expect(RETAINED, 8, retained=True); self.control(8, retained=True)
            self.results.append("RETAINED_AFTER_RESTART_PASS")
        elif line == "P85_BROKER_RECONNECT_PASS":
            self.expect(TOPIC, 10); self.control(10); self.results.append("BROKER_RECONNECT_BYTES_PASS")
        elif line == "P85_RESTART_DELETE":
            self.expect(RETAINED, None)
            peer = Peer(self.lab.host, self.lab.port, self.lab.case / "observer", self.config["username"], self.config["password"], "e01-p85-delete", deadline=self.deadline)
            try:
                peer.subscribe(RETAINED); peer.assert_no_replay()
            finally:
                peer.close()
            self.control(20); self.results.append("RETAINED_LIVE_DELETE_AND_NO_REPLAY_PASS")
        elif line == "P85_DUPLICATE_READY":
            peer = Peer(self.lab.host, self.lab.port, self.lab.case / "external", "e01-external", self.config["external_password"], "e01-p85-duplicate", deadline=self.deadline)
            try:
                identifier = peer.next_id(); body = field(TOPIC) + identifier + payload(9)
                for header in (0x32, 0x3a):
                    peer.send(header, body); peer.await_packet(0x40, identifier)
            finally:
                peer.close()
            self.expect(TOPIC, 9); self.expect(TOPIC, 9); self.results.append("QOS1_DUPLICATE_BYTES_PASS")
        elif line == "P85_EXTERNAL_SUB_READY":
            self.expect(RETAINED, 11); validate_external(self.lab.external("sub"))
            self.control(11); self.results.append("MOSQUITTO_QOS2_REPLAY_BYTES_PASS")
        elif line == "P85_EXTERNAL_PUB_READY":
            self.lab.external("pub"); self.expect(TOPIC, 12); self.results.append("MOSQUITTO_QOS2_PUBLISH_BYTES_PASS")
        elif line in ("P85_NEGATIVE_CA_PASS", "P85_NEGATIVE_PASSWORD_PASS", "P85_NEGATIVE_ACL_PASS"):
            self.base.send(0xc0); self.base.await_packet(0xd0, b"")
            self.results.append(line.removeprefix("P85_") + "_SERVICE_ALIVE")
        elif line == "P85_SAN_READY":
            began = time.monotonic(); self.control(30)
            if time.monotonic() - began > 1:
                raise ValueError("SAN control latency exceeded")
        elif line == "P85_SAN_ARMED":
            self.close_base(); self.lab.replace("san")
        elif line == "P85_NEGATIVE_SAN_PASS":
            self.lab.replace("normal"); self.open(); self.expect(RETAINED, 11, retained=True)
            self.control(31, retained=True); self.results.append("NEGATIVE_SAN_SERVICE_ALIVE")
        elif line == "P85_SAN_RESTORED":
            self.expect(TOPIC, 14); self.results.append("FINAL_VALID_MTLS_BYTES_PASS")

    def complete(self):
        return self.results == ["BASELINE_BYTES_PASS", "WILL_LINK_LOSS_PASS", "WIFI_RECONNECT_BYTES_PASS",
            "RETAINED_AFTER_RESTART_PASS", "BROKER_RECONNECT_BYTES_PASS", "RETAINED_LIVE_DELETE_AND_NO_REPLAY_PASS",
            "QOS1_DUPLICATE_BYTES_PASS", "MOSQUITTO_QOS2_REPLAY_BYTES_PASS", "MOSQUITTO_QOS2_PUBLISH_BYTES_PASS",
            "NEGATIVE_CA_PASS_SERVICE_ALIVE", "NEGATIVE_PASSWORD_PASS_SERVICE_ALIVE", "NEGATIVE_ACL_PASS_SERVICE_ALIVE",
            "NEGATIVE_SAN_SERVICE_ALIVE", "FINAL_VALID_MTLS_BYTES_PASS"]


def flash(root, port):
    candidates = [p for p in (root / "target/xtensa-esp32-espidf/release/build").glob("esp-idf-sys-*/out")
                  if (p / "build/bootloader/bootloader.bin").is_file()]
    if len(candidates) != 1:
        raise ValueError("ambiguous SDK output")
    sdk = candidates[0]; app = root / "p85-app.bin"
    command([sys.executable, "-m", "esptool", "--chip", "esp32", "elf2image", "--flash_mode", "dio",
             "--flash_freq", "40m", "--flash_size", "4MB", "--elf-sha256-offset", "0xb0", "--output", str(app),
             str(root / "target/xtensa-esp32-espidf/release/xmqr-esp32-e01")])
    if app.stat().st_size > 1048576:
        raise ValueError("app exceeds partition")
    command([sys.executable, "-m", "esptool", "--chip", "esp32", "--port", port, "--baud", "115200",
             "write_flash", "--flash_mode", "dio", "--flash_freq", "40m", "--flash_size", "4MB",
             "0x1000", str(sdk / "build/bootloader/bootloader.bin"), "0x8000", str(sdk / "build/partition_table/partition-table.bin"),
             "0x10000", str(app)], timeout=240)
    return app.stat().st_size


def exercise(args):
    root = args.private_dir.resolve(strict=True)
    if root.is_relative_to(REPO) or not args.flash:
        raise ValueError("explicit flash and private lab required")
    backup = verified_backups(args.backup_dir.resolve(strict=True))
    case, config = load(root)
    url = urlsplit(json.loads(read_bounded(private_file(root, "firmware-config.json")))["mqtt_url"])
    if url.scheme != "mqtts" or url.username:
        raise ValueError("secure endpoint required")
    with socket.socket() as probe:
        probe.bind((url.hostname, url.port))
    lab = Lab(root, url.hostname, url.port, case)
    report = dict(schema=3, prompt="P85", broker="0.11.4", client="0.8.1", port=args.serial_port,
                  started_utc=datetime.now(timezone.utc).isoformat(), backup_sha256=backup, backup_bytes=4194304,
                  flashed=False, result="FAIL_PRECHECK", markers=[], observer_results=[], phase2_closed=False)
    digest = hashlib.sha256()
    for relative in ("Cargo.toml", "Cargo.lock", "build.rs", "sdkconfig.defaults", ".cargo/config.toml", "src/main.rs", "src/campaign.rs", "src/memory_probe.rs"):
        digest.update(relative.encode()); digest.update((Path(__file__).resolve().parent / relative).read_bytes())
    report["host_source_sha256"] = digest.hexdigest()
    report["campaign_mode"] = True
    supervisor = None
    try:
        lab.start(); print("P85_HOST_MTLS_READY", flush=True)
        report["app_bytes"] = flash(root, args.serial_port); report["flashed"] = True
        print("P85_FLASH_VERIFIED", flush=True)
        supervisor = Supervisor(lab, config)
        def emit(line):
            print(line, flush=True); report["markers"].append(line); supervisor.event(line)
        report["result"] = "FAIL_HOST_OR_PHYSICAL"
        with serial.Serial(args.serial_port, 115200, timeout=.2) as uart:
            uart.dtr = False; uart.rts = True; time.sleep(.1); uart.rts = False
            transcript = collect(uart, seconds=180, emit=emit, milestones=CAMPAIGN_MILESTONES)
        report.update(transcript.summary())
        if report["result"] == "PASS_PHYSICAL_CAMPAIGN":
            if not supervisor.complete():
                report["result"] = "FAIL_OBSERVER"
            else:
                report["result"] = "FAIL_METRICS"
                report["metrics"] = metrics(report["markers"])
                report["result"] = "PASS_PHYSICAL_CAMPAIGN"
        return report
    finally:
        if supervisor is not None:
            report["observer_results"] = list(supervisor.results)
            try:
                supervisor.close_base()
            except Exception:
                report["result"] = "FAIL_OBSERVER_CLOSE"
        report["cleanup_errors"] = lab.cleanup()
        if report["cleanup_errors"]:
            report["result"] = "FAIL_CLEANUP"
        report["ended_utc"] = datetime.now(timezone.utc).isoformat()
        save_report(root, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--serial-port", default="COM4")
    parser.add_argument("--flash", action="store_true")
    args = parser.parse_args()
    try:
        result = exercise(args)
        print("P85_RESULT " + result["result"], flush=True)
        sys.exit(0 if result["result"] == "PASS_PHYSICAL_CAMPAIGN" else 1)
    except Exception:
        print("P85_RUN_FAILED (private details suppressed)", file=sys.stderr)
        sys.exit(1)
