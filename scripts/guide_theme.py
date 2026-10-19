#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P236: acrescenta temas ao guia existente sem regenerar seu conteúdo histórico.

``enhance(document)`` é puro e idempotente. ``enhance_file(path)`` só grava
quando necessário e conserva o BOM e o conteúdo fora dos blocos desta extensão.
Não lê arquivos de configuração nem carrega recursos externos.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re


VERSION = "1.0"
STORAGE_KEY = "xmqr-code-guide-theme"

# Executado antes dos estilos e do body: a primeira pintura já usa a preferência.
BOOT_SCRIPT = r"""(function () {
  'use strict';
  var theme = 'light';
  try {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) theme = 'dark';
  } catch (_) { /* Sem matchMedia, o tema inicial é claro. */ }
  try {
    var saved = window.localStorage.getItem('xmqr-code-guide-theme');
    if (saved === 'light' || saved === 'dark') theme = saved;
  } catch (_) { /* Armazenamento bloqueado não impede a leitura. */ }
  document.documentElement.dataset.theme = theme;
})();"""

STYLE = r"""
:root, html[data-theme="light"] {
  color-scheme: light;
  --guide-bg: #f3f6fb;
  --guide-text: #203249;
  --guide-muted: #50667c;
  --guide-surface: #ffffff;
  --guide-soft: #e9f0f7;
  --guide-line: #c7d5e3;
  --guide-heading: #085b7e;
  --guide-accent: #17694c;
  --guide-link: #075e8a;
  --guide-header-start: #e4eef8;
  --guide-header-end: #eef3fa;
  --guide-code: #edf3f9;
  --guide-source: #f7faff;
  --guide-source-even: #eaf1f8;
  --guide-source-hover: #dce9f4;
  --guide-source-text: #203a56;
  --guide-source-head: #e0ebf5;
  --guide-meaning: #24564c;
  --guide-number: #506c87;
  --guide-active: #dcebf4;
  --guide-active-text: #153b55;
  --guide-control: #e2edf5;
  --guide-control-text: #153e5a;
  --guide-control-line: #7d9db8;
  --guide-focus: #8b4d00;
  --guide-badge: #75500b;
  --guide-badge-line: #bea46a;
  --guide-shadow: #203c551f;
}
html[data-theme="dark"] {
  color-scheme: dark;
  --guide-bg: #0c1320;
  --guide-text: #e5edf8;
  --guide-muted: #a8bdd1;
  --guide-surface: #121e30;
  --guide-soft: #172738;
  --guide-line: #3b526c;
  --guide-heading: #90d9f4;
  --guide-accent: #8de2b5;
  --guide-link: #9bdcf5;
  --guide-header-start: #122d46;
  --guide-header-end: #182039;
  --guide-code: #0b1423;
  --guide-source: #09111e;
  --guide-source-even: #0d1928;
  --guide-source-hover: #203145;
  --guide-source-text: #d9e7f5;
  --guide-source-head: #102033;
  --guide-meaning: #b4d8d0;
  --guide-number: #9bb2c9;
  --guide-active: #20394d;
  --guide-active-text: #ffffff;
  --guide-control: #213e55;
  --guide-control-text: #ffffff;
  --guide-control-line: #6d95ae;
  --guide-focus: #a9e4fb;
  --guide-badge: #f0d293;
  --guide-badge-line: #a38a53;
  --guide-shadow: #00000044;
}
html[data-theme] { background: var(--guide-bg); }
html[data-theme] body { background: var(--guide-bg); color: var(--guide-text); }
html[data-theme] header {
  background: linear-gradient(120deg, var(--guide-header-start), var(--guide-header-end));
  color: var(--guide-text); border-color: var(--guide-line);
}
html[data-theme] h1, html[data-theme] h3 { color: var(--guide-text); }
html[data-theme] h2, html[data-theme] th { color: var(--guide-heading); }
html[data-theme] a { color: var(--guide-link); }
html[data-theme] .label, html[data-theme] .sidebar-heading { color: var(--guide-accent); }
html[data-theme] .subtitle, html[data-theme] .sidebar-hint,
html[data-theme] .nav-children > summary, html[data-theme] footer { color: var(--guide-muted); }
html[data-theme] .card, html[data-theme] .sidebar {
  background: var(--guide-surface); color: var(--guide-text); border-color: var(--guide-line);
}
html[data-theme] .course-section > h2 { border-color: var(--guide-accent); }
html[data-theme] .sidebar .nav-group { border-color: var(--guide-line); }
html[data-theme] .sidebar .nav-group > h3 { color: var(--guide-heading); }
html[data-theme] nav a { color: var(--guide-link); border-color: var(--guide-line); }
html[data-theme] nav a:hover, html[data-theme] .sidebar .nav-link::before { color: var(--guide-accent); }
html[data-theme] .sidebar .nav-link[aria-expanded="true"] {
  background: var(--guide-active); color: var(--guide-active-text); border-left-color: var(--guide-accent);
}
html[data-theme] .sidebar .nav-link[aria-current="location"] { outline-color: var(--guide-heading); }
html[data-theme] .topic, html[data-theme] .topic[open] > summary { border-color: var(--guide-line); }
html[data-theme] .topic > summary { background: var(--guide-soft); color: var(--guide-heading); }
html[data-theme] summary, html[data-theme] .subtopic > summary { color: var(--guide-heading); }
html[data-theme] .badge { color: var(--guide-badge); border-color: var(--guide-badge-line); }
html[data-theme] pre { background: var(--guide-code); color: var(--guide-source-text); }
html[data-theme] code { color: inherit; }
html[data-theme] .source { background: var(--guide-source); color: var(--guide-source-text); }
html[data-theme] .source::before {
  background: var(--guide-source-head); color: var(--guide-accent); border-color: var(--guide-line);
}
html[data-theme] .line { border-color: var(--guide-line); }
html[data-theme] .line:nth-child(even) { background: var(--guide-source-even); }
html[data-theme] .line:hover { background: var(--guide-source-hover); }
html[data-theme] .line code { color: var(--guide-source-text); }
html[data-theme] .num { color: var(--guide-number); }
html[data-theme] .meaning { color: var(--guide-meaning); border-color: var(--guide-line); }
html[data-theme] th, html[data-theme] td { border-color: var(--guide-line); }
html[data-theme] .flow { background: var(--guide-soft); color: var(--guide-text); border-color: var(--guide-accent); }
html[data-theme] input, html[data-theme] select, html[data-theme] textarea {
  background: var(--guide-surface); color: var(--guide-text); border-color: var(--guide-control-line);
  accent-color: var(--guide-link);
}
html[data-theme] input::placeholder, html[data-theme] textarea::placeholder { color: var(--guide-muted); opacity: 1; }
html[data-theme] button, html[data-theme] .action-link {
  background: var(--guide-control); color: var(--guide-control-text); border-color: var(--guide-control-line);
}
html[data-theme] button:hover, html[data-theme] .action-link:hover { background: var(--guide-active); color: var(--guide-active-text); }
html[data-theme] :focus-visible { outline: 3px solid var(--guide-focus); outline-offset: 3px; }
#guide-theme-controls {
  position: fixed; right: 20px; top: 16px; z-index: 40; max-width: calc(100vw - 32px);
}
html[data-theme] #guide-theme-toggle {
  display: inline-flex; align-items: center; gap: 8px; min-height: 42px; padding: 9px 13px;
  font: 600 13px/1.4 system-ui, sans-serif; border-radius: 7px; box-shadow: 0 3px 12px var(--guide-shadow);
}
#guide-theme-toggle::before { content: '\263e'; font-size: 19px; line-height: 1; }
#guide-theme-toggle[aria-pressed="true"]::before { content: '\2713'; font-size: 15px; }
@media (max-width: 800px) {
  #guide-theme-controls { top: 10px; right: 16px; }
  html[data-theme] body > header { padding-top: 72px; }
  html[data-theme] #guide-theme-toggle { min-height: 40px; padding: 8px 11px; font-size: 12px; }
}
@media print {
  #guide-theme-controls { display: none !important; }
  html[data-theme], html[data-theme] body, html[data-theme] header,
  html[data-theme] .card, html[data-theme] .topic, html[data-theme] .topic > summary,
  html[data-theme] .source, html[data-theme] pre, html[data-theme] .source::before,
  html[data-theme] .line:nth-child(even), html[data-theme] .line:hover, html[data-theme] .flow {
    background: #ffffff !important; color: #111111 !important; box-shadow: none !important;
  }
  html[data-theme] h1, html[data-theme] h2, html[data-theme] h3,
  html[data-theme] .line code, html[data-theme] .meaning, html[data-theme] .num,
  html[data-theme] a, html[data-theme] summary, html[data-theme] th,
  html[data-theme] .label, html[data-theme] .subtitle, html[data-theme] .badge,
  html[data-theme] footer { color: #111111 !important; }
  html[data-theme] .meaning, html[data-theme] .line, html[data-theme] th,
  html[data-theme] td, html[data-theme] .topic, html[data-theme] .card,
  html[data-theme] .course-section > h2 { border-color: #999999 !important; }
  html[data-theme] .source { max-height: none; overflow: visible; }
  html[data-theme] .line { min-width: 0; }
  html[data-theme] body > header { padding-top: 24px; }
}
"""

