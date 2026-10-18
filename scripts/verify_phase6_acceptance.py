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
import selectors
import shutil
import signal
import subprocess
import sys
import time
import tomllib


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
NAMED_MARKERS = dict(line.split() for line in """
ack_property_reasons P187_ACK_PROPERTY_REASONS_PASS
alias_error_disconnect P176_ALIAS_DISCONNECT_PASS
assigned_client_id P166_C97_C98_C99_ASSIGNED_ID_PASS
auth_fixed_flags P204_AUTH_FLAGS_PASS
auth_refusal P158_CLIENT_PASS
client_disconnect_reasons P174_CLIENT_DISCONNECT_PASS
connect_property_reason P183_CONNECT_PROPERTY_REASON_PASS
connect_property_semantic_reason P184_CONNECT_PROPERTY_SEMANTIC_REASON_PASS
connect_structure P199_CONNECT_STRUCTURE_PASS
connect_utf8_reason P196_CONNECT_UTF8_PASS
control_property_reasons P186_CONTROL_PROPERTY_REASONS_PASS
disconnect_with_will P172_DISCONNECT_WITH_WILL_PASS
fixed_header_flags_disconnect P205_FIXED_HEADER_FLAGS_PASS
initial_connect_flags P207_INITIAL_CONNECT_FLAGS_PASS
malformed_length_disconnect P177_MALFORMED_LENGTH_PASS
malformed_utf8 P195_UTF8_PASS
negative_puback P169_NEGATIVE_PUBACK_PASS
negative_pubrec P170_NEGATIVE_PUBREC_PASS
oversize_disconnect P175_OVERSIZE_DISCONNECT_PASS
plain_auth P159_TLS_PASS
publish_fixed_header_reasons P190_PUBLISH_FLAGS_PASS
publish_property_reasons P185_PUBLISH_PROPERTY_REASONS_PASS
qos2_completion_reasons P171_QOS2_COMPLETION_PASS
qos_ack_fixed_flags P208_QOS_ACK_FLAGS_PASS
reauth P160_REAUTH_PASS
reserved_control_type P203_RESERVED_CONTROL_PASS
second_connect P194_SECOND_CONNECT_PASS
server_keep_alive P162_KEEP_ALIVE_PASS
server_only_packet_reasons P201_SERVER_ONLY_PASS
shared_durable P154_C89_PASS
shared_live P153_C89_PASS
shared_qos1_reassignment P156_TCP_PASS
subscribe_options P148_C85_PASS
subscription_identifier P150_C87_PASS
subscription_property_disconnect P181_SUBSCRIPTION_PROPERTY_DISCONNECT_PASS
subscription_pubrel_fixed_flags P200_FLAGS_PASS
subscription_user_properties P180_SUBSCRIPTION_USER_PROPERTIES_PASS
truncated_fields P197_STRUCTURE_PASS
zero_command_id P189_ZERO_COMMAND_ID_PASS
zero_qos_ack_id P188_ZERO_QOS_ACK_ID_PASS
""".strip().splitlines())
TEXT_MARKERS = {
    "connack_receive_maximum": "PASS: P144 CONNACK Receive Maximum 1/32, packet-size boundaries, QoS0/1/2, overflow/restart, XMQR and Mosquitto",
    "disconnect_expiry": "PASS: MQTT 5 DISCONNECT expiry 0/finite/infinite, restart and invalid zero-to-positive",
    "maximum_packet_size": "PASS: MQTT 5 Maximum Packet Size, discard, QoS1/2, retained/restart, small CONNACK, C73 and Mosquitto",
    "message_expiry": "PASS: MQTT 5 Message Expiry client/Mosquitto QoS2 wire, remaining interval, offline/retained expiry after restart",
    "outbound_alias": "PASS: outbound MQTT 5 Topic Alias QoS0/1/2, retained/restart, max, reconnect, XMQR client; Mosquitto 2.0.22 limitation reproduced",
    "publish_metadata": "PASS: MQTT 5 PFI/Content Type QoS0/1/2, retained, offline/restart, MQTT3 subscriber, Mosquitto publisher",
    "receive_maximum": "PASS: MQTT 5 Receive Maximum quota, QoS0, replay after restart, client C72 and Mosquitto",
    "request_properties": "PASS: MQTT 5 request properties QoS0/1/2, retained, offline/restart, MQTT3 subscriber, Mosquitto publisher",
    "resumed_qos2_quota": "PASS: P146 resumed QoS2 full quota, PUBREC 0x97, old transaction, restart/recovery",
    "topic_alias": "PASS: MQTT 5 inbound Topic Alias QoS0/1/2, rebind, connection reset, client and Mosquitto",
    "will_delay": "PASS: MQTT 5 Will Delay, reconnect cancel, Clean Start, Session Expiry, restart, client C70 and Mosquitto",
    "will_expiry": "PASS: MQTT 5 Will expiry starts on publication, delayed/restart, offline/retained expiry and zero",
    "will_metadata": "PASS: MQTT 5 Will metadata, client C94, immediate, delayed/restart, offline and retained",
    "cross": ["PASS: MQTT 5 QoS 0/1 -> MQTT 3.1.1 subscriber (two deliveries)",
              "PASS: MQTT 3.1.1 -> MQTT 5 subscriber (retained and live QoS 1)"],
    "sessions": ["PASS: MQTT 5 resume, client/Mosquitto offline QoS1 after restart, expiry zero clears session",
                 "PASS: finite Session Expiry resumes before deadline and expires automatically across restart"],
    "retain_handling": "PASS: P147/C84 retain handling 0/1/2, persisted session/restart, XMQR",
}


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
                       "expected_marker": NAMED_MARKERS.get(name, TEXT_MARKERS.get(name)), "timeout_seconds": 180})
    result.extend([
        {"file": "verify_paho_mqtt5.py", "phase": "6A", "arguments": ["--broker", "{broker}"],
         "expected_marker": "P168_PAHO_MQTT5_PASS", "timeout_seconds": 120, "requires_paho": True},
        {"file": "verify_phase6_vbi.py", "phase": "6A", "arguments": ["--broker", "{broker}", "--label", "candidate", "--report", "{vbi_report}"],
         "expected_marker": "P227_VBI_PASS", "timeout_seconds": 180},
        {"file": "verify_phase6_alias_reason.py", "phase": "6A", "arguments": ["--broker", "{broker}", "--label", "candidate", "--report", "{alias_reason_report}"],
         "expected_marker": "P227_ALIAS_REASON_PASS", "timeout_seconds": 120},
        {"file": "verify_phase6_crash_matrix.py", "phase": "6B", "arguments": ["--broker", "{broker}", "--report", "{crash_report}"],
         "expected_marker": "P227_CRASH_MATRIX_PASS", "timeout_seconds": 240},
        {"file": "verify_phase6_shared_will.py", "phase": "6D", "arguments": ["--broker", "{broker}", "--report", "{shared_will_report}"],
         "expected_marker": "P227_SHARED_WILL_PASS", "timeout_seconds": 120},
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


def classify(returncode, output, expected_marker, timed_out=False, error_output=""):
    if timed_out:
        return "FAIL", "timeout"
    if returncode != 0:
        return "FAIL", "nonzero_exit"
    if re.search(r"\b(?:NOT_[A-Z0-9_]*PASS|[A-Z0-9_]*_FAIL|FAIL(?:ED)?|BLOCKED|SKIP(?:PED)?)\b",
                 output + "\n" + error_output):
        return "FAIL", "negative_marker_present"
    markers = expected_marker if isinstance(expected_marker, list) else [expected_marker]
    position = 0
    for marker in markers:
        if not marker:
            return "FAIL", "success_marker_missing"
        match = re.search(r"(?m)^" + re.escape(marker) + r"(?:[ :][^\n]*)?$", output[position:])
        if not match:
            return "FAIL", "success_marker_missing"
        position += match.end()
    return "PASS", None


def execute(command, expected_marker, timeout, cwd, environment):
    began = time.monotonic()
    timed_out = False
    budget_exceeded = False
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    process = subprocess.Popen(command, cwd=cwd, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map() or process.poll() is None:
            if time.monotonic() - began >= timeout:
                timed_out = True
                break
            finished = process.poll() is not None
            ready = selector.select(0 if finished else min(.05, timeout))
            if not ready and finished:
                break
            for key, _ in ready:
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffer = captured[key.data]
                buffer.extend(chunk[:max(0, 262145 - len(buffer))])
                if len(buffer) > 262144:
                    budget_exceeded = True
                    break
            if budget_exceeded:
                break
    if timed_out or budget_exceeded:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=5)
    descendants_remaining = False
    try:
        os.killpg(process.pid, 0)
        descendants_remaining = True
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.stdout.close()
    process.stderr.close()
    out, err = bytes(captured["stdout"]), bytes(captured["stderr"])
    status, reason = classify(process.returncode, out.decode("utf-8", errors="replace"),
                              expected_marker, timed_out, err.decode("utf-8", errors="replace"))
    if budget_exceeded:
        status, reason = "FAIL", "output_budget_exceeded"
    elif descendants_remaining and not timed_out:
        status, reason = "FAIL", "private_descendants_remaining"
    return {"status": status, "reason": reason, "exit_code": process.returncode,
            "cleanup": "REMAINING_GROUP_KILLED" if descendants_remaining else "PASS",
            "elapsed_seconds": round(time.monotonic() - began, 3),
            "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(err).hexdigest(),
            "stdout_bytes": len(out), "stderr_bytes": len(err)}


def provenance(root):
    result = {}
    for name in ("xmqr", "xmqr-client", "xmqr-admin"):
        repo = root if name == "xmqr" else root.parent / name
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True, timeout=30).strip()
        changed = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True, timeout=60)
        paths = subprocess.check_output([
            "git", "ls-files", "-z", "src", "scripts", "tests", "vendor", "validation",
            "Cargo.toml", "Cargo.lock", "Dockerfile", "packaging",
        ], cwd=repo, timeout=30).decode().split("\0")
        hashes = {path: digest(repo / path) for path in paths if path and (repo / path).is_file()}
        result[name] = {"revision": revision, "clean": not changed.strip(),
                        "tracked_files_sha256": hashes}
    return result


