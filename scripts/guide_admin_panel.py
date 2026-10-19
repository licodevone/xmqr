#!/usr/bin/env python3
"""Extensão P236: acrescenta operação A23–A25 sem refazer o snapshot do curso."""
from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import tempfile


FRAGMENT = Path(__file__).resolve().parents[1] / "docs" / "course-admin-web.html"
CONTENT_BEGIN = "<!-- XMQR_ADMIN_WEB_CONTENT_BEGIN -->"
CONTENT_END = "<!-- XMQR_ADMIN_WEB_CONTENT_END -->"
NAV_BEGIN = "<!-- XMQR_ADMIN_WEB_NAV_BEGIN -->"
NAV_END = "<!-- XMQR_ADMIN_WEB_NAV_END -->"


class _Headings(HTMLParser):
    """A sidebar usa os próprios títulos, evitando cópias divergentes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.group = ""
        self.lessons: list[tuple[str, str, list[tuple[str, str]]]] = []
        self.section: str | None = None
        self.child: str | None = None
        self.heading: str | None = None
        self.parts: list[str] = []
        self.identifiers: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            if not identifier.startswith("admin-web-") or identifier in self.identifiers:
                raise ValueError("IDs do fragmento devem ser únicos e começar com admin-web-")
            self.identifiers.add(identifier)
        if tag == "section":
            self.section = identifier
        if tag == "details" and "subtopic" in attributes.get("class", "").split():
            self.child = identifier
        if tag in {"h2", "h3"}:
            self.heading = tag
            self.parts = []
        if tag == "input" and attributes.get("type") == "checkbox" and "checked" in attributes:
            raise ValueError("Checklist deve começar totalmente desmarcado")

    def handle_data(self, data: str) -> None:
        if self.heading:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self.heading:
            text = "".join(self.parts).strip()
            if tag == "h2":
                if self.section:
                    self.lessons.append((self.section, text, []))
                elif self.group:
                    raise ValueError("Fragmento deve conter um único título de seção")
                else:
                    self.group = text
            elif self.child and self.lessons:
                self.lessons[-1][2].append((self.child, text))
            self.heading = None
        if tag == "section":
            self.section = None
        if tag == "details":
            self.child = None


def _sidebar(fragment: str) -> str:
    headings = _Headings()
    headings.feed(fragment)
    headings.close()
    if not headings.group or len(headings.lessons) != 8:
        raise ValueError("Esperada seção administrativa com oito aulas")

    def link(identifier: str, title: str) -> str:
        return (f'<a class="nav-link" href="#{escape(identifier, quote=True)}" '
                f'aria-controls="{escape(identifier, quote=True)}" '
                f'aria-expanded="false">{escape(title)}</a>')

    rows = []
    for identifier, title, children in headings.lessons:
        rows.append(f'<details class="nav-topic" data-topic="{escape(identifier, quote=True)}">'
                    f'<summary>{link(identifier, title)}</summary><div class="nav-children">'
                    + "".join(link(child, label) for child, label in children)
                    + "</div></details>")
    return ('<div class="nav-group section-group"><h3>' + escape(headings.group)
            + "</h3>" + "".join(rows) + "</div>")


def _insert(document: str, begin: str, end: str, body: str, closing: str) -> str:
    block = begin + "\n" + body.strip() + "\n" + end
    if begin in document or end in document:
        if document.count(begin) != 1 or document.count(end) != 1:
            raise ValueError("Marcadores administrativos ausentes ou duplicados")
        pattern = re.escape(begin) + r".*?" + re.escape(end)
        updated, count = re.subn(pattern, lambda _: block, document, count=1, flags=re.S)
        if count != 1:
            raise ValueError("Ordem dos marcadores administrativos inválida")
        return updated
    if document.count(closing) != 1:
        raise ValueError("Estrutura do guia inesperada; atualização cancelada")
    return document.replace(closing, block + "\n" + closing, 1)


def enhance(document: str) -> str:
    """Atualiza apenas blocos administrativos; não lê manifests nem código Rust."""
    fragment = FRAGMENT.read_text(encoding="utf-8")
    sidebar = _sidebar(fragment)
    if CONTENT_BEGIN not in document and re.search(r'\bid=["\']admin-web-', document):
        raise ValueError("IDs administrativos existentes sem marcadores; preservar para revisão")
    document = _insert(document, CONTENT_BEGIN, CONTENT_END, fragment, "</main>")
    return _insert(document, NAV_BEGIN, NAV_END, sidebar, "</nav>")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True, help="HTML existente a atualizar")
    args = parser.parse_args()
    if args.html.is_symlink() or not args.html.is_file():
        parser.error("informe um arquivo HTML existente, regular e sem symlink")
    original = args.html.read_text(encoding="utf-8")
    updated = enhance(original)
    if updated == original:
        print("Seção administrativa já atualizada; arquivo preservado.")
        return
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=args.html.parent,
                                         prefix=".xmqr-guide-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(args.html.stat().st_mode)
        os.replace(temporary, args.html)
        print("Seção administrativa e sidebar atualizadas sem regenerar o snapshot histórico.")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
