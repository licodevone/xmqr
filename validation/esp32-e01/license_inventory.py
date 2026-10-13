#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mechanical license-declaration inventory of this fixture, not the broker."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def document():
    result = subprocess.run([
        "cargo", "+esp", "metadata", "--locked", "--offline", "--format-version", "1",
        "--filter-platform", "xtensa-esp32-espidf"
    ], cwd=Path(__file__).resolve().parent, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError("locked fixture metadata unavailable")
    packages = sorted(json.loads(result.stdout)["packages"], key=lambda p: (p["name"], p["version"]))
    if any(not p.get("license") for p in packages):
        raise ValueError("license declaration missing")
    lines = ["# Licenças declaradas — fixture E01", "",
             "Gerado de Cargo.metadata locked/offline para xtensa-esp32-espidf.",
             "Inclui pacote próprio e dependências de build/plataforma do grafo.",
             "Preserva as expressões declaradas, inclusive sintaxe legada com `/`.",
             "Inventário não equivale a auditoria jurídica nem muda licenças para MIT.",
             "SDK ESP-IDF/toolchain têm licenças e componentes próprios fora deste grafo;",
             "preserve seus avisos ao distribuir. Nenhum firmware com senha será publicado.", "",
             f"Total de pacotes: {len(packages)}.", "",
             "| Pacote | Versão | Licença declarada |",
             "| --- | --- | --- |"]
    for p in packages:
        name = p["name"]
        label = f"[{name}](https://crates.io/crates/{name}/{p['version']})" if p["source"] else name
        lines.append(f"| {label} | {p['version']} | {p['license']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = Path(__file__).resolve().parent / "third-party-licenses.md"
    try:
        output = document()
        if args.check:
            if target.read_text(encoding="utf-8") != output:
                raise ValueError("fixture inventory out of date")
        else:
            target.write_text(output, encoding="utf-8")
        print("E01_LICENSE_DECLARATIONS_PASS")
    except Exception:
        print("E01_LICENSE_DECLARATIONS_FAILED", file=sys.stderr)
        sys.exit(1)
