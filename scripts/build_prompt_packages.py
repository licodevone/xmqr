"""P70: pacotes cumulativos de evidências e snapshots Git, sem inventar autoria."""
from pathlib import Path
import ast
import collections
import hashlib
import html
import json
import io
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / 'docs' / 'curso-udemy' / 'pacotes'
# Marcos relacionados por registros e mensagens Git. IDs não são ordem de commit.
BROKER = {41:'59c9e70',42:'bc4cc55',43:'3a3dde7',44:'b3f34b9',45:'a79eb4d',46:'f83ff77',47:'e6d2df8',48:'cb52a5b',49:'a2743bc',50:'d70e6f8',51:'8e55f80',52:'7da894a',53:'d95fcb7',54:'7d5f371',55:'d76c9e9',56:'627aab3',57:'4fe905a',58:'49edfc2',59:'49edfc2',60:'49edfc2',61:'d7b9d41',62:'aa5fda4',63:'121153e',64:'725251b',65:'c5edf38',66:'2648f32',67:'58b6cd6',69:'f231226'}
CLIENT = {25:'26c1019',26:'fe0e9e9',27:'6d25b33',28:'d26eb9c',29:'c0375a6',30:'3e7c16a',31:'24cf106',32:'87653d1',33:'ab012ad',34:'9619776',35:'98b72f0',36:'1f22a18',37:'6ee5aa8',38:'35580ba',39:'890829f',40:'8bb7aaf'}


def git(repo, *arguments):
    return subprocess.check_output(['git', *arguments], cwd=repo)


def note_reader():
    """Reutilizar só funções/dicionários; não executar escrita do anotador HTML."""
    tree = ast.parse((ROOT/'scripts/guide_line_notes.py').read_text(encoding='utf-8'))
    allowed = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            allowed.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('calls','variables','stats') for t in node.targets):
            allowed.append(node)
    namespace={'html':html,'re':re,'collections':collections,'pending':[]}
    exec(compile(ast.Module(body=allowed,type_ignores=[]),'<notas-de-leitura>','exec'),namespace)
    return namespace['note']


def valid_path(name):
    path=Path(name)
    return not path.is_absolute() and '..' not in path.parts and '\\' not in name


def snapshot(repo, commit):
    result={}
    excluded=[]
    archive=tarfile.open(fileobj=io.BytesIO(git(repo,'archive','--format=tar',commit)),mode='r:')
    for member in archive.getmembers():
        if not member.isfile():
            continue
        name=member.name
        if not valid_path(name):
            raise ValueError('Caminho Git inseguro')
        # Artefato HTML gerado é substituído pela leitura específica do pacote.
        if name.endswith('code-guide.html'):
            excluded.append(name)
            continue
        if Path(name).suffix.lower() in {'.key','.pem','.p12','.pfx','.crt','.der'} or Path(name).name.startswith('.env'):
            raise ValueError(f'Arquivo sensível inesperado: {name}')
        data=archive.extractfile(member).read()
        if re.search(rb'^-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----',data,re.M):
            raise ValueError(f'Chave privada inesperada: {name}')
        result[name]=data
    return result,excluded


def source_html(files, paths, note, label):
    output=['<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Leitura do código '+label+'</title><style>body{font:16px/1.6 system-ui;margin:30px;background:#f6f8fb;color:#172638}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd5df;padding:9px;vertical-align:top}code{white-space:pre-wrap;overflow-wrap:anywhere}h2{margin-top:45px}</style><h1>Leitura do código — '+label+'</h1><p>Fonte original do snapshot acumulado. Notas por linha são ajuda de leitura sintática, não uma revisão humana completa. Mudanças e autoria comprovável estão no diff e em proveniencia.json. Arquivos não Rust têm conteúdo e papel no projeto, sem notas Rust aplicadas indevidamente.</p>']
    if not paths:
        output.append('<p>Não há arquivo de implementação identificável neste marco. Leia o contrato e a proveniência: o prompt pode ser planejamento, organização, validação ou documentação. Isso não autoriza atribuir um programa ao seu texto.</p>')
    for path in paths:
        if path not in files:
            continue
        raw=files[path].decode('utf-8',errors='replace')
        output.append('<h2>'+html.escape(path)+'</h2>')
        if path.endswith('.rs'):
            output.append('<table><tr><th>Linha</th><th>Código</th><th>Explicação de leitura</th></tr>')
            for number,line in enumerate(raw.splitlines(),1):
                output.append(f'<tr><td>{number}</td><td><code>{html.escape(line)}</code></td><td>{html.escape(note(line))}</td></tr>')
            output.append('</table>')
        else:
            output.append('<pre><code>'+html.escape(raw)+'</code></pre>')
    return ''.join(output)+'</html>'


