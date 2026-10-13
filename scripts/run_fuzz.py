#!/usr/bin/env python3
"""P90: bounded synthetic mutational campaign; no nightly or global installs.

Linux only. Builds the normal library test executable, then runs one owned
process group per target/seed with a deadline and aggregate RSS watchdog.
Reports are runtime-generated evidence under ignored dist/fuzz, not corpus.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("frame", "decode", "fragment", "topics", "state", "router")


def positive(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def group_rss(group: int) -> int:
    """Only this driver's newly created Linux process group, never operator PID."""
    total = 0
    for candidate in Path("/proc").iterdir():
        if not candidate.name.isdecimal():
            continue
        try:
            fields = (candidate / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) != group:
                continue
            resident = int((candidate / "statm").read_text().split()[1])
            total += resident * os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError, IndexError):
            continue  # process exited while observing its public process counters
    return total


def revision() -> dict:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_snapshot() -> dict:
    paths = list((ROOT / "src").rglob("*.rs"))
    paths += [ROOT / "Cargo.toml", ROOT / "Cargo.lock", Path(__file__).resolve()]
    paths += list((ROOT / "tests" / "fuzz-corpus").iterdir())
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths) if path.is_file()}


def compile_test() -> Path:
    result = subprocess.run(
        ["cargo", "test", "--locked", "--lib", "--no-run", "--message-format=json"],
        cwd=ROOT, text=True, capture_output=True, timeout=300,
    )
    if result.returncode:
        sys.stderr.write(result.stderr)
        raise RuntimeError("library test compilation failed")
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if event.get("reason") == "compiler-artifact" and event.get("executable"):
            if event.get("profile", {}).get("test") and event["target"]["kind"] == ["lib"]:
                return Path(event["executable"]).resolve(strict=True)
    raise RuntimeError("Cargo did not return the library test executable")


def run_one(binary: Path, target: str, seed: int, args: argparse.Namespace, failures: Path) -> dict:
    env = os.environ.copy()
    env.update({
        "XMQR_FUZZ_SEED": str(seed), "XMQR_FUZZ_ITERATIONS": str(args.iterations),
        "XMQR_FUZZ_STATE_ITERATIONS": str(args.state_iterations),
        "XMQR_FUZZ_ROUTER_ITERATIONS": str(args.router_iterations),
        "XMQR_FUZZ_FAILURE_DIR": str(failures),
    })
    command = [str(binary), f"mqtt::codec::fuzz_tests::fuzz_{target}_campaign",
               "--exact", "--ignored", "--nocapture", "--test-threads=1"]
    started = time.monotonic()
    peak = 0
    gate = "PASS"
    with tempfile.TemporaryFile() as stream:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while process.poll() is None:
                peak = max(peak, group_rss(process.pid))
                if time.monotonic() - started > args.timeout:
                    gate = "TIMEOUT"
                    break
                if peak > args.rss_mib * 1024 * 1024:
                    gate = "RSS_LIMIT"
                    break
                time.sleep(0.02)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
        stream.seek(0)
        output = stream.read().decode("utf-8", errors="replace")
    report_lines = [line.partition("XMQR_FUZZ_RESULT ")[2] for line in output.splitlines()
                    if "XMQR_FUZZ_RESULT " in line]
    try:
        counts = json.loads(report_lines[0]) if len(report_lines) == 1 else None
    except json.JSONDecodeError:
        counts = None
    expected_cases = {"state": args.state_iterations, "router": args.router_iterations}.get(target, args.iterations)
    if counts is not None and (counts.get("target") != target or counts.get("seed") != seed
                               or counts.get("cases") != expected_cases):
        counts = None
    if process.returncode or counts is None:
        gate = "FAIL" if gate == "PASS" else gate
    result = {"status": gate, "target": target, "seed": seed,
              "exit_code": process.returncode, "elapsed_seconds": round(time.monotonic() - started, 4),
              "peak_sampled_group_rss_bytes": peak, "counts": counts}
    if gate != "PASS":
        # This output comes only from the test harness's synthetic inputs.
        log = failures / f"{target}-{seed}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(output)
        result["failure_log"] = str(log.relative_to(ROOT))
    print(f"{target} seed={seed}: {gate}; cases={counts['cases'] if counts else 'unknown'}; "
          f"duration={result['elapsed_seconds']}s; sampled_RSS={peak}B", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=positive, default=25_000)
    parser.add_argument("--state-iterations", type=positive, default=128)
    parser.add_argument("--router-iterations", type=positive, default=256)
    parser.add_argument("--seeds", type=positive, nargs="+", default=[151195649, 305419896, 11400714819323198485])
    parser.add_argument("--targets", choices=TARGETS, nargs="+", default=list(TARGETS))
    parser.add_argument("--timeout", type=positive, default=120)
    parser.add_argument("--rss-mib", type=positive, default=512)
    parser.add_argument("--output", type=Path, default=Path("dist/fuzz/p90.json"))
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Linux/WSL required; native Windows persistence is not certified")
    if args.iterations > 1_000_000 or args.state_iterations > 1024 or args.router_iterations > 4096:
        parser.error("iteration counts exceed harness bounds")
    if any(seed > 2**64 - 1 for seed in args.seeds):
        parser.error("seed must fit a nonzero u64")
    output = (ROOT / args.output).resolve()
    destination = ROOT / "dist" / "fuzz"
    if not output.is_relative_to(destination) or output == destination:
        parser.error("reports must remain within this repository's ignored dist/fuzz")
    output.parent.mkdir(parents=True, exist_ok=True)
    failures = output.parent / f"{output.stem}-failures"
    before = source_snapshot()
    binary = compile_test()
    if source_snapshot() != before:
        raise RuntimeError("source changed during compilation; rerun after source freeze")
    results = []
    started = time.monotonic()
    for seed in args.seeds:
        for target in args.targets:
            results.append(run_one(binary, target, seed, args, failures))
            if results[-1]["status"] != "PASS":
                break
        if results[-1]["status"] != "PASS":
            break
    stable_source = source_snapshot() == before
    evidence = {
        "schema": 1, "method": "seeded_mutational_stable_rust",
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": revision(), "platform": sys.platform,
        "rust": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "binary_sha256": digest(binary), "elapsed_seconds": round(time.monotonic() - started, 4),
        "source_sha256": before, "source_unchanged_during_campaign": stable_source,
        "limits": {"input_bytes": 65536, "timeout_seconds_per_target": args.timeout,
                   "sampled_group_rss_mib": args.rss_mib, "sample_interval_ms": 20},
        "corpus_sha256": {str(path.relative_to(ROOT)): digest(path)
                          for path in sorted((ROOT / "tests" / "fuzz-corpus").iterdir()) if path.is_file()},
        "results": results,
        "status": "PASS" if stable_source and len(results) == len(args.seeds) * len(args.targets)
                  and all(item["status"] == "PASS" for item in results) else "FAIL",
        "limitations": ["not coverage-guided", "no LibFuzzer/ASAN/nightly gate",
                        "sampled RSS, not instantaneous allocation instrumentation",
                        "finite synthetic campaign, not full conformance or production approval"],
    }
    output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"campaign={evidence['status']} report={output.relative_to(ROOT)}", flush=True)
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