CONTROLS = """<div id="guide-theme-controls" aria-label="Aparência do curso">
<button id="guide-theme-toggle" type="button" aria-pressed="false">Modo escuro</button>
</div>"""

SCRIPT = r"""(function () {
  'use strict';
  var key = 'xmqr-code-guide-theme';
  var root = document.documentElement;
  var button = document.getElementById('guide-theme-toggle');
  if (!button) return;
  var choice = null;
  var media = null;
  function valid(value) { return value === 'light' || value === 'dark'; }
  try {
    var stored = window.localStorage.getItem(key);
    if (valid(stored)) choice = stored;
  } catch (_) { /* A escolha ainda funciona na memória da página. */ }
  try { media = window.matchMedia('(prefers-color-scheme: dark)'); } catch (_) {}
  function systemTheme() { return media && media.matches ? 'dark' : 'light'; }
  function apply(theme) {
    root.dataset.theme = theme;
    button.setAttribute('aria-pressed', String(theme === 'dark'));
    button.title = theme === 'dark' ? 'Modo escuro ativo. Clique para usar o modo claro.' : 'Clique para usar o modo escuro.';
  }
  apply(choice || systemTheme());
  button.addEventListener('click', function () {
    choice = root.dataset.theme === 'dark' ? 'light' : 'dark';
    apply(choice);
    try { window.localStorage.setItem(key, choice); } catch (_) {}
  });
  function followSystem() { if (choice === null) apply(systemTheme()); }
  if (media) {
    if (typeof media.addEventListener === 'function') media.addEventListener('change', followSystem);
    else if (typeof media.addListener === 'function') media.addListener(followSystem);
  }
  window.addEventListener('storage', function (event) {
    if (event.key !== key && event.key !== null) return;
    choice = valid(event.newValue) ? event.newValue : null;
    apply(choice || systemTheme());
  });
})();"""

