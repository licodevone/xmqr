"""Empacota a base didática nova P00/P03 e gera guia HTML de digitação."""
from pathlib import Path
import hashlib
import html
import json
import zipfile


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'curso/projeto-inicial'
DESTINATION=ROOT.parent/'docs/curso-udemy/projeto-inicial'


def build():
    DESTINATION.mkdir(parents=True,exist_ok=True)
    files={}
    for path in sorted(SOURCE.rglob('*')):
        if path.is_file() and 'target' not in path.relative_to(SOURCE).parts:
            name=path.relative_to(SOURCE).as_posix()
            if '..' in Path(name).parts or path.suffix in {'.key','.pem','.pfx','.p12'}:
                raise ValueError('Arquivo fora do escopo do pacote inicial')
            files[name]=path.read_bytes()
    required={'broker/Cargo.toml','broker/Cargo.lock','broker/src/main.rs','client/Cargo.toml','client/Cargo.lock','client/src/main.rs','README.md','LICENSE','prompts/00-contexto.md','prompts/03-criar-base.md'}
    if not required.issubset(files):
        raise ValueError('Base inicial incompleta')
    explanation='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>P00/P03 — projeto inicial Windows</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:25px;background:#101c2c;color:#e7edf6;overflow-wrap:anywhere}a{color:#99ddf3}nav{padding:20px;background:#192b41;border-radius:8px}nav a{display:inline-block;margin:8px}h1{line-height:1.2;color:#a3e4cc}h2{color:#99ddf3}details{border:1px solid #46607a;border-radius:8px;margin:20px 0;padding:18px}summary{cursor:pointer;font-weight:bold}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#091321;padding:18px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #456077;text-align:left;padding:12px;vertical-align:top}.scroll{overflow:auto}@media print{body{background:white;color:black}pre{background:#eee}h1,h2{color:black}}</style></head><body><h1>Projeto inicial — Rust no Windows</h1><p>Da lógica ao Broker e Clientes MQTT utilizando Rust</p><nav><a href="#inicio">O que foi criado</a><a href="#rodar">Executar no Windows</a><a href="#codigo">Digitar e entender</a><a href="#arquivos">Arquivos completos</a><a href="P03-projeto-inicial-windows.zip" download>Baixar código (ZIP)</a></nav><section id="inicio"><h2>P00 prepara; P03 cria a base</h2><p>P03 é o prompt histórico que descreve bootstrap: criação da estrutura inicial que compila. O primeiro recorte foi implementado agora para este curso. Não é uma recuperação comprovada da execução antiga. P00 define contexto antes do código; ele está incluído no pacote.</p><p>São dois projetos independentes: broker-inicial e client-inicial. Cada programa imprime identificação e termina com sucesso. Ainda não abre porta nem interpreta MQTT. Nenhuma biblioteca externa é necessária.</p></section><section id="rodar"><h2>Executar com sua instalação Rust</h2><p>Extraia o ZIP. Abra PowerShell na pasta que contém broker, client e README.md. Digite:</p><pre>cargo --version
rustc --version
cargo run --locked --offline --manifest-path .\\broker\\Cargo.toml
cargo run --locked --offline --manifest-path .\\client\\Cargo.toml</pre><p>Saídas dos programas:</p><pre>Broker MQTT: projeto inicial em Rust.
Client MQTT: projeto inicial em Rust.</pre><p>O encerramento imediato é esperado: a função termina depois de imprimir. Nesta entrega, a compilação e execução foram verificadas no Windows com Rust1.98.1/MSVC. Leia README.md para criar sua própria cópia digitada.</p></section><section id="codigo"><h2>Código completo: digite e entenda os comentários</h2>'''
    explanation+='<pre>'+html.escape(files['broker/src/main.rs'].decode())+'</pre>'
    tokens=[('// ...','Comentário que identifica a etapa P03; não executa uma ação.'),('fn','Declara uma função, um bloco de instruções que pode ser executado.'),('main','Nome da entrada desse executável: o programa começa aqui.'),('()','Lista vazia de parâmetros da função.'),('{','Abre o corpo da função.'),('quatro espaços','Indentação de leitura; não substitui as chaves.'),('println!','Macro da biblioteca padrão que imprime o texto e uma nova linha. ! identifica a chamada de macro.'),('("texto")','Parênteses delimitam argumentos; aspas delimitam o texto literal.'),(';','Encerra a instrução de impressão.'),('}','Fecha a função: quando ela termina, este programa encerra.')]
    explanation+='<div class="scroll"><table><tr><th>Parte digitada</th><th>Explicação</th></tr>'+''.join('<tr><td><code>'+html.escape(token)+'</code></td><td>'+html.escape(meaning)+'</td></tr>' for token,meaning in tokens)+'</table></div><p>No client, a estrutura é a mesma: o texto começa com Client MQTT. Digite a alteração, salve e execute novamente. Cargo.toml, Cargo.lock e todos os comandos são explicados no README completo abaixo.</p></section><section id="arquivos"><h2>Todos os arquivos do pacote</h2>'
    for name,data in files.items():
        explanation+='<details><summary>'+html.escape(name)+'</summary><pre>'+html.escape(data.decode('utf-8'))+'</pre></details>'
    explanation+='</section></body></html>'
    archive=DESTINATION/'P03-projeto-inicial-windows.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as package:
        for name,data in files.items():
            package.writestr(name,data)
        standalone=explanation.replace('<a href="P03-projeto-inicial-windows.zip" download>Baixar código (ZIP)</a>','')
        package.writestr('GUIA.html',standalone.encode('utf-8'))
    with zipfile.ZipFile(archive) as package:
        if package.testzip():
            raise ValueError('ZIP corrompido')
        if any(package.read(name)!=data for name,data in files.items()):
            raise ValueError('ZIP não corresponde às fontes')
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    (DESTINATION/'P03-projeto-inicial-windows.zip.sha256').write_text(checksum+'  '+archive.name+'\n',encoding='utf-8')
    (DESTINATION/'index.html').write_text(explanation,encoding='utf-8')
    (DESTINATION/'manifesto.json').write_text(json.dumps({'serie':'nova implementação didática','preparacao':'P00','codigo':'P03, recorte inicial','arquivo':archive.name,'sha256':checksum,'arquivos':list(files),'protocolo_mqtt_implementado':False},ensure_ascii=False,indent=2),encoding='utf-8')
    # Atualiza o índice já aberto pelo usuário sem reconstruir snapshots históricos.
    index=ROOT.parent/'docs/curso-udemy/pacotes/index.html'
    if index.exists():
        page=index.read_text(encoding='utf-8')
        link='<p><a href="../projeto-inicial/index.html">Nova base inicial P00/P03 — código para Rust nativo Windows</a></p>'
        if '../projeto-inicial/index.html' not in page:
            index.write_text(page.replace('<table>',link+'<table>',1),encoding='utf-8')
    print(f'ZIP íntegro: {archive} ({len(files)} arquivos-fonte); SHA-256 {checksum}')


if __name__=='__main__':
    build()
