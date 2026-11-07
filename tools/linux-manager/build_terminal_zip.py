#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Create the allowlisted terminal companion ZIP; never includes runtime files."""
import argparse
import ast
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    version = next(ast.literal_eval(n.value) for n in ast.parse((ROOT/'terminal.py').read_text()).body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'VERSION' for t in n.targets))
    inputs = {'terminal.py': ROOT/'terminal.py', 'backend.py': ROOT/'backend.py',
              'README.md': REPO/'docs/linux-terminal-manager.md', 'LICENSE': REPO/'LICENSE'}
    files = {name: path.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')
             for name, path in inputs.items()}
    files['xmqr-manager-terminal'] = (b'#!/bin/sh\nexec /usr/bin/python3 -I '
        b'/usr/local/lib/xmqr-manager-terminal/terminal.py "$@"\n')
    files['SHA256SUMS'] = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n'
                                for name, data in sorted(files.items())).encode('ascii')
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output/f'xmqr-manager-terminal-{version}.zip'
    checksum = archive.with_suffix('.zip.sha256')
    if archive.exists() or checksum.exists():
        parser.error('Artefato ja existe. Escolha outra pasta; nao sobrescrever.')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as stream:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if name == 'xmqr-manager-terminal' else 0o100644) << 16
            stream.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f'{digest}  {archive.name}\n', encoding='ascii', newline='\n')
    print(archive.resolve())
    print(checksum.resolve())


if __name__ == '__main__':
    main()