def verify_versions(root, info):
    """A same-version stale binary still needs the separate source/hash gates."""
    manifests = {
        "broker": root / "Cargo.toml",
        "admin": root / "Cargo.toml",
        "client": root.parent / "xmqr-client/Cargo.toml",
        "client_release": root.parent / "xmqr-client/Cargo.toml",
        "independent_admin": root.parent / "xmqr-admin/Cargo.toml",
    }
    for role, manifest in manifests.items():
        with manifest.open("rb") as stream:
            version = tomllib.load(stream)["package"]["version"]
        if info[role]["version"].split()[-1] != version:
            raise RuntimeError("manifest_binary_version_mismatch:" + role)


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
    verify_versions(root, info)
    for program in ("mosquitto_pub", "mosquitto_sub", "openssl"):
        if not shutil.which(program):
            raise RuntimeError("missing_prerequisite:" + program)
    return binaries, info


def external_provenance():
    result = {}
    for program, arguments in (("mosquitto_pub", ["--help"]),
                               ("mosquitto_sub", ["--help"]), ("openssl", ["version"])):
        path = shutil.which(program)
        if not path:
            raise RuntimeError("missing_prerequisite:" + program)
        version = subprocess.run([path, *arguments], capture_output=True, text=True, timeout=5, check=False)
        if program.startswith("mosquitto_"):
            # These CLI --help commands return 1 normally, not only on failure.
            lines = [line for line in version.stdout.splitlines() if line.startswith(program + " version ")]
            if version.returncode not in (0, 1) or len(lines) != 1:
                raise RuntimeError("unrecognized_external_version:" + program)
            version_line = lines[0]
        else:
            if version.returncode != 0 or not version.stdout.startswith("OpenSSL "):
                raise RuntimeError("unrecognized_external_version:" + program)
            version_line = version.stdout.splitlines()[0]
        result[program] = {"executable": str(Path(path).resolve()), "sha256": digest(path),
                           "version": version_line}
    return result


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
    stage = "provenance_before"
    try:
        before = provenance(root)
        report["sources"] = before
        if any(not repo["clean"] for repo in before.values()):
            raise RuntimeError("dirty_source_use_isolated_committed_layout")
        stage = "preflight"
        binaries, info = preflight(root)
        report.update(sources=before, binaries=info, external_tools=external_provenance())
        replacements = {name: str(path.resolve()) for name, path in binaries.items()}
        replacements.update(vbi_report=str(args.report.with_name(args.report.stem + "-vbi.json").resolve()),
                            alias_reason_report=str(args.report.with_name(args.report.stem + "-alias-reason.json").resolve()),
                            crash_report=str(args.report.with_name(args.report.stem + "-crash.json").resolve()),
                            shared_will_report=str(args.report.with_name(args.report.stem + "-shared-will.json").resolve()))
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MQTT_") and key not in ("PYTHONOPTIMIZE",)}
        environment.update(TMPDIR="/var/tmp", PYTHONDONTWRITEBYTECODE="1")
        for fixture in fixtures(root):
            if args.phase != "all" and fixture["phase"] != args.phase:
                continue
            row = {"file": fixture["file"], "phase": fixture["phase"]}
            stage = "fixture:" + fixture["file"]
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
                import paho.mqtt
                module_path = Path(paho.mqtt.__file__).resolve()
                row["paho"] = {"version": paho.mqtt.__version__,
                               "package_files_sha256": {
                                   str(path.relative_to(module_path.parent)): digest(path)
                                   for path in sorted(module_path.parent.rglob("*.py"))}}
            command = [sys.executable, str(source)]
            command += [value.format(**replacements) for value in fixture["arguments"]]
            row.update(execute(command, fixture["expected_marker"], fixture["timeout_seconds"], root, environment))
            print(row["phase"], row["file"], row["status"], flush=True)
        stage = "provenance_after"
        after = provenance(root)
        report["source_unchanged"] = after == before
        report["binaries_unchanged"] = all(digest(path) == info[role]["sha256"] for role, path in binaries.items())
        statuses = {row["status"] for row in report["scenarios"]}
        report["status"] = ("FAIL" if "FAIL" in statuses or not report["source_unchanged"] or not report["binaries_unchanged"]
                            else "BLOCKED" if "BLOCKED" in statuses else "PASS" if statuses else "FAIL")
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status="BLOCKED", error_type=type(error).__name__, error_stage=stage,
                      error_errno=getattr(error, "errno", None))
    report["elapsed_seconds"] = round(time.monotonic() - began, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print("P227_INTEGRATED_" + report["status"])
    return 0 if report["status"] == "PASS" else 2 if report["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
