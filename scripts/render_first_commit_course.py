"""P77: guia de digitação com sidebar sincronizada e todas as fontes por etapa."""

import hashlib
import html
import json
from pathlib import Path
import re
import zipfile

from build_first_commit_course import COURSE, OUTPUT, COMMIT, snapshots, original_files
from build_prompt_packages import note_reader


def inline(text):
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"\[([^]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)


def markdown(text):
    output, paragraph, code, listing, table = [], [], None, False, False
    def flush():
        if paragraph:
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()
    for line in text.splitlines():
        if line.startswith("```"):
            flush()
            if code is None:
                code = []
            else:
                output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        is_list = bool(re.match(r"^(?:\d+\.|-) ", line))
        is_table = line.startswith("|")
        if listing and not is_list:
            output.append("</ul>")
            listing = False
        if table and not is_table:
            output.append("</tbody></table></div>")
            table = False
        if not line.strip():
            flush()
        elif re.match(r"^#{1,3} ", line):
            flush()
            level, title = line.split(" ", 1)
            output.append(f"<h{len(level)}>{inline(title)}</h{len(level)}>")
        elif is_list:
            flush()
            if not listing:
                output.append("<ul>")
                listing = True
            output.append("<li>" + inline(re.sub(r"^(?:\d+\.|-) ", "", line)) + "</li>")
        elif is_table:
            flush()
            if re.match(r"^\|[\s:|\-]+\|$", line):
                continue
            cells = line.strip("|").split("|")
            if not table:
                output.append('<div class="scroll"><table><tbody>')
                table = True
            output.append("<tr>" + "".join("<td>" + inline(cell.strip()) + "</td>" for cell in cells) + "</tr>")
        else:
            paragraph.append(line.strip())
    flush()
    if listing:
        output.append("</ul>")
    if table:
        output.append("</tbody></table></div>")
    return "".join(output)


def human_toml(line):
    value = line.strip()
    if not value:
        return "Separa visualmente partes do manifesto."
    if value.startswith("#"):
        return "Comentário TOML: explica a opção sem executar código."
    if value.startswith("["):
        return "Abre a seção indicada do manifesto."
    if "=" in value:
        return "Define " + value.split("=", 1)[0].strip() + ": leia a explicação de manifesto/bibliotecas antes de escolher este valor."
    return "Continua a declaração TOML iniciada nas linhas anteriores."


