"""Navegação P67: links acessíveis controlam seções e subtópicos do curso."""
import html
import re
import json
from pathlib import Path
from guide_udemy import GROUPS


def navigation(parts):
    topics = []
    updated = []
    for number, part in enumerate(parts):
        match = re.fullmatch(r'<section id="([^"]+)"><h2>(.*?)</h2>(.*)</section>', part, re.S)
        if not match:
            raise ValueError('Seção inesperada no gerador de navegação')
        identifier, title, body = match.groups()
        children = []

        def subtopic(card):
            prefix, heading, content = card.groups()
            if identifier=='prompts':
                heading='Aula '+str(len(children)+1)+' — '+heading
            child_id = f'{identifier}-topic-{len(children) + 1}'
            children.append((child_id, heading))
            return f'{prefix}<details id="{child_id}" class="subtopic"><summary><h3>{heading}</h3></summary><div class="topic-body">{content}</div></details></article>'

        body = re.sub(r'(<article\b[^>]*>)<h3>(.*?)</h3>(.*?)</article>', subtopic, body, flags=re.S)
        opened = ' open' if number == 0 else ''
        updated.append(f'<section id="{identifier}"><details class="topic"{opened}><summary><h2>{title}</h2></summary><div class="topic-body">{body}</div></details></section>')
        topics.append((identifier, title, children))

    groups = GROUPS

    def link(identifier, label):
        return f'<a class="nav-link" href="#{identifier}" aria-controls="{identifier}" aria-expanded="false">{label}</a>'

    sidebar = '<div class="sidebar-heading">Conteúdo do curso</div><p class="sidebar-hint">Abertura e fechamento sincronizados com o texto.</p><a class="action-link open-all" href="#course-topics">Abrir todos os tópicos</a>'
    curriculum=[]
    by_id={identifier:part for (identifier,_,_),part in zip(topics,updated)}
    grouped=[]
    for index, (title, identifiers) in enumerate(groups):
        rows = []
        section_parts=[]
        lessons=[]
        topic_map={identifier:(label,children) for identifier,label,children in topics}
        for number,identifier in enumerate(identifiers,1):
            label,children=topic_map[identifier]
            label=f'Aula {index+1}.{number} — '+label
            rows.append(f'<details class="nav-topic" data-topic="{identifier}"><summary>{link(identifier, label)}</summary><div class="nav-children">' + ''.join(link(child, text) for child, text in children) + '</div></details>')
            section_parts.append(by_id[identifier].replace('<h2>'+topic_map[identifier][0]+'</h2>','<h2>'+label+'</h2>',1))
            lessons.append({'titulo':html.unescape(label),'ancora':identifier,'partes':[{'titulo':html.unescape(text),'ancora':child} for child,text in children]})
        sidebar += f'<div class="nav-group"><h3>{html.escape(title)}</h3>{"".join(rows)}</div>'
        grouped.append(f'<div class="course-section" id="secao-{index+1}"><h2>{html.escape(title)}</h2>'+''.join(section_parts)+'</div>')
        curriculum.append({'secao':title,'aulas':lessons})
    folder=Path(__file__).resolve().parents[2]/'docs/curso-udemy'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'curriculo.json').write_text(json.dumps(curriculum,ensure_ascii=False,indent=2),encoding='utf-8')
    return grouped, sidebar


STYLE = '''
.course-section{margin:50px 0}.course-section>h2{padding-bottom:16px;border-bottom:2px solid #8de2b5}
.layout{grid-template-columns:280px minmax(0,1fr);max-width:1440px}
.sidebar{background:#111e30;border:1px solid #2a3c54;border-radius:12px;padding:18px;scrollbar-width:thin}
.sidebar-heading{font-size:16px;font-weight:700;color:#8de2b5}.sidebar-hint{font-size:12px;color:#a3b8cc;margin:8px 0 16px}
.sidebar .nav-group{border-top:1px solid #30435e;padding-top:8px}.sidebar .nav-group>summary{font-size:14px}
.sidebar .nav-link{display:block;font-size:13px;line-height:1.5;padding:9px 10px;margin:3px 0;border-radius:5px;border-left:3px solid transparent}
.sidebar .nav-link::before{content:'＋';display:inline-block;width:20px;color:#8de2b5}
.sidebar .nav-link[aria-expanded=true]{background:#20394d;border-left-color:#8de2b5;color:#fff}
.sidebar .nav-link[aria-expanded=true]::before{content:'−'}
.sidebar .nav-link[aria-current=location]{outline:1px solid #67afc4}
.nav-children{margin:0 0 10px 18px}.nav-children>summary{font-size:12px;color:#a3b8cc}.nav-children .nav-link{font-size:12px}
.nav-group>h3{font-size:14px;color:#90d9f4;margin:12px 0}.nav-topic{margin:4px 0}.nav-topic>summary{padding:0;list-style-position:inside}.nav-topic>summary>.nav-link{display:inline;padding:6px 2px;line-height:1.6;border:0}.nav-topic>summary>.nav-link::before{display:none}.action-link{display:inline-block;padding:10px;border:1px solid #5a8399;border-radius:6px;background:#213e55;color:#fff;text-decoration:none}.sidebar>.action-link{font-size:13px;margin-bottom:12px}
.topic{border:1px solid #30435e;border-radius:10px;margin:0;overflow:hidden}
.topic>summary{display:list-item;padding:20px 24px;background:#142338;list-style-position:inside}
.topic>summary h2{display:inline;font-size:25px;margin:0}.topic-body{padding:10px 24px 24px}
.subtopic{margin:0}.subtopic>summary{list-style-position:inside}.subtopic>summary h3{display:inline;font-size:20px;margin:0}
.subtopic>.topic-body{padding:8px 0}.topic[open]>summary{border-bottom:1px solid #30435e}
section{margin-bottom:22px}.toolbar{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 24px}
#menu-toggle{display:none}.nav-link:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #90d9f4;outline-offset:3px}
@media(max-width:800px){.layout{display:block}.sidebar{display:none;position:fixed;top:66px;left:16px;right:16px;max-height:75vh;overflow:auto;z-index:30;box-shadow:0 15px 40px #0008;margin:0}.sidebar.is-open{display:block}#menu-toggle{display:block;position:sticky;top:10px;z-index:31;margin:10px 16px}.topic>summary{padding:16px}.topic>summary h2{font-size:22px}.topic-body{padding:8px 16px 16px}header{padding-top:24px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{.sidebar,#menu-toggle,.toolbar{display:none!important}.topic,.topic>summary{background:#fff;color:#111}.topic-body{padding:8px}}
'''