_BLOCKS = re.compile(
    r"<!-- XMQR:P236:theme:(boot|style|controls|script):start -->.*?"
    r"<!-- XMQR:P236:theme:\1:end -->",
    re.DOTALL,
)
_RESERVED_IDS = re.compile(
    r"\bid\s*=\s*(['\"])guide-theme-(?:boot|style|controls|toggle|script)\1",
    re.IGNORECASE,
)


def _block(name: str, content: str) -> str:
    return (
        f"<!-- XMQR:P236:theme:{name}:start -->\n"
        f"{content}\n<!-- XMQR:P236:theme:{name}:end -->"
    )


def enhance(document: str) -> str:
    """Insere ou atualiza somente os quatro blocos reservados de tema P236.

    O retorno é idêntico em chamadas repetidas da mesma versão. Documento
    incompleto ou IDs reservados fora dos blocos são recusados sem alteração.
    """
    if not isinstance(document, str):
        raise TypeError("O documento HTML deve ser texto.")
    clean = _BLOCKS.sub("", document)
    if _RESERVED_IDS.search(clean):
        raise ValueError("O HTML já usa IDs reservados para o tema do guia.")
    required = (r"<head\b[^>]*>", r"</head\s*>", r"<body\b[^>]*>", r"</body\s*>")
    if not all(re.search(pattern, clean, re.IGNORECASE) for pattern in required):
        raise ValueError("O guia deve conter head e body completos.")
    boot = _block("boot", f'<script id="guide-theme-boot">{BOOT_SCRIPT}</script>')
    style = _block("style", f'<style id="guide-theme-style">{STYLE}</style>')
    controls = _block("controls", CONTROLS)
    script = _block("script", f'<script id="guide-theme-script">{SCRIPT}</script>')
    result = re.sub(r"(<head\b[^>]*>)", lambda match: match[0] + boot, clean, count=1, flags=re.IGNORECASE)
    result = re.sub(r"</head\s*>", lambda match: style + match[0], result, count=1, flags=re.IGNORECASE)
    result = re.sub(r"(<body\b[^>]*>)", lambda match: match[0] + controls, result, count=1, flags=re.IGNORECASE)
    return re.sub(r"</body\s*>", lambda match: script + match[0], result, count=1, flags=re.IGNORECASE)


def enhance_file(path: str | Path) -> bool:
    """Atualiza o HTML explicitamente indicado e retorna se houve mudança."""
    target = Path(path)
    data = target.read_bytes()
    bom = b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b""
    document = data.decode("utf-8-sig")
    result = enhance(document)
    if result == document:
        return False
    target.write_bytes(bom + result.encode("utf-8"))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Acrescenta tema claro/escuro ao guia HTML existente.")
    parser.add_argument("--html", type=Path, required=True, help="Caminho do guia HTML a atualizar.")
    args = parser.parse_args()
    try:
        changed = enhance_file(args.html)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"Não foi possível atualizar o guia: {error}\n")
    print("Tema do guia atualizado." if changed else "O tema do guia já está atualizado.")


if __name__ == "__main__":
    main()
