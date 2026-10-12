"""P75: exportar todos os commits, com fontes intactas e evidência documental."""

import ast
import csv
from contextlib import nullcontext
import hashlib
import html
import io
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import subprocess
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "docs/curso-udemy/versoes-github"
ARCHIVE = "todos-os-commits-broker-client.zip"
REPOS = [(ROOT, "P", "broker"), (ROOT.parent / "xmqr-client", "C", "clients")]
# Apenas casos conferidos lendo os registros daquela versão. Não inferir aceite
# pela palavra "feat", pela existência de tag ou por notas históricas antigas.
AUDIT = {
    "b577dd0": ("Preparação: P55 ainda sem implementação", "P55-quotas-estado.md", "Implementação\nP55 e testes funcionais P55 NOT_RUN.", "d7b9d41", "Aceite agregado P61 em Ubuntu26/WSL"),
    "10e1b59": ("Implementação local; aceite Unix bloqueado", "P55-quotas-estado.md", "IMPLEMENTED_LOCAL / ACCEPTANCE_BLOCKED", "d7b9d41", "Aceite agregado P61 em Ubuntu26/WSL"),
    "d76c9e9": ("Correção intermediária; aceite Unix ainda necessário", "P55-quotas-estado.md", "### Aceite ainda necessário", "d7b9d41", "Aceite agregado P61 em Ubuntu26/WSL"),
    "49edfc2": ("Preparação do aceite final; fase 1 ainda aberta", "P55-quotas-estado.md", "Fase1 permanece aberta", "d7b9d41", "Aceite agregado P61 em Ubuntu26/WSL"),
    "5d1f742": ("Preparação: C37 ainda sem implementação", "C37-timeout-keepalive.md", "PREPARED, implementação NOT_RUN.", "6ee5aa8", "C37 aceito no escopo portátil; Ubuntu/fase1 pendentes naquele marco"),
}
ACCEPTED = {
    "d7b9d41": ("Aceite histórico declarado: fase 1 no Ubuntu26/WSL amd64", "P61-aceite-final-fase1.md", "PHASE1_ACCEPTED"),
    "6ee5aa8": ("Aceite histórico declarado: C37 portátil; fase 1/Ubuntu ainda pendentes", "C37-timeout-keepalive.md", "Marco aceito no escopo portátil C37"),
}


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo)


