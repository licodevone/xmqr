"""P76: compilar os snapshots do ZIP P75 sem modificar as fontes históricas."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parent / "docs/curso-udemy/versoes-github"


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_command(command, cwd, env, log, timeout=600):
    started = time.monotonic()
    settings = {"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    with log.open("wb") as stream:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, **settings)
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    return {"comando": command, "cwd": str(cwd), "exit_code": code, "timeout": timed_out, "duracao_segundos": round(time.monotonic() - started, 2)}


def classify(text, attempt):
    if attempt["timeout"]:
        return "BLOCKED", "TEMPO_LIMITE"
    if attempt["exit_code"] == 0:
        return "PASS", "COMPILADO"
    if any(item in text for item in ["lock file needs to be updated", "lockfile needs to be updated", "lock file of", "the lock file"]):
        return "FAIL", "LOCKFILE"
    if re.search(r"no matching package named|failed to download|failed to get .* as a dependency|could not resolve host|failed to fetch|network failure|unable to update registry", text, re.I):
        return "BLOCKED", "DEPENDENCIA_OU_REDE"
    if re.search(r"linker .*not found|link.exe.*not found|cmake.*not found|failed to find tool|could not find.*compiler|No space left|os error 28", text, re.I):
        return "BLOCKED", "FERRAMENTA_OU_RECURSO"
    if "error[E" in text or "could not compile" in text or "error: linking" in text:
        return "FAIL", "CODIGO_OU_LINKER"
    return "FAIL", "OUTRO_ERRO_BUILD"


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Caminho inválido: {name}")
    return path


def verify_sources(folder, hashes):
    for name, expected in hashes.items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Fonte alterada: {folder}/{name}")


def worker(run_id, phase):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("Identificador de execução inválido")
    platform = "windows" if os.name == "nt" else "ubuntu26"
    reports = ARTIFACTS / "compilacao" / run_id
    logs = reports / "logs" / platform
    logs.mkdir(parents=True, exist_ok=True)
    workspace = (ROOT / "target" / run_id / platform) if os.name == "nt" else (Path.home() / ".cache/xmqr-history" / run_id / platform)
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "cargo-target"
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(target)
    env["CARGO_TERM_COLOR"] = "never"
    # Controle só deste processo: limitar memória/CPU sem mudar Cargo global.
    env["CARGO_BUILD_JOBS"] = "2"
    env["CARGO_PROFILE_DEV_DEBUG"] = "0"
    env["CARGO_INCREMENTAL"] = "0"
    env["LC_ALL"] = "C.UTF-8" if os.name != "nt" else env.get("LC_ALL", "C")
    versions = {}
    for tool in ("rustc", "cargo"):
        versions[tool] = subprocess.check_output([tool, "-vV"], env=env, text=True).strip()
    if os.name != "nt":
        versions["distribuicao"] = Path("/etc/os-release").read_text()
    archive_path = ARTIFACTS / "todos-os-commits-broker-client.zip"
    expected = (ARTIFACTS / (archive_path.name + ".sha256")).read_text().split()[0]
    archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if expected != archive_hash:
        raise ValueError("ZIP de entrada divergente do checksum")
    cargo_action = "build" if phase == "build" else "check"
    cargo_targets = "--bins" if phase == "build" else "--all-targets"
    result = {"run_id": run_id, "plataforma": platform, "fase": phase, "ferramentas": versions, "zip_sha256": archive_hash, "workspace": str(workspace), "target": str(target), "escopo": f"cargo {cargo_action} --locked {cargo_targets}; sem execução dos binários ou testes", "ambiente_build": {key: env[key] for key in ("CARGO_TARGET_DIR", "CARGO_BUILD_JOBS", "CARGO_PROFILE_DEV_DEBUG", "CARGO_INCREMENTAL")}, "resultados": []}
    output_json = reports / (platform + ("-check" if phase == "check" else "") + ".json")
    write_json(output_json, result)
    with zipfile.ZipFile(archive_path) as archive:
        catalogue = json.loads(archive.read("indice.json"))
        for position, snapshot in enumerate(catalogue, 1):
            project = snapshot["repositorio"]
            commit = snapshot["commit"]
            source = workspace / "snapshots" / project / commit[:7]
            if source.exists() and phase == "build":
                raise ValueError(f"Snapshot já existente; use novo run-id: {source}")
            hashes = snapshot["sha256_fontes"]
            if not source.exists():
                source.mkdir(parents=True)
                for name in hashes:
                    relative = safe_path(name)
                    destination = source.joinpath(*relative.parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(f"{snapshot['pasta']}/codigo/{name}"))
                    if os.name != "nt":
                        destination.chmod(0o755 if snapshot["modos_git"][name] == "100755" else 0o644)
            verify_sources(source, hashes)
            manifests = [name for name in hashes if PurePosixPath(name).name == "Cargo.toml"]
            manifests.sort(key=lambda name: (name != "Cargo.toml", name))
            for manifest in manifests:
                role = "principal" if manifest == "Cargo.toml" else "didatico" if manifest.startswith("curso/") else "auxiliar_validacao"
                package_path = str(PurePosixPath(manifest).parent)
                cwd = source / package_path
                slug = project + "-" + commit[:7] + "-" + package_path.replace("/", "_").replace(".", "root")
                if phase == "check":
                    slug += "-check"
                attempts = []
                print(f"[{platform}] {position}/{len(catalogue)} {project} {commit[:7]} {package_path}: iniciando", flush=True)
                command = ["cargo", cargo_action, "--locked", "--offline", cargo_targets, "--jobs", "2"]
                log = logs / (slug + "-offline.log")
                attempt = run_command(command, cwd, env, log)
                attempt["log"] = log.relative_to(reports).as_posix()
                attempts.append(attempt)
                text = log.read_text(encoding="utf-8", errors="replace")
                if attempt["exit_code"] != 0 and re.search(r"no matching package named|failed to download|offline|Unable to update", text, re.I) and not attempt["timeout"]:
                    command = ["cargo", cargo_action, "--locked", cargo_targets, "--jobs", "2"]
                    log = logs / (slug + "-online.log")
                    print(f"[{platform}] {commit[:7]}: tentando dependências online com lock preservado", flush=True)
                    attempt = run_command(command, cwd, env, log)
                    attempt["log"] = log.relative_to(reports).as_posix()
                    attempts.append(attempt)
                    text = log.read_text(encoding="utf-8", errors="replace")
                verify_sources(source, hashes)
                status, category = classify(text, attempt)
                errors = [line for line in text.splitlines() if re.match(r"(?:error(?:\[|:)|warning:|Caused by:|  -->|   -->)", line)][:40]
                row = {"repositorio": project, "commit": commit, "pasta_snapshot": snapshot["pasta"], "versao": snapshot["versao"], "prompts": snapshot["prompts_relacionados"], "pacote": package_path, "papel": role, "plataforma": platform, "fase": phase, "status": status, "categoria": category, "tentativas": attempts, "diagnosticos": errors, "hashes_fontes_conferidos": True}
                result["resultados"].append(row)
                write_json(output_json, result)
                print(f"[{platform}] {commit[:7]} {package_path}: {status} / {category}", flush=True)
    result["finalizado"] = True
    write_json(output_json, result)
    print(f"[{platform}] CONCLUÍDO: {len(result['resultados'])} compilações registradas em {output_json}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", choices=("build", "check"), default="build")
    args = parser.parse_args()
    worker(args.run_id, args.phase)
