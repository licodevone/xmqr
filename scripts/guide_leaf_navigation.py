#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P236: links diretos para itens do curso sem subtópicos na sidebar."""
import argparse
from dataclasses import dataclass, field
import html
from html.parser import HTMLParser
from pathlib import Path
import re


@dataclass
class Node:
    tag: str
    attrs: list
    start: int
    opening_end: int
    closing_start: int = 0
    end: int = 0
    parent: object = None
    children: list = field(default_factory=list)

    def has_class(self, value):
        return value in (dict(self.attrs).get('class') or '').split()


class NavigationParser(HTMLParser):
    """Track ranges so the historical lesson HTML never needs serialization."""
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.stack, self.nodes = [], []

    def character_offset(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.character_offset()
        node = Node(tag, attrs, start, start + len(self.get_starttag_text()),
                    parent=self.stack[-1] if self.stack else None)
        if node.parent:
            node.parent.children.append(node)
        self.nodes.append(node)
        if tag in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
                   'meta', 'param', 'source', 'track', 'wbr'}:
            node.closing_start = node.end = node.opening_end
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1].tag == tag:
            node = self.stack.pop()
            node.closing_start = node.end = node.opening_end

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                node = self.stack[index]
                node.closing_start = self.character_offset()
                node.end = self.source.index('>', node.closing_start) + 1
                del self.stack[index:]
                break


STYLE = '''<style id="p236-leaf-navigation-style">
#course-nav a.nav-leaf::before,#course-nav a.nav-leaf::after{content:none!important;display:none!important}
#course-nav a.nav-leaf{display:block;list-style:none}
#course-nav a.nav-leaf:focus-visible{outline:3px solid #67afc4;outline-offset:3px}
</style>'''

SCRIPT = '''<script id="p236-leaf-navigation-script">
(()=>{
  "use strict";
  const nav=document.getElementById("course-nav");
  if(!nav)return;
  const clean=()=>nav.querySelectorAll("a.nav-leaf[aria-expanded]").forEach(link=>link.removeAttribute("aria-expanded"));
  if(typeof window.sync==="function"){
    const original=window.sync;
    window.sync=function(...args){const result=original.apply(this,args);clean();return result;};
  }
  nav.addEventListener("click",event=>{
    const link=event.target.closest("a.nav-leaf");
    if(!link||!nav.contains(link))return;
    let identifier=link.hash.slice(1);
    try{identifier=decodeURIComponent(identifier);}catch{return;}
    const target=document.getElementById(identifier);
    if(!target||!target.closest("main"))return;
    event.preventDefault();event.stopImmediatePropagation();
    if(location.hash!==link.hash)history.pushState(null,"",link.hash);
    if(typeof window.visit==="function")window.visit(target);
    else{
      for(let node=target;node;node=node.parentElement)if(node.tagName==="DETAILS")node.open=true;
      const detail=target.matches("section")?target.querySelector(":scope > details"):target.closest("details");
      if(detail)detail.open=true;
      target.scrollIntoView({block:"start"});
    }
    if(typeof window.closeMenu==="function")window.closeMenu();
    clean();
  },true);
  new MutationObserver(clean).observe(nav,{subtree:true,attributes:true,attributeFilter:["aria-expanded"]});
  clean();
})();
</script>'''


def leaf_anchor(source, anchor):
    classes = dict(anchor.attrs).get('class', '').split()
    if 'nav-leaf' in classes and 'aria-expanded' not in dict(anchor.attrs):
        return source[anchor.start:anchor.end]
    classes = list(dict.fromkeys([*classes, 'nav-leaf']))
    attrs = []
    for name, value in anchor.attrs:
        if name == 'aria-expanded':
            continue
        if name == 'class':
            value = ' '.join(classes)
        attrs.append(name if value is None else f'{name}="{html.escape(value, quote=True)}"')
    if 'class' not in dict(anchor.attrs):
        attrs.append('class="nav-link nav-leaf"')
    return '<a ' + ' '.join(attrs) + '>' + source[anchor.opening_end:anchor.end]


def enhance(document):
    match = re.search(r'<nav\b[^>]*\bid=["\']course-nav["\'][^>]*>.*?</nav\s*>', document,
                      flags=re.S | re.I)
    if not match:
        raise ValueError('P236: sidebar #course-nav não encontrada')
    source = match.group(0)
    parser = NavigationParser(source)
    parser.feed(source)
    replacements, converted = [], []
    for node in parser.nodes:
        if node.tag != 'details' or not node.has_class('nav-topic'):
            continue
        summaries = [child for child in node.children if child.tag == 'summary']
        children = [child for child in node.children if child.tag == 'div' and child.has_class('nav-children')]
        if len(summaries) != 1 or len(children) != 1:
            continue
        child = children[0]
        if not child.end or re.sub(r'<!--.*?-->', '', source[child.opening_end:child.closing_start], flags=re.S).strip():
            continue
        anchors = [child for child in summaries[0].children if child.tag == 'a' and child.has_class('nav-link')]
        if len(anchors) != 1 or not anchors[0].end or not node.end:
            raise ValueError('P236: link de aula sem filhos inválido')
        replacements.append((node.start, node.end, leaf_anchor(source, anchors[0])))
        converted.append((node.start, node.end))
    for node in parser.nodes:
        if node.tag != 'a' or not node.has_class('nav-link') or not node.end:
            continue
        if any(start <= node.start < end for start, end in converted):
            continue
        parent = node.parent
        in_children = False
        while parent:
            in_children |= parent.has_class('nav-children')
            parent = parent.parent
        owner = node.parent.parent if node.parent and node.parent.tag == 'summary' else None
        parent_control = owner and owner.tag == 'details' and owner.has_class('nav-topic')
        if (in_children and not parent_control) or node.has_class('nav-leaf'):
            replacements.append((node.start, node.end, leaf_anchor(source, node)))
    for start, end, value in sorted(replacements, reverse=True):
        source = source[:start] + value + source[end:]
    document = document[:match.start()] + source + document[match.end():]
    if 'id="p236-leaf-navigation-style"' not in document:
        if '</head>' not in document:
            raise ValueError('P236: fechamento de head ausente')
        document = document.replace('</head>', STYLE + '\n</head>', 1)
    if 'id="p236-leaf-navigation-script"' not in document:
        if '</body>' not in document:
            raise ValueError('P236: fechamento de body ausente')
        document = document.replace('</body>', SCRIPT + '\n</body>', 1)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, required=True)
    args = parser.parse_args()
    original = args.html.read_text(encoding='utf-8')
    updated = enhance(original)
    if original != updated:
        args.html.write_text(updated, encoding='utf-8')
    print('P236: navegação sem expansão aplicada; aulas preservadas')


if __name__ == '__main__':
    main()