def safe(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Caminho inseguro: {name}")
    if path.suffix.lower() in {".key", ".pem", ".p12", ".pfx"} or path.name in {".env", "id_rsa", "id_ed25519"}:
        raise ValueError(f"Arquivo sensível: {name}")


def mapped_prompts():
    # Ler constantes sem executar o antigo gerador de pacotes.
    tree = ast.parse((ROOT / "scripts/build_prompt_packages.py").read_text(encoding="utf-8"))
    result = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"BROKER", "CLIENT"}:
                    result[target.id] = ast.literal_eval(node.value)
    result["BROKER"].update({70: "b47e063", 72: "cf0c99c", 73: "2dbeb84"})
    result["CLIENT"].update({41: "8cd0e1c"})
    return result


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def raw_blobs(repo, names):
    """cat-file ignora conversões CRLF/export-subst e preserva bytes do Git."""
    query = "".join(oid + "\n" for oid in names.values()).encode()
    raw = subprocess.check_output(["git", "cat-file", "--batch"], cwd=repo, input=query)
    stream, result = io.BytesIO(raw), {}
    for name, oid in names.items():
        actual, kind, size = stream.readline().decode().strip().split()
        if actual != oid or kind != "blob":
            raise ValueError(f"Objeto Git inesperado: {name}")
        result[name] = stream.read(int(size))
        if stream.read(1) != b"\n":
            raise ValueError("Resposta cat-file truncada")
    return result


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    catalogue, checksums, pending = [], {}, []
    maps = mapped_prompts()
    totals = {repo.name: int(git(repo, "rev-list", "--all", "--count")) for repo, _, _ in REPOS}
    temporary = OUTPUT / (ARCHIVE + ".tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as output:
        def put(name, data):
            safe(name)
            if name in checksums:
                raise ValueError(f"Arquivo duplicado: {name}")
            output.writestr(name, data)
            checksums[name] = hashlib.sha256(data).hexdigest()

        for repo, prefix, prompt_folder in REPOS:
            commits = git(repo, "rev-list", "--all", "--reverse", "--topo-order").decode().splitlines()
            head = git(repo, "rev-parse", "HEAD").decode().strip()
            tags = {}
            for tag in git(repo, "tag", "--list").decode().splitlines():
                tags.setdefault(git(repo, "rev-parse", tag + "^{commit}").decode().strip(), []).append(tag)
            mapping = {}
            for number, short in maps["BROKER" if prefix == "P" else "CLIENT"].items():
                mapping.setdefault(git(repo, "rev-parse", short).decode().strip(), []).append(f"{prefix}{number:02d}")
            if prefix == "P":
                for short in ("af64337", "e3e4a23"):
                    mapping.setdefault(git(repo, "rev-parse", short).decode().strip(), []).append("P74")
            doc_names = git(repo, "ls-tree", "-r", "--name-only", head, "prompts").decode().splitlines()
            documents = {name: git(repo, "show", f"{head}:{name}") for name in doc_names if name.endswith((".md", ".json"))}
            for name, data in documents.items():
                put(f"{repo.name}/documentos/{name}", data)

            for number, commit in enumerate(commits, 1):
                base = f"{repo.name}/{number:03d}-{commit[:7]}"
                subject, date, parents = git(repo, "show", "-s", "--format=%s%x00%cI%x00%P", commit).decode().strip().split("\0")
                changed = sorted(set(git(repo, "diff-tree", "--root", "-m", "--no-commit-id", "--name-only", "-r", commit).decode().splitlines()))
                related = set(mapping.get(commit, []))
                evidence = [{"id": identifier, "tipo": "Marco relacionado no índice do curso; não prova autoria exclusiva"} for identifier in sorted(related)]
                for name in changed:
                    match = re.search(r"^prompts/(?:broker|clients)/(\d+)-", name)
                    record = re.search(r"^prompts/registros/([PC]\d+)[-_.]", name)
                    identifier = f"{prefix}{int(match[1]):02d}" if match else record[1] if record else None
                    if identifier:
                        related.add(identifier)
                        evidence.append({"id": identifier, "tipo": "Documento alterado neste commit", "arquivo": name})
                for identifier in re.findall(r"\b[PC]\d{2,}\b", subject):
                    related.add(identifier)
                    evidence.append({"id": identifier, "tipo": "ID citado na mensagem do commit"})

                modes, hashes, names = {}, {}, {}
                tree = git(repo, "ls-tree", "-r", "-z", commit)
                for entry in tree.split(b"\0"):
                    if not entry:
                        continue
                    attributes, raw_name = entry.split(b"\t", 1)
                    mode, kind, oid = attributes.decode().split()
                    name = raw_name.decode("utf-8")
                    safe(name)
                    if kind != "blob" or mode not in {"100644", "100755"}:
                        raise ValueError(f"Link/submódulo inesperado: {name}")
                    names[name], modes[name] = oid, mode
                with nullcontext(raw_blobs(repo, names)) as snapshot:
                    exported = set(snapshot)
                    if exported != set(names):
                        raise ValueError(f"git archive excluiu arquivos em {commit}")
                    for name in sorted(exported):
                        data = snapshot[name]
                        oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                        if oid != names[name]:
                            raise ValueError(f"Conteúdo divergente do Git: {commit}:{name}")
                        if re.search(rb"^-----BEGIN [A-Z ]*PRIVATE KEY-----", data, re.M):
                            raise ValueError(f"Chave privada inesperada: {name}")
                        put(f"{base}/codigo/{name}", data)
                        hashes[name] = checksums[f"{base}/codigo/{name}"]
                    package = tomllib.loads(snapshot["Cargo.toml"].decode("utf-8"))["package"]
                    audit = AUDIT.get(commit[:7])
                    if audit:
                        status, record, quote, closing, closing_note = audit
                        record_name = f"prompts/registros/{record}"
                        raw = snapshot[record_name].decode("utf-8")
                        if quote not in raw:
                            raise ValueError(f"Evidência de pendência ausente: {commit}")
                        acceptance = {"estado": status, "registro": record_name, "trecho": quote, "marco_posterior": git(repo, "rev-parse", closing).decode().strip(), "nota_posterior": closing_note}
                        pending.append({"repositorio": repo.name, "commit": commit, "pasta": base, **acceptance})
                    elif commit[:7] in ACCEPTED:
                        status, record, quote = ACCEPTED[commit[:7]]
                        record_name = f"prompts/registros/{record}"
                        if quote not in snapshot[record_name].decode("utf-8"):
                            raise ValueError(f"Evidência de aceite ausente: {commit}")
                        acceptance = {"estado": status, "registro": record_name, "trecho": quote, "nota": "Aceite declarado pelo registro histórico, no escopo indicado; não reexecutado nesta embalagem."}
                    else:
                        acceptance = {"estado": "Conclusão integral não determinada por esta embalagem", "nota": "Consultar registros; não houve nova execução de testes nem auditoria funcional desta versão."}

                links = []
                for identifier in sorted(related):
                    value = int(identifier[1:])
                    candidates = [name for name in documents if name.startswith(f"prompts/{prompt_folder}/{value:02d}-") or re.match(rf"^prompts/registros/{identifier}[-_.]", name)]
                    for name in candidates:
                        target = f"codigo/{name}" if name in names else f"../documentos/{name}"
                        links.append(f"- [{identifier}: {name}]({target})")
                meta = {"repositorio": repo.name, "commit": commit, "ordem_topologica": number, "data_commit": date, "pais": parents.split(), "assunto": subject, "pacote": package["name"], "versao": package["version"], "tags_exatas": tags.get(commit, []), "prompts_relacionados": sorted(related), "evidencias_associacao": evidence, "aceite_documental": acceptance, "arquivos_alterados": changed, "modos_git": modes, "sha256_fontes": hashes, "referencia_de_corte": head, "pasta": base}
                catalogue.append(meta)
                lines = [f"# {repo.name} — versão {package['version']} — commit {commit[:7]}", "", f"- Commit completo: `{commit}`", f"- Data do commit: {date}", f"- Assunto: {subject}", f"- Tags neste commit: {', '.join(tags.get(commit, [])) or 'Nenhuma'}", f"- Pais: {parents or 'Primeiro commit deste histórico'}", f"- Prompts relacionados: {', '.join(sorted(related)) or 'Sem associação comprovada neste commit'}", "", "## O que esta versão representa", "", "Esta pasta é o projeto completo no instante desse commit. Commits diferentes podem manter a mesma versão em Cargo.toml: commit identifica uma gravação do histórico; a versão do pacote identifica um marco escolhido pelo projeto.", "", "O README original permanece em [codigo/README.md](codigo/README.md). Este README adicional explica a procedência do snapshot sem alterar suas fontes.", "", "## Prompt e evidência de origem", ""]
                if evidence:
                    lines += [f"- {item['id']}: {item['tipo']}" + (f" (`{item['arquivo']}`)" if "arquivo" in item else "") for item in evidence]
                else:
                    lines += ["Não há evidência suficiente para atribuir a criação deste commit a um prompt específico. O primeiro commit pode importar trabalho já desenvolvido; isso não registra sua criação desde uma pasta vazia."]
                lines += ["", "Um registro ou prompt alterado indica relação com o trabalho. Não demonstra que todo o código foi produzido por esse ID. Um commit pode reunir implementação, documentação e vários prompts.", ""] + links
                if commit[:7] in {"2dbeb84", "af64337", "e3e4a23"}:
                    lines += ["", "P73/P74 criaram a nova série didática P03/P04/P05. Esses IDs de aula não reconstituem a saída dos prompts históricos originais. Consulte curso/projeto-inicial ou curso/etapas no código. Essas primeiras etapas ensinam base Rust/TCP; não implementam MQTT."]
                lines += ["", "## A funcionalidade estava terminada?", "", acceptance["estado"], ""]
                if audit:
                    lines += [f"Evidência: [{acceptance['registro']}](codigo/{acceptance['registro']}).", "", f"> {acceptance['trecho'].replace(chr(10), ' ')}", "", f"Marco posterior: `{acceptance['marco_posterior'][:7]}`. {acceptance['nota_posterior']}. A pendência descreve este snapshot, não necessariamente o estado mais recente."]
                else:
                    lines += [acceptance["nota"]]
                    if "registro" in acceptance:
                        lines += ["", f"Evidência: [{acceptance['registro']}](codigo/{acceptance['registro']}).", "", f"> {acceptance['trecho']}"]
                lines += ["", "O relatório é documental: não confirma compatibilidade de todas as versões, produção ou todas as funcionalidades do Mosquitto. MQTT 5 e WebSockets não se tornam disponíveis por existir um prompt de planejamento.", "", "## Como consultar e executar", "", "1. Extraia o ZIP inteiro em uma pasta separada.", "2. Abra codigo/ no editor e leia seu README, Cargo.toml e documentos.", "3. Confira a versão mínima de Rust e o ambiente requerido naquela versão. O broker real possui administração/persistência com requisitos Unix: utilize Ubuntu/WSL conforme seu README. Os exemplos didáticos P03/P04/P05 têm validação histórica no Windows.", "4. Para compilar no ambiente compatível, dentro de codigo/, use `cargo build --locked`. Não execute serviços ou configurações antigas sobre estado/credenciais atuais; use ambiente de estudo isolado.", "5. Prompts e registros sem código por si só são preparação. Resultados históricos não foram reexecutados durante esta exportação.", "", "## Arquivos alterados nesse commit", ""]
                lines += [f"- `{name}`" for name in changed]
                lines += ["", "ALTERACOES.txt contém resumo do Git; COMMIT.json contém hashes e modos de cada fonte. O índice na raiz permite percorrer todos os commits em ordem topológica, dos ancestrais para os descendentes.", ""]
                put(f"{base}/README.md", "\n".join(lines).encode())
                put(f"{base}/COMMIT.json", json_bytes(meta))
                put(f"{base}/ALTERACOES.txt", git(repo, "show", "--format=fuller", "--stat", "--no-renames", commit))
                print(f"{repo.name}: {number}/{len(commits)} {commit[:7]}", flush=True)

        csv_file = io.StringIO(newline="")
        writer = csv.writer(csv_file, delimiter=";")
        writer.writerow(["repositorio", "commit", "data", "versao", "tags", "prompts", "assunto", "aceite", "pasta"])
        for row in catalogue:
            writer.writerow([row["repositorio"], row["commit"], row["data_commit"], row["versao"], ", ".join(row["tags_exatas"]), ", ".join(row["prompts_relacionados"]), row["assunto"], row["aceite_documental"]["estado"], row["pasta"]])
        put("versoes.csv", csv_file.getvalue().encode("utf-8-sig"))
        put("indice.json", json_bytes(catalogue))
        report = ["# Commits intermediários identificados", "", "Verificação documental dos registros no próprio commit. Um commit intermediário pode estar correto e ainda depender de implementação ou aceite posterior. Não é uma nova auditoria de código nem reexecução dos testes.", ""]
        for item in pending:
            report += [f"## {item['repositorio']} {item['commit'][:7]}", "", item["estado"], "", f"Evidência: [{item['registro']}]({item['pasta']}/codigo/{item['registro']}).", "", "> " + item["trecho"].replace("\n", " "), "", f"Marco posterior: {item['marco_posterior'][:7]} — {item['nota_posterior']}.", ""]
        report += ["## Plano P68", "", "O prompt P68 do capítulo IA/agentes/skills/MCP aparece no histórico como planejamento importado. Não há registro próprio comprovando a implementação integral. Não atribuir a ele uma entrega só pela presença do arquivo. Veja os documentos do broker e docs/course-handoff.txt no snapshot final.", "", "Nos casos sem classificação explícita de aceite, o estado é 'Conclusão integral não determinada por esta embalagem': ausência de uma pendência aqui não equivale a concluir a funcionalidade. P61 e C37 têm aceite histórico indicado nos READMEs, com seus limites. Consulte o README e os registros daquela versão."]
        put("PENDENCIAS.md", "\n".join(report).encode())
        readme = f"""# Todas as versões por commit — broker e client

Abra index.html após extrair o ZIP inteiro. São {totals['xmqr']} snapshots do broker e {totals['xmqr-client']} do
client no corte desta exportação; cada pasta tem README adicional, codigo/
original completo, COMMIT.json e ALTERACOES.txt. O índice mostra versão, tags,
prompts relacionados e situação documental. PENDENCIAS.md apresenta exemplos
conferidos de commits anteriores ao término de uma funcionalidade.

Histórico: todos os commits alcançáveis por referências locais/remotas e tags
disponíveis, após fetch --all --tags. Não inclui commits apagados/inacessíveis,
arquivos não commitados ou trabalho anterior à criação desses repositórios.
O commit do próprio exportador é posterior ao corte informado em indice.json.

Commit não é versão de pacote: vários commits podem declarar a mesma versão.
Tag marca um commit; release é a publicação de notas/anexos associada a um marco.
Prompts relacionados não significam autoria exclusiva de todas as linhas.
Documentos de consulta do corte estão em xmqr/documentos e xmqr-client/documentos.

Preservamos bytes de todos os arquivos Git, inclusive artefatos distribuídos
já commitados. Não incluímos diretórios de estado, segredos locais, target ou
credenciais não versionadas. Modos Git estão no JSON; extração Windows não
preserva automaticamente o bit executável Unix.

Esta exportação verifica fontes, hashes e integridade ZIP. Não compila nem
homologa novamente 78 versões. Leia o README original da versão antes de usar
Ubuntu/WSL ou Windows; não reutilize credenciais/estado de serviços reais.
"""
        put("README.md", readme.encode())
        escape = html.escape
        rows = []
        for row in catalogue:
            rows.append(f"<tr><td>{escape(row['repositorio'])}</td><td><a href='{row['pasta']}/README.md'>{row['ordem_topologica']:03d} · {row['commit'][:7]}</a></td><td>{escape(row['data_commit'])}</td><td>{escape(row['versao'])}<br>{escape(', '.join(row['tags_exatas']))}</td><td>{escape(', '.join(row['prompts_relacionados']) or 'Não comprovado')}</td><td>{escape(row['assunto'])}</td><td>{escape(row['aceite_documental']['estado'])}</td></tr>")
        page = "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Versões por commit</title><style>body{font:16px/1.6 system-ui;margin:24px;color:#14253b;background:#f4f7fb}a{color:#174c97}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #c9d4e0;padding:10px;text-align:left;vertical-align:top}.scroll{overflow:auto}</style><h1>Versões do broker e do client</h1>" + f"<p>{totals['xmqr']} commits do broker e {totals['xmqr-client']} do client. Abra o README de cada versão pelo link do commit. O código original está dentro de codigo/.</p>" + "<p><a href='README.md'>Como usar</a> · <a href='PENDENCIAS.md'>Commits com pendências identificadas</a> · <a href='versoes.csv'>Tabela CSV</a></p><p>Prompts indicam relações documentadas; não atribuem todo o programa a um único ID. A exportação não reexecutou testes de cada versão.</p><div class='scroll'><table><thead><tr><th>Projeto</th><th>Commit / README</th><th>Data</th><th>Versão / tags</th><th>Prompts relacionados</th><th>Alteração</th><th>Aceite documental</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div></html>"
        put("index.html", page.encode())
        put("SHA256SUMS.txt", "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())).encode())

    with zipfile.ZipFile(temporary) as verified:
        if verified.testzip() is not None:
            raise ValueError("CRC ZIP inválido")
        for name, digest in checksums.items():
            if hashlib.sha256(verified.read(name)).hexdigest() != digest:
                raise ValueError(f"Hash ZIP divergente: {name}")
        # Todos os links locais do índice e dos READMEs adicionais devem resolver.
        all_names = set(verified.namelist())
        for row in catalogue:
            if f"{row['pasta']}/README.md" not in all_names:
                raise ValueError("README de versão ausente")
            name = f"{row['pasta']}/README.md"
            for link in re.findall(r"\]\(([^)]+)\)", verified.read(name).decode("utf-8")):
                if "://" not in link and posixpath.normpath(posixpath.join(posixpath.dirname(name), link)) not in all_names:
                    raise ValueError(f"Link README ausente: {name}: {link}")
        for link in re.findall(r"href='([^']+)'", verified.read("index.html").decode("utf-8")):
            if link not in all_names:
                raise ValueError(f"Link índice ausente: {link}")
        print(f"PASS: {len(catalogue)} commits; {len(checksums)} arquivos; CRC/SHA-256/blobs Git", flush=True)
    temporary.replace(OUTPUT / ARCHIVE)
    target = OUTPUT / ARCHIVE
    (OUTPUT / (ARCHIVE + ".sha256")).write_text(f"{hashlib.sha256(target.read_bytes()).hexdigest()}  {ARCHIVE}\n", encoding="utf-8")
    (OUTPUT / "indice.json").write_bytes(json_bytes(catalogue))
    external_report = "\n".join(report)
    for item in pending:
        external_report = external_report.replace(f"{item['pasta']}/codigo/{item['registro']}", f"https://github.com/licodevone/{item['repositorio']}/blob/{item['commit']}/{item['registro']}")
    (OUTPUT / "PENDENCIAS.md").write_text(external_report, encoding="utf-8")
    (OUTPUT / "index.html").write_text("<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Download de todas as versões</title><h1>Todos os commits do broker e do client</h1>" + f"<p>{totals['xmqr']} versões do broker e {totals['xmqr-client']} do client, com README e prompts relacionados por versão.</p>" + "<p><a href='" + ARCHIVE + "'>Baixar ZIP completo</a></p><p>Extraia o ZIP e abra index.html dentro da pasta extraída. Consulte PENDENCIAS.md para commits intermediários identificados.</p></html>", encoding="utf-8")
    print(f"ZIP: {target} ({target.stat().st_size / 1024**2:.1f} MiB)", flush=True)


if __name__ == "__main__":
    build()
