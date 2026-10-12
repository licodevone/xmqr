"""Exporta snapshots novos P03/P04/P05, fontes acumuladas, comentários e diffs."""
from pathlib import Path  # Caminhos independentes do diretório atual do terminal.
import difflib  # Compara o texto da etapa anterior e da atual.
import hashlib  # Calcula SHA-256 dos arquivos para conferir conteúdo.
import html  # Escapa caracteres do código antes de mostrá-los no HTML.
import json  # Registra a origem e os hashes em um formato estruturado.
import subprocess  # Consulta o commit real dos arquivos, sem alterar o Git.
import zipfile  # Compacta, lê e confere os pacotes ZIP.

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT.parent/'docs/curso-udemy/serie-didatica'
STAGES=[('P03',ROOT/'curso/projeto-inicial','Base inicial, dois executáveis sem rede.'),('P04',ROOT/'curso/etapas/P04','Acrescenta broker de eco TCP; mantém client P03.'),('P05',ROOT/'curso/etapas/P05','Acrescenta client TCP; mantém broker P04.')]


def collect(folder):
    files={}
    for path in sorted(folder.rglob('*')):
        if path.is_file() and 'target' not in path.relative_to(folder).parts:
            name=path.relative_to(folder).as_posix()
            if '..' in Path(name).parts or path.suffix in {'.pem','.key','.p12','.pfx','.exe'}:
                raise ValueError('Arquivo fora do escopo')
            files[name]=path.read_bytes()
    return files


def build():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    previous={}
    rows=[]
    catalogue=[]
    for identifier,folder,description in STAGES:
        files=collect(folder)
        changes=[]
        for name in sorted(set(previous)|set(files)):
            before=previous.get(name,b'').decode('utf-8').splitlines(keepends=True)
            after=files.get(name,b'').decode('utf-8').splitlines(keepends=True)
            if before!=after:
                changes.extend(difflib.unified_diff(before,after,fromfile='anterior/'+name,tofile=identifier+'/'+name))
        difference=''.join(changes)
        guide='<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+identifier+' — série didática</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:24px;background:#101c2c;color:#e8eef5;overflow-wrap:anywhere}h1,h2,a{color:#99ddf3}details{border:1px solid #49627b;padding:16px;margin:15px 0;border-radius:8px}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#091321;padding:18px}</style></head><body><h1>'+identifier+' — projeto acumulado</h1><p>'+html.escape(description)+'</p><p>Série didática nova, executável no Windows. Comentários identificam as origens e explicam comandos/APIs; o README descreve cada conceito novo. Ainda não há protocolo MQTT nestas etapas.</p><h2>Como executar e entender esta etapa</h2><pre>'+html.escape(files['README.md'].decode())+'</pre><h2>Código comentado</h2>'
        for name in ('broker/src/main.rs','client/src/main.rs','broker/Cargo.toml','client/Cargo.toml'):
            guide+='<h3>'+name+'</h3><pre>'+html.escape(files[name].decode())+'</pre>'
        guide+='<details><summary>Diferença em relação à etapa anterior</summary><pre>'+html.escape(difference)+'</pre></details><h2>Arquivos e prompts acumulados</h2>'
        for name,data in files.items():
            if name not in {'README.md','broker/src/main.rs','client/src/main.rs','broker/Cargo.toml','client/Cargo.toml'}:
                guide+='<details><summary>'+html.escape(name)+'</summary><pre>'+html.escape(data.decode())+'</pre></details>'
        guide+='</body></html>'
        archive=OUTPUT/(identifier+'-projeto-acumulado-windows.zip')
        states={name:('MANTIDO da etapa anterior' if previous.get(name)==data else ('ALTERADO neste prompt' if name in previous else 'NOVO neste prompt')) for name,data in files.items()}
        commit=subprocess.check_output(['git','log','-1','--format=%H','--',folder.relative_to(ROOT).as_posix()],cwd=ROOT,text=True).strip()
        metadata={'serie':'nova série didática','etapa':identifier,'commit_etapa':commit or None,'descricao':description,'arquivos_fonte':list(files),'origem_por_arquivo':states,'sha256_fontes':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()},'bibliotecas_externas':[],'protocolo_mqtt':False}
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as package:
            for name,data in files.items():
                package.writestr(name,data)
            package.writestr('ALTERACOES.diff',difference.encode())
            package.writestr('GUIA.html',guide.encode())
            package.writestr('PROVENIENCIA.json',json.dumps(metadata,ensure_ascii=False,indent=2).encode())
        with zipfile.ZipFile(archive) as package:
            if package.testzip() is not None or any(package.read(name)!=data for name,data in files.items()):
                raise ValueError('Arquivo ZIP divergente')
        checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
        metadata.update({'zip':archive.name,'sha256_zip':checksum})
        catalogue.append(metadata)
        (OUTPUT/(identifier+'-codigo-comentado.html')).write_text(guide,encoding='utf-8')
        rows.append('<tr><td>'+identifier+'</td><td>'+html.escape(description)+'</td><td><a href="'+archive.name+'">Baixar código completo</a></td><td><a href="'+identifier+'-codigo-comentado.html">Código e explicação</a></td></tr>')
        previous=files
    page='<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Etapas cumulativas — Rust Windows</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:24px;background:#101c2c;color:#e8eef5;overflow-wrap:anywhere}h1,h2,a{color:#99ddf3}table{border-collapse:collapse;width:100%}th,td{border:1px solid #49627b;padding:14px;text-align:left}div{overflow:auto}pre{white-space:pre-wrap;background:#091321;padding:18px}</style></head><body><h1>Etapas cumulativas — Rust nativo Windows</h1><p>P00 prepara o contexto. P03, P04 e P05 abaixo são novas implementações didáticas. Cada ZIP mantém o código anterior e acrescenta a mudança do seu prompt, com fonte completa, comentários e diff.</p><div><table><tr><th>Prompt</th><th>Evolução</th><th>ZIP acumulado</th><th>Leitura</th></tr>'+''.join(rows)+'</table></div><h2>Identificação dos comentários</h2><p>[Pxx - NOVO]: trecho acrescentado. [Pxx - ALTERADO]: mudança em código existente. [Pxx - MANTIDO]: funcionalidade preservada da etapa anterior. A diferença completa está em ALTERACOES.diff.</p><h2>Próximas partes do curso</h2><pre>'+html.escape((ROOT/'curso/README.md').read_text(encoding='utf-8'))+'</pre></body></html>'
    (OUTPUT/'index.html').write_text(page,encoding='utf-8')
    (OUTPUT/'indice.json').write_text(json.dumps(catalogue,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUTPUT/'SHA256SUMS.txt').write_text(''.join(item['sha256_zip']+'  '+item['zip']+'\n' for item in catalogue),encoding='utf-8')
    index=ROOT.parent/'docs/curso-udemy/pacotes/index.html'
    if index.exists():
        old=index.read_text(encoding='utf-8')
        if '../serie-didatica/index.html' not in old:
            index.write_text(old.replace('<table>','<p><a href="../serie-didatica/index.html">Nova série: P03 + P04 + P05, códigos cumulativos comentados para Windows</a></p><table>',1),encoding='utf-8')
    print(f'{len(catalogue)} ZIPs cumulativos íntegros: {OUTPUT}')


if __name__=='__main__':
    build()
