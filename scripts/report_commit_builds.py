"""P76: relatórios de compilação e ZIP com evidências por snapshot."""

import argparse
from collections import Counter
import csv
import hashlib
import html
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parent / "docs/curso-udemy/versoes-github"
PLATFORMS = ("windows", "ubuntu26")
PHASES = ("build", "check")


def correction(row):
    if row["status"] == "PASS":
        return "Nenhuma correção de compilação necessária para este comando no ambiente verificado."
    category = row["categoria"]
    if category == "LOCKFILE":
        return "Em uma branch de correção, comparar Cargo.toml e Cargo.lock. Conferir se o lock existe e corresponde ao manifest. Se a mudança de dependência for intencional, gerar/revisar um novo lock nessa branch e repetir build --locked e check --all-targets. Preservar o snapshot original."
    if category == "DEPENDENCIA_OU_REDE":
        return "Conferir o log de resolução, a conexão e o acesso ao registry. Executar cargo fetch --locked no ambiente em questão e repetir o comando. Falta de cache/rede não comprova defeito no código; não usar cargo update para contornar isso."
    if category == "FERRAMENTA_OU_RECURSO":
        return "O log indica ferramenta ou recurso ausente: conferir linker/C compiler/CMake ou espaço livre, conforme a mensagem específica. Preparar o ambiente correspondente ao alvo, manter o lock e repetir. Não é prova de erro Rust até resolver o pré-requisito."
    if category == "TEMPO_LIMITE":
        return "Conferir o log e processos de compilação da tarefa. Repetir em executor com recursos disponíveis e limite maior. Não classificar timeout como erro do código."
    if any("std::os::unix" in text or "unresolved import" in text for text in row["diagnosticos"]) and row["plataforma"] == "windows":
        return "Localizar o import e seus usos no arquivo/linha do diagnóstico. Separar código Unix com cfg(unix) e definir comportamento Windows explícito, preservando durabilidade e permissões. Não substituir fsync/permissões Unix por sucesso fictício. Repetir Windows e Linux em uma branch nova."
    return "Abrir o log completo, localizar arquivo/linha e código de erro Rust. Reproduzir nesta versão isolada; preparar prompt de correção e uma branch a partir do commit. Corrigir a API/tipo/linkagem indicada e repetir build e check nos dois ambientes. Não reescrever tags ou fontes históricas."


