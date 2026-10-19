#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P236: atualiza a operação e a aparência sem refazer fontes históricas."""
import argparse
import os
from pathlib import Path
import tempfile

from guide_admin_panel import enhance as admin_panel
from guide_leaf_navigation import enhance as leaf_navigation
from guide_theme import enhance as theme


def enhance(document):
    # As extensões preservam blocos independentes. Normalizar sua ordem também
    # quando o HTML já continha apenas algumas delas, sem refazer o curso.
    for _ in range(4):
        updated = leaf_navigation(theme(admin_panel(document)))
        if updated == document:
            return updated
        document = updated
    raise ValueError('As extensões do guia não convergiram para uma ordem estável.')


def update(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('O destino deve ser um arquivo HTML existente e real.')
    original = path.read_bytes()
    bom = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
    document = original.decode('utf-8-sig')
    result = enhance(document)
    if enhance(result) != result:
        raise ValueError('As extensões não passaram na verificação de idempotência.')
    encoded = bom + result.encode('utf-8')
    if encoded == original:
        return False
    mode = path.stat().st_mode
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.code-guide-', suffix='.tmp', delete=False) as target:
            temporary = Path(target.name)
            target.write(encoded)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, required=True)
    args = parser.parse_args()
    changed = update(args.html)
    print('Guia atualizado.' if changed else 'O guia já está atualizado.')


if __name__ == '__main__':
    main()