def build():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    note=note_reader()
    index=[]
    for repo,prefix,folder,mapping in [(ROOT,'P','broker',BROKER),(ROOT.parent/'xmqr-client','C','clients',CLIENT)]:
        commits=git(repo,'rev-list','--reverse','HEAD').decode().splitlines()
        positions={commit:i for i,commit in enumerate(commits)}
        previous=None
        originals={}
        cumulative_documents={}
        origin={}
        cache={}
        for prompt in sorted((repo/'prompts'/folder).glob('*.md')):
            identifier=int(prompt.name.split('-')[0])
            label=f'{prefix}{identifier:02d}'
            reference=git(repo,'rev-parse',mapping[identifier]).decode().strip() if identifier in mapping else None
            if prefix=='P' and identifier==70:
                candidate=git(repo,'log','-1','--format=%H','--fixed-strings','--grep=docs: preparar curso Udemy e pacotes P70').decode().strip()
                reference=candidate or None
            before=previous
            if reference is not None and (previous is None or positions[reference]>positions[previous]):
                previous=reference
            commit=previous
            if commit:
                if commit not in cache:
                    cache[commit]=snapshot(repo,commit)
                originals,excluded=cache[commit]
            else:
                originals={}
                excluded=[]
            cumulative_documents[f'materiais-acumulados/{label}/{prompt.name}']=prompt.read_bytes()
            records=list((repo/'prompts/registros').glob(f'{prefix}{identifier}-*.md'))
            for record in records:
                cumulative_documents[f'materiais-acumulados/{label}/{record.name}']=record.read_bytes()
            changes=[]
            if reference:
                diff_base=before if before and positions[before]<positions[reference] else git(repo,'rev-parse',reference+'^').decode().strip()
                changes=git(repo,'diff','--name-only',diff_base,reference).decode().splitlines()
                for name in changes:
                    origin.setdefault(name,[]).append(label)
            status=('marco_git_relacionado' if reference else ('sem_marco_proprio_codigo_herdado' if commit else 'documentos_sem_snapshot_comprovavel'))
            info={'id':label,'prompt':prompt.name,'status':status,'snapshot_cumulativo':commit,'marco_relacionado':reference,'arquivos_do_marco':changes,'registros':[r.name for r in records],'exclusoes':excluded,'observacao':'O marco Git relacionado pode agrupar alterações de mais de um prompt; diff não prova autoria exclusiva. IDs podem ser executados fora de ordem. A acumulação nunca volta a um commit anterior.'}
            if commit:
                overview=f'Código acumulado recuperado do commit {commit}. O pacote contém todos os arquivos Git desse snapshot, exceto artefatos gerados explicitamente listados. '
                if not reference:
                    overview+='Este prompt não tem uma entrega de código separada comprovada. O código nesta pasta é herdado do último marco conhecido, não foi gerado por este prompt. '
                elif commit!=reference:
                    overview+='A execução deste ID ocorreu fora da ordem numérica. O snapshot acumulado mantém o marco mais recente já incluído; o diff mostra o marco associado a este prompt. '
            else:
                overview='Não foi encontrado snapshot Git que represente código gerado por este prompt. Este ZIP contém contrato, explicação e materiais anteriores; não há código inventado. A história importada não registra todos os passos antigos de criação. '
            explanation=f'# {label}: entrega e código acumulado\n\n{overview}\n\n## Como estudar o pacote\n\n1. Leia o contrato em prompt.md: é o pedido da tarefa.\n2. Leia proveniencia.json: mostra o que pode ser associado ao histórico.\n3. Abra explicacao-do-codigo.html para consultar os arquivos do marco e as notas.\n4. Confira alteracoes-do-marco.diff para ver o que mudou nesse commit.\n5. Use codigo/ para executar o projeto no ambiente daquela versão.\n6. Use codigo-com-anotacoes/ apenas para ler as legendas de origem; codigo/ é a fonte íntegra.\n\n## Termos\n\nContexto de entrada: versão, arquivos, ambiente e funcionalidades existentes antes da tarefa; não são dados recebidos pelo programa.\nFronteiras do projeto: quais responsabilidades pertencem ao broker, ao client e à aplicação que usa os dois.\nRuntime: infraestrutura que funciona durante a execução do programa; o runtime Tokio agenda tarefas assíncronas e atende eventos de I/O.\nRegistro: relatório do que foi feito, comandos executados e seus resultados; o pedido sozinho não prova a implementação.\n\n## Quando não há registro\n\nNão encontramos um relatório separado identificado por este ID. Isso não prova que nada foi feito, mas impede afirmar uma entrega específica só pela existência do prompt.\n\n## Código e comentários\n\nOs comentários de origem indicam arquivos alterados nos marcos relacionados, não que todas as linhas do arquivo tenham sido escritas por esse único prompt. Marcos históricos podem reunir vários trabalhos. O código original não foi modificado para inserir legendas.\n'
            if identifier==0 and prefix=='P':
                explanation+='\nP00 descreve a situação inicial verificada do projeto: versão, protocolo, capacidades e limites. Não recebe mensagens MQTT nem cria o runtime do servidor.\n'
            if identifier==1 and prefix=='P':
                explanation+='\nP01 orienta a sequência de trabalho da IA: conferir o repositório, preparar a alteração, implementar somente o pedido e validar. Não contém uma implementação Rust nem gera um executável sozinho. Por isso não há pasta de código inventada como entrega P01.\n'
            contents=dict(cumulative_documents)
            contents['prompt.md']=prompt.read_bytes()
            contents['LEIA-PRIMEIRO.md']=explanation.encode()
            contents['proveniencia.json']=json.dumps(info,ensure_ascii=False,indent=2).encode()
            contents['alteracoes-do-marco.diff']=git(repo,'diff','--no-ext-diff',diff_base,reference) if reference else b'Nenhum marco Git separado associado a este prompt.\n'
            paths=[p for p in changes if p in originals and (p.endswith('.rs') or p=='Cargo.toml' or p.startswith('scripts/'))]
            contents['explicacao-do-codigo.html']=source_html(originals,paths,note,label).encode()
            (OUTPUT/(label+'-codigo-explicado.html')).write_bytes(contents['explicacao-do-codigo.html'])
            for name,data in originals.items():
                contents['codigo/'+name]=data
                if name.endswith('.rs'):
                    attribution=', '.join(origin.get(name,[]))
                    header=('// Comandos gerados ou alterados nos marcos relacionados: '+attribution+'.\n// A legenda descreve mudanças no arquivo; não atribui todas as linhas ao mesmo prompt.\n') if attribution else '// Código herdado: autoria por prompt não comprovada no histórico disponível.\n'
                    contents['codigo-com-anotacoes/'+name]=header.encode()+data
            filename=label+'-cumulativo.zip'
            target=OUTPUT/filename
            with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
                for name,data in sorted(contents.items()):
                    if not valid_path(name):
                        raise ValueError('Caminho ZIP inseguro')
                    archive.writestr(name,data)
            with zipfile.ZipFile(target) as archive:
                if archive.testzip() is not None:
                    raise ValueError('ZIP corrompido')
                for name,data in originals.items():
                    if archive.read('codigo/'+name)!=data:
                        raise ValueError('Snapshot divergente')
            info.update({'arquivo':filename,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'arquivos_codigo':len(originals)})
            index.append(info)
    (OUTPUT/'indice.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUTPUT/'SHA256SUMS.txt').write_text(''.join(item['sha256']+'  '+item['arquivo']+'\n' for item in index),encoding='utf-8')
    index_html='<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>ZIPs cumulativos</title><h1>Pacotes cumulativos por prompt</h1><p>Arquivos de código preservam o snapshot comprovável. Planos sem entrega própria não recebem código inventado. Consulte LEIA-PRIMEIRO.md em cada pacote.</p><table><tr><th>ID</th><th>Download</th><th>Arquivos de código</th><th>Estado</th></tr>'+''.join(f'<tr><td>{item["id"]}</td><td><a href="{item["arquivo"]}">{item["arquivo"]}</a></td><td>{item["arquivos_codigo"]}</td><td>{item["status"]}</td></tr>' for item in index)+'</table></html>'
    for name,label in [('projeto-inicial','Base P00/P03 para Rust Windows'),('serie-didatica','Etapas novas P03/P04/P05 — código cumulativo comentado')]:
        if (OUTPUT.parent/name/'index.html').exists():
            index_html=index_html.replace('<table>','<p><a href="../'+name+'/index.html">'+label+'</a></p><table>',1)
    (OUTPUT/'index.html').write_text(index_html,encoding='utf-8')
    print(f'{len(index)} ZIPs verificados em {OUTPUT}; {sum(i["bytes"] for i in index):,} bytes.')


if __name__=='__main__':
    build()
