#!/usr/bin/env python3
"""P261: real CLI argument checks that stop at a missing password before networking."""
import argparse
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import tempfile


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def invoke(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=20)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=pathlib.Path,
                        default=pathlib.Path(__file__).with_name("install_oracle_x86.sh"))
    parser.add_argument("--client", default="/usr/bin/mqtt-client")
    parser.add_argument("--skip-other-versions", action="store_true")
    parser.add_argument("--integrity-only", action="store_true")
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args()
    source = args.script.read_text(encoding="utf-8")
    version_match = re.search(r"^INSTALLER_VERSION='([^']+)'$", source, re.M)
    require(version_match is not None, "Versao do instalador ausente")
    report = {"installer_version": version_match[1], "integrity": "NOT_RUN",
              "versions": {}, "parser_cases": []}
    manifest_path = args.script.parent / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        require(manifest["version"] == report["installer_version"], "Versoes divergentes")
        for name, expected in manifest["files"].items():
            path = args.script.parent / name
            require(path.parent == args.script.parent and not path.is_symlink(),
                    "Caminho de pacote invalido")
            require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                    f"Integridade divergente: {name}")
        report["integrity"] = "PASS"
    require(not args.integrity_only or report["integrity"] == "PASS",
            "Manifesto obrigatorio para --integrity-only")
    if not args.integrity_only:
        expectations = re.findall(
            r"\[\[ \$\(/usr/bin/([a-z-]+) --version\) == '([^']+)' \]\]", source)
        require(len(expectations) == 4, "Exige quatro verificacoes de versao")
        for executable, expected in expectations:
            if args.skip_other_versions and executable != "mqtt-client":
                continue
            binary = args.client if executable == "mqtt-client" else f"/usr/bin/{executable}"
            code, stdout, _ = invoke([binary, "--version"])
            require(code == 0 and stdout == expected,
                    f"Versao inesperada: {executable}: {stdout!r}")
            report["versions"][executable] = stdout

        common_match = re.search(r"client_args=\((.*?)\)\nrun_client\(\)", source, re.S)
        require(common_match is not None, "Argumentos comuns nao encontrados")
        common = shlex.split(common_match[1])
        cases = re.findall(
            r'\b(pub|sub)\s+"\$\{(?:client_args|negative_args)\[@\]\}"\s+--client-id\s+([\w-]+)', source)
        require(len(cases) == 5, "Exige cinco comandos de smoke MQTT")
        with tempfile.TemporaryDirectory(prefix="xmqr-cli-preflight-") as directory:
            absent = pathlib.Path(directory) / "missing-password"
            require(not absent.exists(), "Senha ficticia deve permanecer inexistente")
            for flag in ("--ca", "--cert", "--key", "--password-file"):
                common[common.index(flag) + 1] = str(absent)
            for command, client_id in cases:
                require(1 <= len(client_id) <= 23 and client_id.isascii(),
                        f"Client ID incompativel com MQTT3.1.1: {client_id}")
                tail = ["--topic", "xmqr/health", "--client-id", client_id]
                if command == "pub":
                    tail += ["--message", "XMQR-PARSER-PROBE", "--retain", "true"]
                else:
                    tail += ["--count", "1", "--output", "raw"]
                code, _, stderr = invoke([args.client, command, *common, *tail])
                require(code == 2 and "nao foi possivel ler a senha MQTT com seguranca" in stderr,
                        f"Parser recusou {client_id}: {stderr.splitlines()[:1]}")
                report["parser_cases"].append({"id": client_id, "result": "PASS"})
            code, _, stderr = invoke([args.client, "pub", *common, "--topic", "xmqr/health",
                                      "--message", "XMQR-PARSER-PROBE", "--client-id", "x" * 24])
            require(code == 2 and "--client-id deve ter 1 a 23" in stderr,
                    "Controle negativo ID24 nao comprovou recusa do parser")
            report["parser_cases"].append({"id": "negative-24-characters", "result": "PASS"})
    report["status"] = "PASS"
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("INTEGRITY_PASS" if args.integrity_only else
          f"CLI_PREFLIGHT_PASS cases={len(report['parser_cases'])} versions={len(report['versions'])}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"VERIFICACAO FALHOU: {error}") from error