SCRIPT = '''
const sidebar=document.querySelector('#course-nav');
const menu=document.querySelector('#menu-toggle');
const links=[...sidebar.querySelectorAll('.nav-link')];
const topics=[...document.querySelectorAll('main .topic,main .subtopic')];
const navigationTopics=[...sidebar.querySelectorAll('.nav-topic')];
const input=document.querySelector('#search');
function ancestors(element){const list=[];for(let node=element.parentElement;node;node=node.parentElement){if(node.tagName==='DETAILS')list.push(node);}return list;}
function panel(target){return target.matches('section')?target.querySelector(':scope > details'):target.closest('details');}
function isVisibleOpen(detail){return detail.open&&ancestors(detail).every(parent=>parent.open);}
function sync(){links.forEach(link=>{const target=document.getElementById(link.hash.slice(1));link.setAttribute('aria-expanded',String(isVisibleOpen(panel(target))));if(link.hash===location.hash)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');});navigationTopics.forEach(item=>{item.open=isVisibleOpen(panel(document.getElementById(item.dataset.topic)));});}
function closeMenu(){sidebar.classList.remove('is-open');menu.setAttribute('aria-expanded','false');}
function reveal(target){const detail=panel(target);ancestors(detail).reverse().forEach(parent=>parent.open=true);detail.open=true;return detail;}
function visit(target,focus=true){const detail=reveal(target);sync();requestAnimationFrame(()=>{target.scrollIntoView({block:'start',behavior:'auto'});if(focus)detail.querySelector(':scope > summary').focus({preventScroll:true});});}
links.forEach(link=>link.addEventListener('click',event=>{event.preventDefault();const target=document.getElementById(link.hash.slice(1));const detail=panel(target);if(isVisibleOpen(detail)){detail.open=false;sync();}else{reveal(target);if(location.hash!==link.hash)history.pushState(null,'',link.hash);visit(target);}closeMenu();}));
topics.forEach(detail=>detail.addEventListener('toggle',sync));
navigationTopics.forEach(item=>item.addEventListener('toggle',()=>{const target=document.getElementById(item.dataset.topic);const detail=panel(target);if(item.open===isVisibleOpen(detail))return;if(item.open)reveal(target);else detail.open=false;sync();}));
function fromHash(){const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(target&&target.closest('main')&&panel(target))visit(target,false);else sync();}
addEventListener('hashchange',fromHash);addEventListener('popstate',fromHash);
menu.addEventListener('click',()=>{const opened=sidebar.classList.toggle('is-open');menu.setAttribute('aria-expanded',String(opened));if(opened)sidebar.querySelector('summary').focus();});
addEventListener('keydown',event=>{if(event.key==='Escape'&&sidebar.classList.contains('is-open')){closeMenu();menu.focus();}});
document.querySelectorAll('.open-all').forEach(control=>control.addEventListener('click',event=>{event.preventDefault();topics.forEach(detail=>detail.open=true);sync();}));
document.querySelector('#close-topics').addEventListener('click',()=>{topics.forEach(detail=>detail.open=false);sync();});
document.querySelector('#collapse')?.addEventListener('click',()=>{document.querySelectorAll('main details:not(.topic):not(.subtopic)').forEach(detail=>detail.open=false);});
input.addEventListener('input',()=>{const q=input.value.toLocaleLowerCase('pt-BR').trim();document.querySelectorAll('main .filter').forEach(card=>{card.hidden=Boolean(q&&!card.textContent.toLocaleLowerCase('pt-BR').includes(q));if(q&&!card.hidden){const detail=card.querySelector(':scope > details');if(detail)detail.open=true;ancestors(card).forEach(parent=>parent.open=true);}});sync();});
addEventListener('beforeprint',()=>{window.printState=[...document.querySelectorAll('main details')].map(detail=>[detail,detail.open]);window.printState.forEach(([detail])=>detail.open=true);});
addEventListener('afterprint',()=>{(window.printState||[]).forEach(([detail,opened])=>detail.open=opened);sync();});
fromHash();
'''