def render():
    original = original_files()
    catalogue = json.loads((OUTPUT / "indice.json").read_text(encoding="utf-8"))
    note = note_reader()
    navigation, body, rust_count = [], [], 0

    def topic(identifier, title, content, children=""):
        navigation.append(f'<details class="nav-node" data-target="{identifier}"><summary>{html.escape(title)}</summary><a href="#{identifier}">Ir ao tópico</a>{children}</details>')
        body.append(f'<details class="main-node" id="{identifier}"><summary>{html.escape(title)}</summary><div class="content">{content}</div></details>')

    topic("inicio", "Como usar este material", '<h1>Do zero ao primeiro commit XMQR</h1><p>Da lógica ao Broker e Clientes MQTT utilizando Rust</p><p>Reconstrução didática nova, preparada por P77. Destino: <code>' + COMMIT + '</code>, XMQR 0.3.0, 35 arquivos e três executáveis. O histórico original não registra sua criação desde uma pasta vazia.</p><p>Os dez ZIPs são cumulativos. Digite os arquivos da etapa, confira os conceitos e só então compile o checkpoint completo. No R10, o conteúdo de codigo/ é idêntico ao primeiro commit. Guias e prompts ficam fora dessa pasta.</p><p><a href="ROTEIRO.md">Roteiro escrito completo</a> · <a href="primeiro-commit-curso-completo.zip" download>Baixar todos os checkpoints e guia</a> · <a href="VALIDACAO.json">Resultados da validação</a></p>')
    roteiro = (COURSE / "ROTEIRO.md").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## ", roteiro)
    for index, section in enumerate(sections[1:], 1):
        title, content = section.split("\n", 1)
        lessons = re.split(r"(?m)^### ", content)
        rendered = markdown(lessons[0])
        child_nav = ""
        for number, lesson in enumerate(lessons[1:], 1):
            lesson_title, lesson_body = lesson.split("\n", 1)
            identifier = f"texto-{index}-aula-{number}"
            rendered += f'<details class="main-node lesson" id="{identifier}"><summary>{html.escape(lesson_title)}</summary><div class="content">{markdown(lesson_body)}</div></details>'
            child_nav += f'<details class="nav-node" data-target="{identifier}"><summary>{html.escape(lesson_title)}</summary><a href="#{identifier}">Ir à aula</a></details>'
        topic("texto-" + str(index), title, rendered, child_nav)
    topic("bibliotecas", "Bibliotecas explicadas antes do uso", markdown((COURSE / "BIBLIOTECAS.md").read_text(encoding="utf-8")))
    previous = {}
    for identifier, title, files, order, concepts in snapshots(original):
        info = next(entry for entry in catalogue if entry["etapa"] == identifier)
        rendered = f'<p><strong>Checkpoint {identifier}:</strong> {html.escape(title)}.</p><p>Conceitos novos: {html.escape(concepts)}.</p><p><a href="{info["zip"]}" download>Baixar {identifier}: projeto acumulado</a> · <a href="prompts/{identifier}.md">Ler prompt da etapa</a></p><p>Digite os arquivos novos/alterados abaixo, na ordem apresentada. Arquivos mantidos permanecem no ZIP. Compilar somente depois de concluir o conjunto da etapa.</p><pre>cargo build --locked --bins\ncargo check --locked --all-targets</pre>'
        selected = [name for name in (order or sorted(files)) if files[name] != previous.get(name)]
        children = ""
        for number, name in enumerate(selected, 1):
            file_id = f"fonte-{identifier}-{number}"
            changes = "ALTERADO" if name in previous else "NOVO"
            raw = files[name].decode("utf-8")
            rows = []
            note.__globals__["pending"].clear()
            if name.endswith(".rs") or name == "Cargo.toml":
                for line_number, line in enumerate(raw.splitlines(), 1):
                    meaning = note(line) if name.endswith(".rs") else human_toml(line)
                    rows.append(f'<tr data-line="{line_number}"><td class="number">{line_number}</td><td><code>{html.escape(line)}</code></td><td>{html.escape(meaning)}</td></tr>')
                if name.endswith(".rs"):
                    rust_count += len(rows)
                code = '<p>A coluna de explicação trata da instrução/sintaxe. Leia a aula do módulo para entender suas decisões e o fluxo completo. Não digite os números nem esta coluna.</p><div class="scroll"><table class="code-table"><thead><tr><th>Linha</th><th>Código a digitar</th><th>Leitura da instrução</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
            else:
                code = ('<p>Arquivo gerado pelo Cargo: preserve o lock fornecido para reproduzir as versões. Não precisa digitar seus hashes.</p>' if name == "Cargo.lock" else '<p>Arquivo original de configuração/documentação. Leia a aula R10 para distinguir arquivos consumidos pelo XMQR de referências ao Mosquitto.</p>') + '<pre><code>' + html.escape(raw) + '</code></pre>'
            rendered += f'<details class="main-node code-file" id="{file_id}" data-path="{html.escape(name)}"><summary>[{identifier} — {changes}] {html.escape(name)} · {len(raw.splitlines())} linhas</summary><div class="content">{code}</div></details>'
            children += f'<details class="nav-node" data-target="{file_id}"><summary>{html.escape(name)}</summary><a href="#{file_id}">Ir ao arquivo</a></details>'
        topic("codigo-" + identifier, identifier + " — " + title, rendered, children)
        previous = files
    validation = []
    for platform in ("windows", "ubuntu26"):
        data = json.loads((OUTPUT / ("VALIDACAO-" + platform + ".json")).read_text(encoding="utf-8"))
        if not data.get("finalizado"):
            raise ValueError("Validação não concluída")
        validation.append(data)
    results = {"primeiro_commit": COMMIT, "arquivos_historicos": 35, "linhas_rust_historicas": 6083, "linhas_rust_exibidas_com_estagios_iniciais": rust_count, "validacoes": validation, "nota": "Clippy histórico falhou por assert_is_empty; ajuste validado em cópia separada sem alterar R10."}
    adjustment = json.loads((OUTPUT / "VALIDACAO-ajuste-clippy.json").read_text(encoding="utf-8"))
    results["ajuste_separado"] = adjustment
    (OUTPUT / "VALIDACAO.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    topic("validacao", "Validação e ajuste posterior de Clippy", '<p>As dez etapas passaram em build/check no Windows Rust 1.98.1/MSVC e Ubuntu 26/WSL Rust 1.99.0. R10: fmt e 52 testes Linux passaram; pub/sub QoS0 recebeu o payload fictício em loopback com estado isolado.</p><p>Clippy 1.99 com warnings como erro apontou <code>assert_is_empty</code> em <code>src/mqtt/store.rs:305</code>. Código original preservado. Em uma cópia separada, o ajuste abaixo passou fmt, 52 testes e Clippy:</p><pre>// Histórico R10\ndebug_assert!(remainder.is_empty());\n\n// Ajuste para um commit posterior\ndebug_assert_eq!(remainder, []);</pre><p>Não aplique a alteração se seu objetivo nesta aula é comparar exatamente R10 ao primeiro commit. O ajuste é uma evolução separada. <a href="VALIDACAO.json">Veja os comandos e resultados</a>.</p><p>O commit criado no ensaio tem a mesma árvore de arquivos do primeiro commit: <code>03a0304b3d6e416139dadc96671433799eec588f</code>. Ele tem outro SHA por metadados diferentes. Sem homologação TLS/Mosquitto/MQTT5 ou execução completa no Windows.</p>')
    styles = """*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font:16px/1.65 system-ui;background:#f4f7fb;color:#172b43}a{color:#175697}code{font-family:Consolas,monospace;font-size:.92em}header{background:#102b43;color:#eef6ff;padding:20px}header a{color:#b9e4ff}button,input{font:inherit;padding:9px 12px;border:1px solid #b4c5d8;border-radius:6px}button{cursor:pointer}nav{position:fixed;top:0;bottom:0;width:285px;overflow:auto;background:#102b43;color:#e9f1fc;padding:18px}nav a{color:#bde2ff}main{margin-left:285px;padding:28px;max-width:1600px}details{border:1px solid #b8c9dc;border-radius:8px;background:white;margin:12px 0}summary{padding:12px;cursor:pointer;font-weight:650}nav details{background:#173751;border-color:#42627a;font-size:14px}nav details details{margin:6px 8px}.content{padding:0 18px 18px}.lesson{background:#f7fafd}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf2f7;padding:16px;border-radius:5px}table{border-collapse:collapse;width:100%;font-size:15px}td,th{border:1px solid #c9d5e2;padding:8px;text-align:left;vertical-align:top}.scroll{overflow:auto}.code-table td:nth-child(2){min-width:360px;max-width:660px;white-space:pre-wrap;overflow-wrap:anywhere}.code-table td:nth-child(3){min-width:260px}.number{color:#64748b;width:55px}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}.code-file summary{overflow-wrap:anywhere}tr.highlight{background:#fff0b3}[hidden]{display:none!important}@media(max-width:900px){nav{position:relative;width:100%;max-height:45vh}main{margin:0;padding:16px}.code-table{font-size:13px}}@media print{nav,.toolbar,header{display:none}main{margin:0;padding:0}details{border:0}summary{font-size:18px}pre{background:white}}"""
    script = """const navs=[...document.querySelectorAll('nav details[data-target]')];const mainNodes=[...document.querySelectorAll('main details[id]')];
navs.forEach(n=>{const t=document.getElementById(n.dataset.target);n.addEventListener('toggle',()=>{if(t.open!==n.open)t.open=n.open;});t.addEventListener('toggle',()=>{if(n.open!==t.open)n.open=t.open;});});
function reveal(id){let target=document.getElementById(id);if(!target)return;for(let p=target;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;target.scrollIntoView({block:'start'});}
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>reveal(a.hash.slice(1))));
document.querySelectorAll('[data-open-all]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();mainNodes.forEach(n=>n.open=true);navs.forEach(n=>n.open=true);}));
document.querySelectorAll('[data-close-all]').forEach(a=>a.addEventListener('click',()=>{mainNodes.forEach(n=>n.open=false);navs.forEach(n=>n.open=false);}));
document.getElementById('search').addEventListener('input',function(){const q=this.value.toLowerCase().trim();const location=q.match(/^(.*):(\\d+)$/);let found=0;document.querySelectorAll('.code-file').forEach(f=>{const path=f.dataset.path.toLowerCase();const rows=[...f.querySelectorAll('tr[data-line]')];rows.forEach(r=>r.classList.remove('highlight'));let match=!q||path.includes(q)||f.querySelector('.content').textContent.toLowerCase().includes(q);if(location){match=path.includes(location[1])&&rows.some(r=>r.dataset.line===location[2]);if(match)rows.filter(r=>r.dataset.line===location[2]).forEach(r=>r.classList.add('highlight'));}f.hidden=!match;if(match&&q){found++;for(let p=f;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;}});document.getElementById('search-status').textContent=q?found+' arquivos encontrados':'';});
if(location.hash)reveal(location.hash.slice(1));else{document.getElementById('inicio').open=true;navs.find(n=>n.dataset.target==='inicio').open=true;}"""
    page = '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Do zero ao primeiro commit XMQR</title><style>' + styles + '</style></head><body><nav aria-label="Seções e aulas"><h2>XMQR · primeiro commit</h2><p><a href="#" data-open-all>Abrir todos os tópicos</a></p><button data-close-all>Recolher todos</button>' + "".join(navigation) + '</nav><main><header><h1>Do zero ao XMQR 0.3.0</h1><p>Passo a passo até o primeiro commit</p><a href="primeiro-commit-curso-completo.zip" download>Baixar curso e projetos cumulativos</a></header><div class="toolbar"><a href="#" data-open-all>Abrir todos os tópicos</a><button data-close-all>Recolher todos</button></div><label>Buscar arquivo, trecho ou arquivo:linha<br><input id="search" placeholder="Ex.: src/main.rs:52 ou debug_assert"></label><p id="search-status" aria-live="polite"></p>' + "".join(body) + '<footer><p>Código histórico preservado; materiais de reconstrução P77. ' + str(rust_count) + ' linhas Rust exibidas, incluindo scaffolds iniciais e substituições.</p></footer></main><script>' + script + '</script></body></html>'
    (OUTPUT / "index.html").write_text(page, encoding="utf-8")
    (OUTPUT / "prompts").mkdir(exist_ok=True)
    for prompt in (COURSE / "prompts").glob("*.md"):
        (OUTPUT / "prompts" / prompt.name).write_bytes(prompt.read_bytes())
    (OUTPUT / "BIBLIOTECAS.md").write_bytes((COURSE / "BIBLIOTECAS.md").read_bytes())
    (OUTPUT / "AJUSTE-CLIPPY.diff").write_text("--- a/src/mqtt/store.rs\n+++ b/src/mqtt/store.rs\n@@ -305 +305 @@\n-        debug_assert!(remainder.is_empty());\n+        debug_assert_eq!(remainder, []);\n", encoding="utf-8")
    complete = OUTPUT / "primeiro-commit-curso-completo.zip"
    files = {file.relative_to(OUTPUT).as_posix(): file.read_bytes() for file in OUTPUT.rglob("*") if file.is_file() and file.name not in {complete.name, complete.name + ".sha256"}}
    with zipfile.ZipFile(complete, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with zipfile.ZipFile(complete) as archive:
        if archive.testzip():
            raise ValueError("Pacote completo inválido")
    complete.with_suffix(".zip.sha256").write_text(hashlib.sha256(complete.read_bytes()).hexdigest() + "  " + complete.name + "\n", encoding="utf-8")
    print(f"Guia HTML completo: {rust_count} linhas Rust, dez etapas e ZIPs; {complete.stat().st_size} bytes no pacote completo")


if __name__ == "__main__":
    render()
