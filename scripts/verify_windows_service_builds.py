"""Prove service builds and console negatives without installing Windows services.

Writes command logs, source hashes and a JSON report. SCM lifecycle, UAC and
native runtime acceptance are deliberately separate gates, never inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = {
    "broker": (ROOT, "mqtt-broker", ["windows_", "configuration::tests"]),
    "client": (ROOT.parent / "xmqr-client", "mqtt-client", ["windows_service::tests", "service_config::tests"]),
    "admin": (ROOT.parent / "xmqr-admin", "xmqr-admin", ["windows_service::tests", "config::tests"]),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(root: Path) -> dict[str, str]:
    files = list((root / "src").rglob("*.rs"))
    files += list((root / "vendor").rglob("*.rs"))
    files += [root / "Cargo.toml", root / "Cargo.lock",
              root / "packaging/windows-service/Cargo.toml",
              root / "packaging/windows-service/Cargo.lock"]
    return {str(p.relative_to(root)).replace("\\", "/"): sha256(p)
            for p in sorted(files) if p.is_file()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory")
    parser.add_argument("--target-dir", type=Path, default=ROOT / "target/p239-service-proof")
    parser.add_argument("--components", nargs="+", choices=PRODUCTS, default=list(PRODUCTS))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This proof requires native Windows")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    target = args.target_dir.resolve()
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(("MQTT_", "XMQR_"))}
    report = {
        "schema": 1, "started_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "target": "x86_64-pc-windows-msvc",
        "script_sha256": sha256(Path(__file__)), "products": {}, "commands": [],
        "scm_lifecycle": "NOT_RUN", "native_acceptance": False,
    }

    def save() -> None:
        (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def run(label: str, command: list[str], cwd: Path, expected=(0,), extra_env=None,
            contains: str | None = None, tests=False, timeout=1200) -> tuple[bool, str]:
        start = time.monotonic()
        print(f"RUN {label}", flush=True)
        log = output / f"{label}.log"
        process_env = env | (extra_env or {})
        with log.open("wb") as stream:
            try:
                result = subprocess.run(command, cwd=cwd, env=process_env,
                                        stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = None
            except OSError as error:
                stream.write(str(error).encode("utf-8"))
                code = None
        text = log.read_text(encoding="utf-8", errors="replace")
        count = sum(int(n) for n in re.findall(r"test result: ok\. (\d+) passed", text))
        passed = code in expected and (contains is None or contains in text) and (not tests or count > 0)
        report["commands"].append({
            "label": label, "argv": command, "cwd": str(cwd),
            "exit_code": code, "expected_exit_codes": list(expected),
            "required_text": contains, "tests_passed": count if tests else None,
            "status": "PASS" if passed else "FAIL", "seconds": round(time.monotonic() - start, 3),
            "log": log.name, "log_sha256": sha256(log),
        })
        save()
        print(f"{'PASS' if passed else 'FAIL'} {label} (exit={code})", flush=True)
        return passed, text

    run("rustc", ["rustc", "-Vv"], ROOT)
    run("cargo", ["cargo", "-V"], ROOT)
    for kind in dict.fromkeys(args.components):
        root, binary, filters = PRODUCTS[kind]
        manifest = root / "packaging/windows-service/Cargo.toml"
        before = sources(root)
        product = {"source_hashes": before, "build": "NOT_RUN", "marker": "NOT_RUN"}
        report["products"][kind] = product
        _, product["head"] = run(f"{kind}-head", ["git", "rev-parse", "HEAD"], root)
        product["head"] = product["head"].strip()
        _, dirty = run(f"{kind}-git-status", ["git", "status", "--porcelain"], root)
        product["source_dirty"] = bool(dirty.strip())
        common = ["--locked", "--manifest-path", str(manifest), "--target-dir", str(target),
                  "--target", report["target"]] + (["--offline"] if args.offline else [])
        run(f"{kind}-fmt", ["cargo", "fmt", "--manifest-path", str(manifest), "--", "--check"], root)
        built, _ = run(f"{kind}-build", ["cargo", "build", *common, "--bin", binary], root)
        product["build"] = "PASS" if built else "FAIL"
        if not built:
            save()
            continue
        executable = target / report["target"] / "debug" / f"{binary}.exe"
        product["executable"] = str(executable)
        product["executable_sha256"] = sha256(executable)
        ok, marker = run(f"{kind}-marker", [str(executable), "--windows-service-capabilities"], root, timeout=15)
        try:
            product["capabilities"] = json.loads(marker)
        except ValueError:
            product["capabilities"] = None
        product["marker"] = "PASS" if ok and product["capabilities"] == {
            "schema": 1, "component": kind, "service_entrypoint": True} else "FAIL"
        run(f"{kind}-version", [str(executable), "--version"], root, timeout=15)
        for index, pattern in enumerate(filters):
            selection = ["--lib"] if kind == "broker" and pattern == "configuration::tests" else ["--bin", binary]
            run(f"{kind}-tests-{index + 1}", ["cargo", "test", *common, *selection, pattern], root, tests=True)
        run(f"{kind}-clippy", ["cargo", "clippy", *common, "--all-targets", "--", "-D", "warnings"], root)
        fixture = output / kind
        fixture.mkdir()
        config = fixture / "config.toml"
        config.write_text("version = 1\n", encoding="utf-8")
        service = "xmqr-client-default" if kind == "client" else f"xmqr-{kind}"
        run(f"{kind}-reject-relative-config", [str(executable), "--windows-service", service,
            str(fixture), "--config", "relative.toml"], root, expected=(1, 2), timeout=15,
            contains="--windows-service")
        # This invokes the real dispatcher outside SCM; it must not start runtime.
        run(f"{kind}-outside-scm", [str(executable), "--windows-service", service,
            str(fixture), "--config", str(config)], root, expected=(1,), timeout=15,
            contains="dispatcher" if kind == "client" else "1063")
        if kind == "broker":
            config.write_text('version = 1\n[broker]\nmode = "open-lab"\nbind = "127.0.0.1:0"\nstate_dir = "state"\n', encoding="utf-8")
            run("broker-native-storage-negative", [str(executable)], root, expected=(1,),
                extra_env={"MQTT_CONFIG": str(config)}, contains="durable directory fsync is supported on Unix targets only", timeout=15)
        elif kind == "admin":
            config.write_text('version = 1\nbind = "127.0.0.1:19080"\nmonitor = "127.0.0.1:19090"\ntoken_file = "token"\n', encoding="utf-8")
            run("admin-native-token-negative", [str(executable), "serve", "--config", str(config)], root,
                expected=(1,), contains="private token files require Unix", timeout=15)
        product["sources_unchanged_during_proof"] = before == sources(root)
        save()
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["builds_and_markers_pass"] = all(p["build"] == "PASS" and p["marker"] == "PASS"
        and p.get("sources_unchanged_during_proof", False) for p in report["products"].values())
    report["all_executed_checks_pass"] = report["builds_and_markers_pass"] and all(c["status"] == "PASS" for c in report["commands"])
    save()
    print(f"Report: {output / 'report.json'}", flush=True)
    return 0 if report["all_executed_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
