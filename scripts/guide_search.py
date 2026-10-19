#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P238: busca em conteúdo incorporado, inclusive quando aberto por file://."""
import re

LEGACY = "input.addEventListener('input',()=>{const q=input.value.toLocaleLowerCase('pt-BR').trim();document.querySelectorAll('main .filter').forEach(card=>{card.hidden=Boolean(q&&!card.textContent.toLocaleLowerCase('pt-BR').includes(q));if(q&&!card.hidden){const detail=card.querySelector(':scope > details');if(detail)detail.open=true;ancestors(card).forEach(parent=>parent.open=true);}});sync();});"

STYLE = """<style id="guide-search-style">
#guide-search-controls { display:flex; align-items:center; flex-wrap:wrap; gap:12px; margin:0 0 8px; }
#guide-search-status { flex:1; margin:0; min-width:180px; }
#guide-search-hint { margin:0 0 20px; font-size:13px; color:var(--guide-muted); }
#guide-search-clear { min-height:44px; }
#guide-search-clear:disabled { opacity:.55; cursor:default; }
main .filter[hidden],main section[hidden],main .course-section[hidden],#course-nav [hidden] { display:none !important; }
@media print { #guide-search-controls,#guide-search-hint { display:none !important; } }
</style>"""

CONTROLS = """<div id="guide-search-controls">
<p id="guide-search-status" role="status" aria-live="polite" aria-atomic="true">Digite um termo para pesquisar.</p>
<button id="guide-search-clear" type="button" disabled>Limpar busca</button>
</div><p id="guide-search-hint">Busca local: pesquisa somente o conteúdo incorporado neste HTML, incluindo prompts e fontes recolhidos.</p>"""

SCRIPT = r"""<script id="guide-search-script">(function () {
  'use strict';
  var input = document.getElementById('search');
  var status = document.getElementById('guide-search-status');
  var clear = document.getElementById('guide-search-clear');
  if (!input || !status || !clear) return;
  input.setAttribute('aria-describedby', Array.from(new Set((input.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean).concat(['guide-search-status', 'guide-search-hint']))).join(' '));
  function normalize(text) {
    return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').replace(/\s+/g, ' ').trim();
  }
  function heading(node, selector) { var el = node && node.querySelector(selector); return el ? el.textContent : ''; }
  var cards = Array.from(document.querySelectorAll('main .filter')).map(function (node) {
    var context = heading(node.closest('section'), ':scope > details > summary, :scope > h2') + ' ' + heading(node.closest('.course-section'), ':scope > h2');
    return {node:node, text:normalize(context + ' ' + node.textContent), details:Array.from(node.querySelectorAll('details')).map(function (detail) {
      return {node:detail, text:normalize(context + ' ' + detail.textContent)};
    })};
  });
  var scopes = Array.from(document.querySelectorAll('main section, main .course-section')).map(function (node) {
    return {node:node, cards:cards.filter(function (card) { return node.contains(card.node); })};
  }).filter(function (scope) { return scope.cards.length; });
  var navLinks = Array.from(document.querySelectorAll('#course-nav .nav-link'));
  var navContainers = Array.from(document.querySelectorAll('#course-nav .nav-topic, #course-nav .nav-group')).reverse();
  var hiddenBefore = new Map(cards.map(function (card) { return [card.node,card.node.hidden]; }).concat(scopes.map(function (scope) { return [scope.node,scope.node.hidden]; }),navLinks.map(function (node) { return [node,node.hidden]; }),navContainers.map(function (node) { return [node,node.hidden]; })));
  var openedBefore = null;
  function syncNavigation() { if (typeof window.sync === 'function') window.sync(); }
  function apply() {
    var query = input.value.trim();
    var terms = normalize(query).split(' ').filter(Boolean);
    clear.disabled = !input.value.length;
    if (!terms.length) {
      hiddenBefore.forEach(function (hidden,node) { node.hidden = hidden; });
      if (openedBefore) openedBefore.forEach(function (open,node) { node.open = open; });
      openedBefore = null;
      status.textContent = 'Digite um termo para pesquisar.';
      syncNavigation();
      return;
    }
    if (!openedBefore) openedBefore = new Map(Array.from(document.querySelectorAll('main details')).map(function (node) { return [node,node.open]; }));
    function matches(text) { return terms.every(function (term) { return text.includes(term); }); }
    var count = 0;
    cards.forEach(function (card) {
      card.node.hidden = hiddenBefore.get(card.node) || !matches(card.text);
      if (card.node.hidden) return;
      count += 1;
      for (var ancestor = card.node.parentElement; ancestor; ancestor = ancestor.parentElement) {
        if (ancestor.tagName === 'DETAILS') ancestor.open = true;
      }
      card.details.forEach(function (detail) { if (matches(detail.text)) detail.node.open = true; });
    });
    scopes.forEach(function (scope) { scope.node.hidden = hiddenBefore.get(scope.node) || !scope.cards.some(function (card) { return !card.node.hidden; }); });
    navLinks.forEach(function (link) {
      var target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      link.hidden = hiddenBefore.get(link) || !target || !!target.closest('[hidden]');
    });
    navContainers.forEach(function (node) { node.hidden = hiddenBefore.get(node) || !Array.from(node.querySelectorAll('.nav-link')).some(function (link) { return !link.hidden; }); });
    status.textContent = count ? count + (count === 1 ? ' resultado para “' : ' resultados para “') + query + '”.' : 'Nenhum resultado para “' + query + '”. Tente outro termo ou limpe a busca.';
    syncNavigation();
  }
  function reset() { input.value = ''; apply(); input.focus(); }
  input.addEventListener('input',apply);
  input.addEventListener('keydown',function (event) { if (event.key === 'Escape') { event.preventDefault(); reset(); } });
  clear.addEventListener('click',reset);
  apply();
})();</script>"""


def block(name, value):
    return f'<!-- XMQR:P238:search:{name}:start -->\n{value}\n<!-- XMQR:P238:search:{name}:end -->'


def enhance(document):
    clean = re.sub(r'<!-- XMQR:P238:search:(style|controls|script):start -->.*?<!-- XMQR:P238:search:\1:end -->', '', document, flags=re.S)
    clean = clean.replace(LEGACY, '')
    if "input.addEventListener('input'," in clean:
        raise ValueError('Busca legada personalizada: revisar antes de substituir.')
    clean = clean.replace("document.querySelector('#collapse').addEventListener", "document.querySelector('#collapse')?.addEventListener")
    if re.search(r'\bid=[\"\']guide-search-', clean):
        raise ValueError('IDs reservados da busca já estão em uso.')
    inputs = list(re.finditer(r'<input\b[^>]*\bid=[\"\']search[\"\'][^>]*>', clean, re.I))
    if len(inputs) != 1 or '</head>' not in clean or '</body>' not in clean:
        raise ValueError('Busca exige head/body e um único campo search.')
    position = inputs[0].end()
    clean = clean[:position] + block('controls', CONTROLS) + clean[position:]
    clean = clean.replace('</head>', block('style', STYLE) + '</head>', 1)
    return clean.replace('</body>', block('script', SCRIPT) + '</body>', 1)
