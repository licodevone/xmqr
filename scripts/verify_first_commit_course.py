"""P77: validar checkpoints reconstruídos, sem tocar no broker instalado."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import time
import zipfile

from verify_commit_builds import run_command, verify_sources, write_json
from build_first_commit_course import ROOT, OUTPUT, COMMIT


def worker(run_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("Identificador de execução deve conter apenas letras, números, hífen e sublinhado")
    platform = "windows" if os.name == "nt" else "ubuntu26"
    workspace = ROOT / "target" / run_id / platform if os.name == "nt" else Path.home() / ".cache/xmqr-history" / run_id / platform
    workspace.mkdir(parents=True, exist_ok=True)
    logs = OUTPUT / "validacao" / platform
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(CARGO_TARGET_DIR=str(workspace / "cargo-target"), CARGO_TERM_COLOR="never", CARGO_BUILD_JOBS="2", CARGO_PROFILE_DEV_DEBUG="0", CARGO_INCREMENTAL="0")
    result = {"plataforma": platform, "rustc": subprocess.check_output(["rustc", "-vV"], text=True), "cargo": subprocess.check_output(["cargo", "-vV"], text=True), "run_id": run_id, "commit_destino": COMMIT, "etapas": [], "gates_finais": []}
    for entry in json.loads((OUTPUT / "indice.json").read_text(encoding="utf-8")):
        source = workspace / entry["etapa"]
        if source.exists():
            raise ValueError("Use novo run-id; não sobrescrever cópia de validação")
        source.mkdir()
        with zipfile.ZipFile(OUTPUT / entry["zip"]) as archive:
            for name in entry["sha256_fontes"]:
                file = source / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(archive.read("codigo/" + name))
        verify_sources(source, entry["sha256_fontes"])
        commands = [["cargo", "build", "--locked", "--offline", "--bins"], ["cargo", "check", "--locked", "--offline", "--all-targets"]]
        rows = []
        for number, command in enumerate(commands):
            log = logs / (entry["etapa"] + ("-build.log" if number == 0 else "-check.log"))
            print(f"[{platform}] {entry['etapa']} {' '.join(command)}", flush=True)
            row = run_command(command, source, env, log)
            row["log"] = log.relative_to(OUTPUT).as_posix()
            rows.append(row)
            verify_sources(source, entry["sha256_fontes"])
        result["etapas"].append({"id": entry["etapa"], "status": "PASS" if all(row["exit_code"] == 0 for row in rows) else "FAIL", "comandos": rows, "hashes": "PASS"})
        write_json(OUTPUT / ("VALIDACAO-" + platform + ".json"), result)
        if any(row["exit_code"] != 0 for row in rows):
            print(f"[{platform}] FALHA {entry['etapa']} — preservada para diagnóstico", flush=True)
        if entry["etapa"] == "R01":
            binary = workspace / "cargo-target/debug" / ("mqtt-broker.exe" if os.name == "nt" else "mqtt-broker")
            printed = subprocess.check_output([str(binary)], env=env, cwd=source, text=True).strip()
            result["r01_impressao"] = printed
            if printed != "XMQR: estrutura inicial em Rust.":
                raise ValueError("R01 não imprimiu resultado esperado")
        if entry["etapa"] == "R10" and os.name != "nt":
            for label, command in [("fmt", ["cargo", "fmt", "--all", "--", "--check"]), ("test", ["cargo", "test", "--locked", "--offline"]), ("clippy", ["cargo", "clippy", "--locked", "--offline", "--all-targets", "--", "-D", "warnings"])]:
                print(f"[{platform}] R10 gate {label}", flush=True)
                log = logs / ("R10-" + label + ".log")
                row = run_command(command, source, env, log)
                row.update(gate=label, log=log.relative_to(OUTPUT).as_posix())
                result["gates_finais"].append(row)
                verify_sources(source, entry["sha256_fontes"])
            result["pubsub"] = pubsub(workspace, source, env, logs)
        if entry["etapa"] == "R10":
            # Repositório de ensaio dentro da cópia isolada; nenhuma configuração global.
            for command in [["git", "init", "--initial-branch=main"], ["git", "-c", "core.autocrlf=false", "add", "."], ["git", "-c", "user.name=Validação P77", "-c", "user.email=p77@example.invalid", "commit", "--no-gpg-sign", "-m", "feat: reconstruir XMQR 0.3.0"]]:
                subprocess.run(command, cwd=source, check=True, capture_output=True)
            tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=source, text=True).strip()
            expected_tree = subprocess.check_output(["git", "rev-parse", COMMIT + "^{tree}"], cwd=ROOT, text=True).strip()
            if tree != expected_tree:
                raise ValueError("Tree do primeiro commit do aluno difere do histórico")
            result["commit_ensaio"] = {"tree": tree, "conteudo_igual_ao_historico": True, "sha_novo": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()}
    result["finalizado"] = True
    write_json(OUTPUT / ("VALIDACAO-" + platform + ".json"), result)
    print(f"[{platform}] Finalizado: {len(result['etapas'])} etapas e commit de ensaio", flush=True)


def pubsub(workspace, source, env, logs):
    laboratory = env.copy()
    for name in list(laboratory):
        if name.startswith("MQTT_"):
            del laboratory[name]
    state = workspace / "estado-laboratorio"
    state.mkdir(mode=0o700)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    laboratory.update(MQTT_MODE="open-lab", MQTT_BIND=f"127.0.0.1:{port}", MQTT_STATE_DIR=str(state), RUST_LOG="info")
    binary_dir = workspace / "cargo-target/debug"
    broker_log = logs / "R10-broker-lab.log"
    sub_log = logs / "R10-sub-lab.log"
    processes = []
    try:
        with broker_log.open("wb") as bstream, sub_log.open("wb") as sstream:
            broker = subprocess.Popen([str(binary_dir / "mqtt-broker")], cwd=source, env=laboratory, stdout=bstream, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(broker)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if broker.poll() is not None:
                    raise ValueError("Broker do laboratório encerrou antes do teste")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                raise ValueError("Listener do laboratório indisponível")
            common = ["--open-lab", "--topic", "aula/mensagem", "--host", "127.0.0.1", "--port", str(port), "--qos", "0"]
            subscriber = subprocess.Popen([str(binary_dir / "mqtt-client"), "sub", *common, "--client-id", "curso-r10-sub", "--count", "1"], cwd=source, env=laboratory, stdout=sstream, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(subscriber)
            time.sleep(0.4)
            publisher = subprocess.run([str(binary_dir / "mqtt-client"), "pub", *common, "--client-id", "curso-r10-pub", "--message", "Ola, XMQR!"], cwd=source, env=laboratory, capture_output=True, timeout=12)
            (logs / "R10-pub-lab.log").write_bytes(publisher.stdout + publisher.stderr)
            subscriber.wait(timeout=12)
            if publisher.returncode != 0 or subscriber.returncode != 0:
                raise ValueError("Pub/sub retornou exit code de erro")
        if "Ola, XMQR!" not in sub_log.read_text():
            raise ValueError("Payload de ensaio não recebido")
        return {"status": "PASS", "porta_loopback": port, "estado_isolado": str(state), "payload_ficticio_recebido": True}
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    worker(parser.parse_args().run_id)
