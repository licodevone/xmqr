#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run current MQTT5 fixtures with explicit provenance and no silent skips.

Run in an isolated, clean three-repository layout after building both debug
and release client binaries. This program never builds, installs or publishes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time


SESSIONS = {
    "sessions", "message_expiry", "will_delay", "will_metadata", "will_expiry",
    "disconnect_expiry", "disconnect_with_will", "resumed_qos2_quota",
}
FLOW = {
    "receive_maximum", "connack_receive_maximum", "maximum_packet_size",
    "topic_alias", "outbound_alias", "publish_metadata", "request_properties",
    "negative_puback", "negative_pubrec", "qos2_completion_reasons",
}
SUBSCRIPTIONS = {
    "retain_handling", "subscribe_options", "subscription_identifier",
    "shared_live", "shared_durable", "shared_qos1_reassignment",
    "plain_auth", "reauth", "auth_refusal",
}
SUPERSEDED = {"verify_mqtt5_shared_unavailable.py": "P152 superseded by P153/P154 shared support"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fixtures(root):
    result = []
    for path in sorted((root / "scripts").glob("verify_mqtt5_*.py")):
        if path.name in SUPERSEDED:
            continue
        name = path.stem.removeprefix("verify_mqtt5_")
        phase = "6B" if name in SESSIONS else "6C" if name in FLOW else "6D" if name in SUBSCRIPTIONS else "6A"
        result.append({"file": path.name, "phase": phase, "arguments": [],
                       "expected_marker": "PASS", "timeout_seconds": 180})
    result.extend([
        {"file": "verify_paho_mqtt5.py", "phase": "6A", "arguments": ["--broker", "{broker}"],
         "expected_marker": "P168_PAHO_MQTT5_PASS", "timeout_seconds": 120, "requires_paho": True},
        {"file": "verify_phase6_vbi.py", "phase": "6A", "arguments": ["--broker", "{broker}", "--report", "{vbi_report}"],
         "expected_marker": "PASS", "timeout_seconds": 180},
        {"file": "verify_phase6_crash_matrix.py", "phase": "6B", "arguments": ["--broker", "{broker}", "--report", "{crash_report}"],
         "expected_marker": "P227_CRASH_MATRIX_PASS", "timeout_seconds": 240},
        {"file": "verify_phase6_paho_auth.py", "phase": "6D", "arguments": ["--broker", "{broker}", "--admin", "{admin}"],
         "expected_marker": "P227_PAHO_AUTH_PASS", "timeout_seconds": 180, "requires_paho": True},
        {"file": "../../xmqr-admin/scripts/verify_channel_cli.py", "phase": "6D",
         "arguments": ["--broker", "{broker}", "--admin", "{independent_admin}"],
         "expected_marker": "CHANNEL_CLI_PASS", "timeout_seconds": 180},
        {"file": "../../xmqr-admin/scripts/verify_core_028_state_v15.py", "phase": "6B", "arguments": [],
         "expected_marker": "A19_V15_PASS", "timeout_seconds": 120},
    ])
    for item in result:
        if item["file"] in ("verify_mqtt5_plain_auth.py", "verify_mqtt5_reauth.py"):
            item["arguments"] = ["--broker", "{broker}", "--admin", "{admin}", "--client", "{client}"]
    return result


def classify(returncode, output, expected_marker, timed_out=False):
    if timed_out:
        return "FAIL", "timeout"
    if returncode != 0:
        return "FAIL", "nonzero_exit"
    if not re.search(r"(?<![A-Za-z0-9_])" + re.escape(expected_marker) + r"(?![A-Za-z0-9_])", output):
        # PASS can also be the final segment of a specifically named marker.
        if expected_marker != "PASS" or not re.search(r"\b[A-Z0-9_]*_PASS\b|\bPASS:", output):
            return "FAIL", "success_marker_missing"
    return "PASS", None


def execute(command, expected_marker, timeout, cwd, environment):
    began = time.monotonic()
    timed_out = False
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=cwd, env=environment,
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        if process.returncode != 0 and not timed_out:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        stdout.seek(0)
        stderr.seek(0)
        out = stdout.read(262145)
        err = stderr.read(262145)
    status, reason = classify(process.returncode, out.decode("utf-8", errors="replace"), expected_marker, timed_out)
    if len(out) > 262144 or len(err) > 262144:
        status, reason = "FAIL", "output_budget_exceeded"
    return {"status": status, "reason": reason, "exit_code": process.returncode,
            "elapsed_seconds": round(time.monotonic() - began, 3),
            "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(err).hexdigest(),
            "stdout_bytes": len(out), "stderr_bytes": len(err)}


def provenance(root):
    result = {}
    for name in ("xmqr", "xmqr-client", "xmqr-admin"):
        repo = root if name == "xmqr" else root.parent / name
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        changed = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True)
        paths = subprocess.check_output([
            "git", "ls-files", "-z", "src", "scripts", "tests", "vendor", "validation",
            "Cargo.toml", "Cargo.lock", "Dockerfile", "packaging",
        ], cwd=repo).decode().split("\0")
        hashes = {path: digest(repo / path) for path in paths if path and (repo / path).is_file()}
        result[name] = {"revision": revision, "clean": not changed.strip(),
                        "tracked_files_sha256": hashes}
    return result


