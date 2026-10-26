#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Build the independent all-architecture Ubuntu desktop package; never install."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

VERSION = '0.1.0'


def main():
    os.umask(0o022)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist/linux-manager'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f'xmqr-manager_{VERSION}-1_all.deb'
    if destination.exists():
        parser.error('Escolha uma pasta nova; artefatos existentes não são sobrescritos.')
    with tempfile.TemporaryDirectory(prefix='xmqr-manager-deb-') as temp:
        stage = Path(temp)
        stage.chmod(0o755)
        def put(source, target, mode=0o644):
            target = stage / target
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            target.chmod(mode)
        for file in ['backend.py', 'xmqr_manager.py']:
            put(root / file, f'usr/lib/xmqr-manager/{file}')
        put(root / 'xmqr-manager', 'usr/bin/xmqr-manager', 0o755)
        put(root / 'xmqr-manager.desktop', 'usr/share/applications/xmqr-manager.desktop')
        put(root / 'xmqr-manager-autostart.desktop', 'etc/xdg/autostart/xmqr-manager.desktop')
        put(root.parent / 'windows-manager/assets/manager-x.png',
            'usr/share/pixmaps/xmqr-manager.png')
        put(root / 'README.md', 'usr/share/doc/xmqr-manager/README.md')
        put(root.parents[1] / 'LICENSE', 'usr/share/doc/xmqr-manager/copyright')
        for file in (root / 'examples').glob('*.json'):
            put(file, f'usr/share/doc/xmqr-manager/examples/{file.name}')
        registry = stage / 'etc/xmqr-manager/components.d'
        registry.mkdir(parents=True)
        registry.chmod(0o755)
        control = stage / 'DEBIAN'
        control.mkdir()
        (control / 'control').write_text(
            f'Package: xmqr-manager\nVersion: {VERSION}-1\nArchitecture: all\n'
            'Maintainer: XMQR maintainers <xmqr@localhost>\nSection: admin\nPriority: optional\n'
            'Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, '
            'systemd, pkexec, gvfs-backends, nautilus, gnome-text-editor\n'
            'Recommends: gir1.2-ayatanaappindicator3-0.1\n'
            'Description: Local desktop manager for XMQR on Ubuntu\n'
            ' Manage installed XMQR services through systemd/polkit and browse protected\n'
            ' configuration through GVfs. Does not install or configure XMQR services.\n', encoding='utf-8')
        (control / 'conffiles').write_text('/etc/xdg/autostart/xmqr-manager.desktop\n')
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(destination)], check=True)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.deb.sha256').write_text(f'{digest}  {destination.name}\n')
    print(destination)


if __name__ == '__main__':
    main()