def build(run_id):
    folder = ARTIFACTS / "compilacao" / run_id
    original = ARTIFACTS / "todos-os-commits-broker-client.zip"
    catalogue = json.loads((ARTIFACTS / "indice.json").read_text(encoding="utf-8"))
    source_digest = hashlib.sha256(original.read_bytes()).hexdigest()
    expected_packages = {(item["repositorio"], item["commit"], str(PurePosixPath(name).parent)) for item in catalogue for name in item["sha256_fontes"] if PurePosixPath(name).name == "Cargo.toml"}
    records, environments, all_rows = {}, {}, []
    for platform in PLATFORMS:
        for phase in PHASES:
            file = folder / (platform + ("-check" if phase == "check" else "") + ".json")
            data = json.loads(file.read_text(encoding="utf-8"))
            if not data.get("finalizado") or data["zip_sha256"] != source_digest:
                raise ValueError(f"Execução incompleta ou ZIP divergente: {file}")
            got = {(row["repositorio"], row["commit"], row["pacote"]) for row in data["resultados"]}
            if got != expected_packages or len(got) != len(data["resultados"]):
                raise ValueError(f"Pacotes não cobertos integralmente: {file}")
            environments[platform + "-" + phase] = {key: value for key, value in data.items() if key != "resultados"}
            for row in data["resultados"]:
                row = {**row, "fase": phase, "passos": correction(row)}
                final = row["tentativas"][-1]
                expected_action = "build" if phase == "build" else "check"
                if expected_action not in final["comando"] or "--locked" not in final["comando"]:
                    raise ValueError("Comando não corresponde à fase")
                if row["status"] == "PASS" and final["exit_code"] != 0:
                    raise ValueError("PASS incompatível com exit code")
                for attempt in row["tentativas"]:
                    log = folder / attempt["log"]
                    if not log.is_file() or not row["hashes_fontes_conferidos"]:
                        raise ValueError("Log ou verificação das fontes ausente")
                records[(row["repositorio"], row["commit"], row["pacote"], platform, phase)] = row
                all_rows.append(row)
    failures = [row for row in all_rows if row["status"] != "PASS"]
    warning_rows = [row for row in all_rows if any(line.startswith("warning:") and "generated" not in line for line in row["diagnosticos"])]
    summary = {"data": "2026-10-12", "run_id": run_id, "snapshots": len(catalogue), "pacotes_por_ambiente": len(expected_packages), "comandos_registrados": len(all_rows), "zip_original_sha256": source_digest, "ambientes": environments, "contagem": dict(Counter(row["status"] for row in all_rows)), "comandos_com_avisos": len(warning_rows), "falhas_ou_bloqueios": failures}
    (folder / "resumo.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "resultados.json").write_text(json.dumps(all_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    table = []
    per_version = {}
    for item in catalogue:
        key = (item["repositorio"], item["commit"])
        main = [records[(*key, ".", platform, phase)] for platform in PLATFORMS for phase in PHASES]
        extras = [row for row in all_rows if (row["repositorio"], row["commit"]) == key and row["papel"] != "principal"]
        table.append({"repositorio": key[0], "commit": key[1], "versao": item["versao"], "prompts": ", ".join(item["prompts_relacionados"]), "windows_build": main[0]["status"], "windows_check": main[1]["status"], "ubuntu_build": main[2]["status"], "ubuntu_check": main[3]["status"], "auxiliares": "Todos PASS" if extras and all(row["status"] == "PASS" for row in extras) else "Não há" if not extras else "Consultar detalhes", "assunto": item["assunto"]})
        lines = [f"# Compilação — {key[0]} {key[1][:7]}", "", "Verificação P76 em2026-10-12. Fontes do snapshotP75 preservadas byte a byte.", "", f"Versão {item['versao']}; prompts relacionados: {', '.join(item['prompts_relacionados']) or 'Não comprovados'}.", "", "Windows: Rust/Cargo1.98.1 x86_64 MSVC. Ubuntu26.04 WSL: Rust/Cargo1.99.0 x86_64 Linux.", "", "| Pacote | Papel | Ambiente | Comando | Resultado | Exit code |", "| --- | --- | --- | --- | --- | --- |"]
        local_rows = main + extras
        for row in local_rows:
            lines.append(f"| {row['pacote']} | {row['papel']} | {row['plataforma']} | {row['fase']} | {row['status']} | {row['tentativas'][-1]['exit_code']} |")
        lines += ["", "## Logs e passos por comando", ""]
        for row in local_rows:
            lines += [f"### {row['plataforma']} / {row['fase']} / {row['pacote']}", "", row["passos"], ""]
            for attempt in row["tentativas"]:
                lines += ["Comando: `" + " ".join(attempt["comando"]) + "`", "", f"Exit{attempt['exit_code']}; duração{attempt['duracao_segundos']}s. [Log completo](../../relatorios-compilacao/{attempt['log']}).", ""]
            if row["status"] != "PASS":
                lines += ["```text", "\n".join(row["diagnosticos"]), "```", ""]
            elif any(line.startswith("warning:") and "generated" not in line for line in row["diagnosticos"]):
                lines += ["Avisos não impediram este comando:", "", "```text", "\n".join(row["diagnosticos"]), "```", "", "Ajuste opcional em branch nova: conferir imports/constantes sem uso e se são exclusivos Unix. Aplicar cfg(unix) quando apropriado, sem remover garantias de segurança/durabilidade. Repetir fmt, build/check e Clippy nos ambientes afetados; preservar o snapshot histórico.", ""]
        lines += ["## Como repetir", "", "1. Extraia o ZIP em uma pasta de estudo e abra codigo/ desta versão.", "2. Confira `rustc --version` e `cargo --version`. Use ambiente equivalente ao indicado acima.", "3. Execute `cargo build --locked --bins` para gerar os executáveis.", "4. Execute `cargo check --locked --all-targets` para conferir os tipos nos demais alvos.", "5. Para cada pacote adicional, entre na pasta listada e repita os comandos.", "", "As execuções usaram cacheoffline primeiro, jobs2, perfildev com debug0 e incremental0, targets isolados por plataforma. Não modificaram Cargo.lock nem código. As variáveis de perfil foram definidas só nos processos da tarefa.", "", "## O que esse resultado significa", "", "Build gera os executáveis do pacote. Check verifica também biblioteca, testes, exemplos e benchmarks existentes sem gerar todos os executáveis finais desses alvos. Não foram executados testes, serviços ou clientes MQTT nesta verificação. Recursos condicionais seguem as features padrão do Cargo.toml; não houve matriz all-features ou MSRV exato1.88.", "", "Compilar não confirma execução de persistência/administrador no Windows nem conclusão funcional. PendênciasP55/C37 anteriores continuam descritas no README histórico; os marcos de aceite posteriores são separados dos resultados de compilaçãoP76.", "", "Fontes oficiais: [Cargo build](https://doc.rust-lang.org/cargo/commands/cargo-build.html) e [Cargo check](https://doc.rust-lang.org/cargo/commands/cargo-check.html).", ""]
        per_version[item["pasta"] + "/COMPILACAO.md"] = "\n".join(lines).encode()
    csv_text = io.StringIO(newline="")
    writer = csv.DictWriter(csv_text, fieldnames=list(table[0]), delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(table)
    (folder / "resultados.csv").write_text(csv_text.getvalue(), encoding="utf-8-sig", newline="\n")
    markdown = ["# Compilação das versões históricas", "", "Verificação realP76 em2026-10-12, sobre os78 snapshots exportados porP75.", "", "WindowsRust1.98.1/MSVC e Ubuntu26.04WSL/Rust1.99.0. Build dos binários e check dos demais alvos separados; testes e execução MQTT não realizados.", "", f"Pacotes por ambiente: {len(expected_packages)}. Comandos build/check registrados nos dois ambientes: {len(all_rows)}. Resultados: {summary['contagem']}.", "", "| Projeto | Commit | Versão | Prompts | Build Windows | Check Windows | Build Ubuntu | Check Ubuntu | Auxiliares |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in table:
        markdown.append("| " + " | ".join(str(row[key]) for key in ("repositorio", "commit", "versao", "prompts", "windows_build", "windows_check", "ubuntu_build", "ubuntu_check", "auxiliares")) + " |")
    markdown += ["", "## Passos para os que não compilaram", ""]
    if failures:
        for row in failures:
            markdown += [f"- {row['repositorio']} {row['commit'][:7]}, {row['pacote']}, {row['plataforma']} {row['fase']}: {row['status']}/{row['categoria']}. {row['passos']}"]
    else:
        markdown += ["Nenhuma falha de build/check foi encontrada nesses ambientes e alvos. Não há correção de compilação a aplicar nos snapshots. Para confirmar funcionamento, é necessário executar os testes e integrações pertinentes, em tarefa/ambiente isolados; esta verificação não substitui aceite funcional."]
    markdown += ["", "## Avisos do compilador", "", f"{len(warning_rows)} comandos emitiram avisos, sem falha de build/check. Logs e COMPILACAO.md de cada versão registram os detalhes. Há imports/constantes sem uso em versões antigas no Windows; avaliar cfg(unix) em branch de melhoria e repetir fmt/Clippy/build/check, sem reescrever snapshots.", "", "Leia os READMEs históricos e PENDENCIAS.md: commits de preparação/implementação parcial podem compilar normalmente. O primeiro commit de cada repositório já continha um projeto; não se trata de criação do zero comprovada por um prompt.", "", "Para repetir: na pasta codigo/ da versão, cargo build --locked --bins e cargo check --locked --all-targets. Para compilar cada pacote didático/auxiliar, entrar na sua pasta e repetir. Dependências travadas por Cargo.lock; --offline somente se o cache está disponível.", "", "Fontes: [Cargo build](https://doc.rust-lang.org/cargo/commands/cargo-build.html), [Cargo check](https://doc.rust-lang.org/cargo/commands/cargo-check.html)."]
    (folder / "RELATORIO.md").write_text("\n".join(markdown), encoding="utf-8")
    esc = html.escape
    rows = []
    for row in table:
        cols = [row[key] for key in ("repositorio", "commit", "versao", "prompts", "windows_build", "windows_check", "ubuntu_build", "ubuntu_check", "auxiliares", "assunto")]
        cells = "".join(f"<td class='{value if value in {'PASS','FAIL','BLOCKED'} else ''}'>{esc(str(value))}</td>" for value in cols)
        rows.append(f"<tr>{cells}</tr>")
    page = "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Compilação de78 commits</title><style>body{font:16px/1.6 system-ui;background:#f4f7fb;color:#182a40;margin:24px}table{border-collapse:collapse;background:white}th,td{border:1px solid #c8d4e3;padding:10px;text-align:left;vertical-align:top}.PASS{color:#126335;font-weight:bold}.FAIL{color:#ad2020;font-weight:bold}.BLOCKED{color:#865900;font-weight:bold}.scroll{overflow:auto}input{font:inherit;padding:10px;width:min(90%,560px)}</style><h1>Compilação dos78 commits</h1>" + f"<p>{len(expected_packages)} pacotes por ambiente; {len(all_rows)} verificações build/check. {esc(str(summary['contagem']))}.</p>" + "<p>WindowsRust1.98.1/MSVC e Ubuntu26.04WSL/Rust1.99.0. Foram gerados os binários e conferidos os tipos dos demais alvos. Testes e serviços não foram executados.</p><p><a href='RELATORIO.md'>Relatório e passos</a> · <a href='resultados.csv'>Tabela CSV</a> · <a href='resultados.json'>Evidências JSON</a></p><label>Buscar commit, prompt ou versão<br><input id='search' placeholder='Exemplo: P55, C37, 0.11.2'></label><p>Compilar não significa terminar uma funcionalidade. Consulte também o README e os registros históricos da versão.</p><div class='scroll'><table><thead><tr><th>Projeto</th><th>Commit</th><th>Versão</th><th>Prompts</th><th>Build Windows</th><th>Check Windows</th><th>Build Ubuntu</th><th>Check Ubuntu</th><th>Auxiliares</th><th>Alteração</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div><script>document.getElementById('search').addEventListener('input',function(){const value=this.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(value));});</script></html>"
    (folder / "index.html").write_text(page, encoding="utf-8")
    # Um ZIP leve só de evidências e outro com fontes+resultados; não incluir targets.
    report_files = {path.relative_to(folder).as_posix(): path.read_bytes() for path in folder.rglob("*") if path.is_file() and path.suffix not in {".zip", ".sha256", ".tmp"}}
    for name in list(report_files):
        if ".." in PurePosixPath(name).parts:
            raise ValueError("Caminho de relatório inválido")
    results_zip = folder / "resultados-compilacao.zip"
    with zipfile.ZipFile(results_zip, "w", zipfile.ZIP_DEFLATED) as output:
        for name, content in report_files.items():
            output.writestr("relatorios-compilacao/" + name, content)
        for name, content in per_version.items():
            output.writestr(name, content)
        output.writestr("index.html", b"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Relatorio de compilacao</title><a href='relatorios-compilacao/index.html'>Abrir resultados dos78 commits</a></html>")
    target = ARTIFACTS / "todos-os-commits-com-compilacao.zip"
    hashes = {}
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(target.with_suffix(".tmp"), "w", zipfile.ZIP_DEFLATED, allowZip64=True) as output:
        def put(name, content):
            if name in hashes:
                raise ValueError(f"Entrada duplicada: {name}")
            output.writestr(name, content)
            hashes[name] = hashlib.sha256(content).hexdigest()
        for name in source.namelist():
            put(name, source.read(name))
        for name, content in per_version.items():
            put(name, content)
        for name, content in report_files.items():
            put("relatorios-compilacao/" + name, content)
        put("COMPILACAO.html", b"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Resultado de compilacao</title><h1>Resultados por commit</h1><p><a href='relatorios-compilacao/index.html'>Abrir relatorio de compilacao dos78 commits</a></p><p>Cada pasta de versao tem COMPILACAO.md com comandos, logs e passos. README.md e codigo/ originais pertencem a exportacao P75 e permanecem intactos.</p></html>")
        output.writestr("SHA256SUMS-COM-COMPILACAO.txt", "".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items())).encode())
    for archive_path in (results_zip, target.with_suffix(".tmp")):
        with zipfile.ZipFile(archive_path) as verified:
            if verified.testzip():
                raise ValueError("CRC inválido")
            names = set(verified.namelist())
            for name in per_version:
                for link in re.findall(r"\]\(([^)]+)\)", verified.read(name).decode("utf-8")):
                    if "://" in link:
                        continue
                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), link))
                    if resolved not in names:
                        raise ValueError(f"Link de compilação ausente: {name}: {link}")
            for name in ["relatorios-compilacao/index.html"]:
                for link in re.findall(r"href='([^']+)'", verified.read(name).decode("utf-8")):
                    if "relatorios-compilacao/" + link not in names:
                        raise ValueError(f"Link de relatório ausente: {link}")
            if archive_path != results_zip:
                for name, digest in hashes.items():
                    if hashlib.sha256(verified.read(name)).hexdigest() != digest:
                        raise ValueError(f"Hash divergente: {name}")
    target.with_suffix(".tmp").replace(target)
    for file in (target, results_zip):
        file.with_suffix(file.suffix + ".sha256").write_text(hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.name + "\n", encoding="utf-8")
    versioned = ROOT / "docs/results/p76-compile-summary.json"
    versioned.parent.mkdir(parents=True, exist_ok=True)
    versioned.write_text(json.dumps({key: value for key, value in summary.items() if key != "ambientes"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (versioned.parent / "p76-compile-matrix.csv").write_text(csv_text.getvalue(), encoding="utf-8-sig", newline="\n")
    print(f"PASS relatórios: {len(catalogue)} commits, {len(all_rows)} verificações; integridade ZIP/fontes preservada", flush=True)
    print(f"Resumo: {summary['contagem']}; pacote: {target}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    build(parser.parse_args().run_id)
