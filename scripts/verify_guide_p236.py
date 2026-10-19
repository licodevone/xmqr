#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P236: structural regression checks for the leaf-navigation transformation."""
import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from guide_leaf_navigation import NavigationParser, enhance


BODY = '<main><section id="leaf"><details class="topic"><summary><h2>Aula sem filhos</h2></summary><div class="topic-body">conteúdo histórico &amp; código &lt;T&gt;</div></details></section><section id="parent"><details class="topic"><summary><h2>Aula com filhos</h2></summary><details id="child" class="subtopic"><summary><h3>Passo</h3></summary><p>Não alterar.</p></details></details></section></main>'
SOURCE = '<!doctype html><html><head><title>Curso</title></head><body><nav id="course-nav"><details class="nav-topic" data-topic="leaf"><summary><a class="nav-link" href="#leaf" aria-controls="leaf" aria-expanded="false">Aula sem filhos</a></summary><div class="nav-children"> <!-- sem filhos --> </div></details><details class="nav-topic" data-topic="parent"><summary><a class="nav-link" href="#parent" aria-controls="parent" aria-expanded="true">Aula com filhos</a></summary><div class="nav-children"><a class="nav-link" href="#child" aria-expanded="false">Passo</a></div></details></nav>' + BODY + '</body></html>'


class LeafNavigationTests(unittest.TestCase):
    def test_leaf_becomes_direct_link_while_parent_and_lesson_body_are_preserved(self):
        updated = enhance(SOURCE)
        self.assertIn(BODY, updated)
        nav = re.search(r'<nav\b.*?</nav>', updated, re.S).group(0)
        parser = NavigationParser(nav)
        parser.feed(nav)
        leaves = [node for node in parser.nodes if node.tag == 'a' and node.has_class('nav-leaf')]
        self.assertEqual(len(leaves), 2)
        self.assertTrue(all('aria-expanded' not in dict(node.attrs) for node in leaves))
        parents = [node for node in parser.nodes if node.tag == 'details']
        self.assertEqual(len(parents), 1)
        self.assertEqual(dict(parents[0].attrs)['data-topic'], 'parent')
        self.assertIn('aria-expanded="true">Aula com filhos', nav)

    def test_repeated_enhancement_is_identical_and_extensions_are_not_duplicated(self):
        first = enhance(SOURCE)
        self.assertEqual(first, enhance(first))
        self.assertEqual(first.count('id="p236-leaf-navigation-style"'), 1)
        self.assertEqual(first.count('id="p236-leaf-navigation-script"'), 1)

    def test_nested_parent_control_keeps_expansion_while_plain_children_do_not(self):
        nested = SOURCE.replace('<div class="nav-children"><a', '<div class="nav-children"><details class="nav-topic"><summary><a class="nav-link" href="#parent" aria-expanded="true">Nested parent</a></summary><div class="nav-children"><a').replace('>Passo</a></div>', '>Passo</a></div></details></div>')
        result = enhance(nested)
        self.assertIn('aria-expanded="true">Nested parent</a>', result)

    def test_entities_classes_and_unrelated_link_attributes_are_preserved(self):
        source = SOURCE.replace('class="nav-link" href="#leaf"', 'class="nav-link extra" data-note="a&amp;b" href="#leaf"')
        result = enhance(source)
        self.assertIn('class="nav-link extra nav-leaf" data-note="a&amp;b" href="#leaf"', result)

    def test_missing_navigation_or_document_boundaries_is_an_explicit_error(self):
        for invalid in ['<html><head></head><body></body></html>', SOURCE.replace('</head>', ''), SOURCE.replace('</body>', '')]:
            with self.assertRaises(ValueError):
                enhance(invalid)


class Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _, attrs):
        self.ids.extend(value for name, value in attrs if name == 'id')


def audit_file(path):
    document = path.read_text(encoding='utf-8')
    assert enhance(document) == document, 'final HTML has not received leaf enhancement'
    ids = Ids()
    ids.feed(document)
    duplicates = [name for name, count in Counter(ids.ids).items() if count > 1]
    assert not duplicates, 'duplicate HTML identifiers'
    nav = re.search(r'<nav\b[^>]*\bid="course-nav"[^>]*>.*?</nav>', document, re.S).group(0)
    parser = NavigationParser(nav)
    parser.feed(nav)
    leaves, parents = 0, 0
    for node in parser.nodes:
        if node.tag == 'a' and node.has_class('nav-link'):
            anchor = dict(node.attrs)
            assert anchor.get('href', '').startswith('#')
            assert anchor['href'][1:] in ids.ids, 'sidebar target not found'
            if node.has_class('nav-leaf'):
                leaves += 1
                assert 'aria-expanded' not in anchor
                assert not (node.parent and node.parent.tag == 'summary'), 'leaf still inside summary'
        if node.tag == 'details' and node.has_class('nav-topic'):
            parents += 1
            children = next(child for child in node.children if child.has_class('nav-children'))
            assert source_has_link(nav[children.opening_end:children.closing_start]), 'empty expandable sidebar item'
    assert leaves and parents, 'fixture should exercise both direct and parent links'
    print(f'P236 HTML structure PASS: {leaves} direct links, {parents} expandable parents, unique IDs and valid targets')


def source_has_link(source):
    return bool(re.search(r'<a\b', source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LeafNavigationTests))
    if not result.wasSuccessful():
        return 1
    if args.html:
        audit_file(args.html)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
