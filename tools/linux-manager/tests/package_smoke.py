#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Inspect a built .deb without installing it or modifying system directories."""
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def main():
    package = Path(sys.argv[1]).resolve()
    payload = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(package)])
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        members = archive.getmembers()
        root = next(m for m in members if m.name in ('.', './'))
        assert root.mode == 0o755, oct(root.mode)
        for member in members:
            assert member.uid == member.gid == 0, member.name
            assert not member.mode & 0o022, member.name
            assert member.isfile() or member.isdir(), member.name
            if member.isdir():
                assert member.mode == 0o755, (member.name, oct(member.mode))
            assert '..' not in Path(member.name).parts and not member.name.startswith('/'), member.name
            assert '/systemd/' not in member.name, member.name
        launcher = next(m for m in members if m.name.endswith('/usr/bin/xmqr-manager'))
        assert launcher.mode == 0o755
    with tempfile.TemporaryDirectory(prefix='xmqr-manager-package-smoke-') as temp:
        subprocess.run(['dpkg-deb', '--extract', str(package), temp], check=True)
        directory = Path(temp)
        program = directory / 'usr/lib/xmqr-manager/xmqr_manager.py'
        result = subprocess.check_output(['/usr/bin/python3', '-I', str(program), '--version'], text=True)
        assert result.strip() == 'XMQR Manager Ubuntu 0.1.0'
        subprocess.run(['sh', '-n', str(directory / 'usr/bin/xmqr-manager')], check=True)
        subprocess.run(['desktop-file-validate', str(directory / 'usr/share/applications/xmqr-manager.desktop'),
                        str(directory / 'etc/xdg/autostart/xmqr-manager.desktop')], check=True)
    print('Package PASS: root mode, ownership, immutable code, executable launcher, isolated imports, desktop entries, no service units')


if __name__ == '__main__':
    main()
