#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run phase-1 source gates in Linux using only test-owned processes and state.

Does not install software, operate installed services, or accept package lifecycle.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-root", type=Path, required=True)
    parser.add_argument("--build-cache-root", type=Path,
                        help="reuse an existing /tmp/xmqr-phase1-build-* Cargo cache; all gates still run")
    args = parser.parse_args()
    if sys.platform != "linux" or sys.version_info < (3, 11):
        parser.exit(2, "BLOCKED: Linux and Python 3.11+ required; run from the current source checkout in Ubuntu/WSL\n")
    broker_root = Path(__file__).resolve().parents[1]
    client_root = args.client_root.resolve()
    for root in (broker_root, client_root):
        if not (root / "Cargo.lock").is_file() or not (root / "Cargo.toml").is_file():
            parser.exit(2, f"BLOCKED: source repository missing: {root}\n")
    missing = [command for command in ("cargo", "rustc", "git") if not shutil.which(command)]
    if missing:
        parser.exit(2, f"BLOCKED: missing prerequisites: {', '.join(missing)}\n")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(tempfile.mkdtemp(prefix=f"phase1-{stamp}-", dir=ensure_target(broker_root)))
    # Native Linux build files avoid DrvFS metadata overhead; logs stay durable
    # in the workspace. These are fresh test-owned targets, not installed bins.
    if args.build_cache_root:
        build_root = args.build_cache_root.resolve()
        if not build_root.is_dir() or build_root.parent != Path("/tmp") or not build_root.name.startswith("xmqr-phase1-build-"):
            parser.exit(2, "BLOCKED: cache must be an existing /tmp/xmqr-phase1-build-* directory\n")
    else:
        build_root = Path(tempfile.mkdtemp(prefix=f"xmqr-phase1-build-{stamp}-", dir="/tmp"))
    targets = {"broker": build_root / "broker-target", "client": build_root / "client-target"}
    env = {key: value for key, value in os.environ.items() if not key.startswith("MQTT_")}
    env.update(CARGO_NET_OFFLINE="true", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", TMPDIR="/tmp")
    # Build only this source, never a configured cross target or installed binary.
    env.pop("CARGO_BUILD_TARGET", None)
    env.pop("CARGO_TARGET_DIR", None)
    records = []

    def blocked(name, reason):
        records.append({"name": name, "status": "BLOCKED", "reason": reason})
        print(f"BLOCKED: {name}: {reason}", flush=True)
        return False

    def run(name, argv, cwd, target=None, timeout=1800):
        log = output / f"{name}.log"
        child_env = dict(env)
        if target is not None:
            child_env["CARGO_TARGET_DIR"] = str(target)
        started = time.monotonic()
        with log.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps({"command": argv, "cwd": str(cwd)}, ensure_ascii=False) + "\n")
            stream.flush()
            try:
                process = subprocess.Popen(argv, cwd=cwd, env=child_env, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                code = process.wait(timeout=timeout)
                status = "PASS" if code == 0 else "FAIL"
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                finally:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=10)
                stream.write("FAIL: runner command timeout\n")
                code, status = None, "FAIL"
            except OSError as error:
                stream.write(f"BLOCKED: {error}\n")
                code, status = None, "BLOCKED"
        records.append({"name": name, "status": status, "exit_code": code,
                        "seconds": round(time.monotonic() - started, 3), "log": str(log)})
        print(f"{status}: {name}: {log}", flush=True)
        return status == "PASS"

    print(f"Logs: {output}", flush=True)
    roots = {"broker": broker_root, "client": client_root}
    before = {name: source_snapshot(root) for name, root in roots.items()}
    (output / "sources-before.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")
    run("rustc-version", ["rustc", "--version"], broker_root)
    run("cargo-version", ["cargo", "--version"], broker_root)
    run("linux-version", ["uname", "-a"], broker_root)
    built = {}
    for name, root in (("broker", broker_root), ("client", client_root)):
        run(f"{name}-head", ["git", "rev-parse", "HEAD"], root)
        run(f"{name}-status", ["git", "status", "--short"], root)
        run(f"{name}-fmt", ["cargo", "fmt", "--all", "--", "--check"], root, targets[name])
        run(f"{name}-tests", ["cargo", "test", "--locked", "--offline"], root, targets[name])
        run(f"{name}-clippy", ["cargo", "clippy", "--locked", "--offline", "--all-targets", "--", "-D", "warnings"], root, targets[name])
        built[name] = run(f"{name}-build", ["cargo", "build", "--locked", "--offline", "--bins"], root, targets[name])
        run(f"{name}-licenses", [sys.executable, "-X", "utf8", "-B", "scripts/license_inventory.py", "--check"], root, targets[name])
    broker_bin = targets["broker"] / "debug" / "mqtt-broker"
    client_bin = targets["client"] / "debug" / "mqtt-client"
    artifacts = {}
    for path in (broker_bin, targets["broker"] / "debug" / "mqtt-admin", client_bin):
        if path.is_file():
            artifacts[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    if built["broker"]:
        run("p54-tcp", [sys.executable, "-B", "scripts/verify_connection_limit.py", "--broker", str(broker_bin)], broker_root, timeout=180)
    else:
        blocked("p54-tcp", "broker build failed")
    missing_interop = [binary for binary in ("mosquitto_pub", "mosquitto_sub", "stdbuf") if not shutil.which(binary)]
    if not built["broker"]:
        blocked("mosquitto-open-lab", "broker build failed")
    elif missing_interop:
        blocked("mosquitto-open-lab", "missing prerequisites: " + ", ".join(missing_interop))
    else:
        run("mosquitto-open-lab", [sys.executable, "-B", "scripts/verify_interop.py", "--broker", str(broker_bin)], broker_root, timeout=300)
    external_interop = dict(records[-1])
    if built["broker"] and built["client"]:
        for name, script in (("p55-quotas", "verify_state_limits.py"), ("will-regression", "verify_last_will.py")):
            run(name, [sys.executable, "-B", f"scripts/{script}", "--broker", str(broker_bin), "--client", str(client_bin)], broker_root, timeout=300)
        c27 = client_root / "validation" / "C27-integration.py"
        if c27.is_file() and shutil.which("openssl"):
            run("c27-integration", [sys.executable, "-B", str(c27), "--broker", str(broker_bin), "--client", str(client_bin), "--fixtures", str(broker_root / "scripts" / "verify_interop.py")], client_root, timeout=300)
        else:
            blocked("c27-integration", "C27 harness or openssl missing")
        c38 = client_root / "scripts" / "verify_phase1.py"
        if c38.is_file():
            run("c38-integration", [sys.executable, "-B", str(c38), "--broker", str(broker_bin), "--client", str(client_bin), "--report", str(output / "c38-report.json")], client_root, timeout=300)
        else:
            blocked("c38-integration", "C38 harness missing")
    else:
        for name in ("p55-quotas", "will-regression", "c27-integration", "c38-integration"):
            blocked(name, "broker/client build failed")
    after = {name: source_snapshot(root) for name, root in roots.items()}
    (output / "sources-after.json").write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
    for name in roots:
        status = "PASS" if before[name] == after[name] else "FAIL"
        records.append({"name": f"{name}-source-unchanged", "status": status})
        print(f"{status}: {name}-source-unchanged", flush=True)
    summary = {"started_utc": stamp, "broker_root": str(broker_root), "client_root": str(client_root),
               "results": records, "artifact_sha256": artifacts,
               "package_lifecycle": "NOT_RUN: execute packaging/test_package.sh only in a disposable Ubuntu container",
               "external_interop": external_interop,
               "sources_before": "sources-before.json", "sources_after": "sources-after.json",
               "phase1_accepted": False}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    passed = all(record["status"] == "PASS" for record in records)
    print("UNIT_INTEGRATION_PASS" if passed else "UNIT_INTEGRATION_INCOMPLETE", flush=True)
    print(f"PHASE1_BLOCKED: package lifecycle NOT_RUN; external open-lab interop {external_interop['status']}", flush=True)
    print(f"Summary: {output / 'summary.json'}", flush=True)
    return 0 if passed else 1


def source_snapshot(root):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    names = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root).split(b"\0")
    files = {}
    for name in sorted(set(names)):
        if not name:
            continue
        relative = os.fsdecode(name)
        path = root / relative
        if path.is_symlink():
            data = os.fsencode(os.readlink(path))
        elif path.is_file():
            data = path.read_bytes()
        else:
            files[relative] = "MISSING"
            continue
        files[relative] = hashlib.sha256(data).hexdigest()
    return {"head": head, "files": files}


def ensure_target(root):
    target = root / "target"
    target.mkdir(exist_ok=True)
    return target


if __name__ == "__main__":
    raise SystemExit(main())
