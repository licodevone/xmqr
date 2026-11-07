#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package a terminal frontend with the exact previously published helper and notices."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
ZIP_SHA = '481bbbdb38f268c475e44013fc5f60476296be6a5f95c0585b734322844a60e5'
EXE_SHA = '3c4e11e1ae9e67e7a01d632d84d6dbf69addda4a85e2202ae0bc12c1e7c5943e'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--helper-zip', type=Path,
        default=REPO/'dist/releases/p256-verify/windows/xmqr-manager-0.1.1-windows-x64.zip')
    args = parser.parse_args()
    if sha(args.helper_zip.read_bytes()) != ZIP_SHA:
        parser.error('ZIP helper difere da distribuicao oficial fixa.')
    files = {}
    with zipfile.ZipFile(args.helper_zip) as source:
        for entry in source.infolist():
            if entry.is_dir():
                continue
            name = entry.filename
            if name.startswith('/') or '..' in PurePosixPath(name).parts or '\\' in name:
                parser.error('Caminho inseguro no pacote helper.')
            if name not in {'xmqr-manager.exe', 'LICENSE', 'README.md'} and not name.startswith('notices/'):
                parser.error('Arquivo inesperado no pacote helper.')
            files['helper/'+name] = source.read(entry)
    if sha(files['helper/xmqr-manager.exe']) != EXE_SHA:
        parser.error('Executavel helper diverge do SHA oficial.')
    for name, path in {'XMQR-Terminal.ps1': ROOT/'XMQR-Terminal.ps1',
                       'README.md': REPO/'docs/windows-terminal-manager.md',
                       'LICENSE': REPO/'LICENSE'}.items():
        files[name] = path.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')
    files['PROVENANCE.json'] = (json.dumps({'frontend_version':'0.1.0-rc.1',
        'frontend_source':'working-tree', 'helper_tag':'manager-windows-v0.1.1',
        'helper_commit':'2aa4279d9b10ec474d65ca4afe262f03e61c4dc6',
        'helper_original_zip_sha256':ZIP_SHA, 'helper_executable_sha256':EXE_SHA,
        'helper_rebuilt':False},indent=2,sort_keys=True)+'\n').encode()
    files['SHA256SUMS'] = ''.join(f'{sha(data)}  {name}\n' for name,data in sorted(files.items())).encode()
    args.output.mkdir(parents=True,exist_ok=True)
    archive=args.output/'xmqr-manager-terminal-windows-0.1.0-rc.1.zip'
    checksum=archive.with_suffix('.zip.sha256')
    if archive.exists() or checksum.exists():
        parser.error('Artefato ja existe; nao sobrescrever.')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as stream:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)); info.create_system=3
            info.external_attr=0o100644 << 16
            stream.writestr(info,data)
    checksum.write_text(f'{sha(archive.read_bytes())}  {archive.name}\n',encoding='ascii',newline='\n')
    print(archive.resolve())
    print(checksum.resolve())


if __name__=='__main__':
    main()