def preflight(root):
    binaries = {
        "broker": root / "target/debug/mqtt-broker",
        "client": root.parent / "xmqr-client/target/debug/mqtt-client",
        "client_release": root.parent / "xmqr-client/target/release/mqtt-client",
        "admin": root / "target/debug/mqtt-admin",
        "independent_admin": root.parent / "xmqr-admin/target/debug/xmqr-admin",
    }
    info = {}
    for role, path in binaries.items():
        if not path.is_file():
            raise RuntimeError("missing_binary:" + role)
        version = subprocess.check_output([str(path), "--version"], text=True, timeout=5).strip()
        info[role] = {"version": version, "sha256": digest(path)}
    if info["client"]["version"] != info["client_release"]["version"]:
        raise RuntimeError("client_debug_release_version_mismatch")
    for program in ("mosquitto_pub", "mosquitto_sub", "openssl"):
        if not shutil.which(program):
            raise RuntimeError("missing_prerequisite:" + program)
    return binaries, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--phase", choices=("all", "6A", "6B", "6C", "6D"), default="all")
    args = parser.parse_args()
    if os.name != "posix" or sys.flags.optimize:
        parser.error("Linux/WSL with Python assertions enabled is required")
    if args.report.exists():
        parser.error("evidence already exists; choose a new report")
    root = Path(__file__).resolve().parents[1]
    report = {"schema_version": 1, "status": "RUNNING", "selection": args.phase,
              "scenarios": [], "superseded_fixtures": SUPERSEDED,
              "limitations": ["Finite gates, not production, power loss or complete MQTT5 certification.",
                              "Mosquitto2.0.22 outbound-alias rejection remains an external limitation, not external interop PASS.",
                              "Python output contains only hashes, not private fixture logs or credentials."]}
    began = time.monotonic()
    try:
        before = provenance(root)
        if any(not repo["clean"] for repo in before.values()):
            raise RuntimeError("dirty_source_use_isolated_committed_layout")
        binaries, info = preflight(root)
        report.update(sources=before, binaries=info)
        replacements = {name: str(path.resolve()) for name, path in binaries.items()}
        replacements.update(vbi_report=str(args.report.with_name(args.report.stem + "-vbi.json").resolve()),
                            crash_report=str(args.report.with_name(args.report.stem + "-crash.json").resolve()))
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MQTT_") and key not in ("PYTHONOPTIMIZE",)}
        environment.update(TMPDIR="/var/tmp", PYTHONDONTWRITEBYTECODE="1")
        for fixture in fixtures(root):
            if args.phase != "all" and fixture["phase"] != args.phase:
                continue
            row = {"file": fixture["file"], "phase": fixture["phase"]}
            report["scenarios"].append(row)
            source = root / "scripts" / fixture["file"]
            if not source.is_file():
                row.update(status="BLOCKED", reason="missing_fixture")
                continue
            row["harness_sha256"] = digest(source)
            if fixture.get("requires_paho"):
                try:
                    available = importlib.util.find_spec("paho.mqtt") is not None
                except ModuleNotFoundError:
                    available = False
                if not available:
                    row.update(status="BLOCKED", reason="paho_not_available_no_install_attempted")
                    continue
            command = [sys.executable, str(source)]
            command += [value.format(**replacements) for value in fixture["arguments"]]
            row.update(execute(command, fixture["expected_marker"], fixture["timeout_seconds"], root, environment))
            print(row["phase"], row["file"], row["status"], flush=True)
        after = provenance(root)
        report["source_unchanged"] = after == before
        report["binaries_unchanged"] = all(digest(path) == info[role]["sha256"] for role, path in binaries.items())
        statuses = {row["status"] for row in report["scenarios"]}
        report["status"] = ("FAIL" if "FAIL" in statuses or not report["source_unchanged"] or not report["binaries_unchanged"]
                            else "BLOCKED" if "BLOCKED" in statuses else "PASS" if statuses else "FAIL")
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status="BLOCKED", error_type=type(error).__name__)
    report["elapsed_seconds"] = round(time.monotonic() - began, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print("P227_INTEGRATED_" + report["status"])
    return 0 if report["status"] == "PASS" else 2 if report["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
