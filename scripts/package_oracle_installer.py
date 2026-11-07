#!/usr/bin/env python3
"""Create an allowlisted, deterministic installer archive; never packages host credentials."""
import argparse
import hashlib
import json
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUTS = {
    "install_oracle_x86.sh": "scripts/install_oracle_x86.sh",
    "verify_oracle_installer.py": "scripts/verify_oracle_installer.py",
    "README.md": "packaging/oracle-installer/README.md",
    "RELEASE_NOTES.md": "docs/releases/oracle-installer-0.1.0-rc.1.md",
}
PACKAGES = [
    {"repository": "licodevone/xmqr", "tag": "v0.43.0",
     "file": "xmqr-broker_0.43.0-1_amd64.deb",
     "sha256": "c2341ab3a341b1854e85ebb2f0bec9535968374b226a12a60cee58aa7cef3d4e"},
    {"repository": "licodevone/xmqr-client", "tag": "v0.43.0",
     "file": "xmqr-client_0.43.0-1_amd64.deb",
     "sha256": "e4d09cec660a0dba20790181727b17c44040913425a3340d3838e45113241f76"},
    {"repository": "licodevone/xmqr-admin", "tag": "v0.11.0",
     "file": "xmqr-admin_0.11.0-1_amd64.deb",
     "sha256": "fe03ffc858e7583e7d8ce6808b4f56495c688beb69d47870db7fe0c1b8b55469"},
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--source-revision")
    parser.add_argument("--evidence", type=pathlib.Path)
    args = parser.parse_args()
    if args.source_revision and not re.fullmatch(r"[0-9a-f]{40}", args.source_revision):
        parser.error("--source-revision exige SHA Git completo")
    files = {name: (ROOT / source).read_text(encoding="utf-8").replace("\r\n", "\n").encode()
             for name, source in INPUTS.items()}
    version = re.search(rb"^INSTALLER_VERSION='([^']+)'$", files["install_oracle_x86.sh"], re.M)[1].decode()
    if args.evidence:
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        if evidence.get("source_revision") != args.source_revision or evidence.get("status") != "PASS":
            parser.error("Evidencia deve ser PASS da mesma revisao")
        files["EVIDENCE.json"] = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    manifest = {"schema": 1, "product": "XMQR Oracle Installer", "version": version,
                "source_revision": args.source_revision,
                "source_kind": "git-commit" if args.source_revision else "working-tree",
                "validation": {"status": "PASS" if args.evidence else "NOT_RUN",
                               "evidence_file": "EVIDENCE.json" if args.evidence else None},
                "runtime": "Ubuntu 26.04 amd64 with systemd", "packages": PACKAGES,
                "files": {name: digest(data) for name, data in sorted(files.items())}}
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    files["SHA256SUMS"] = "".join(f"{digest(data)}  {name}\n"
                                    for name, data in sorted(files.items())).encode()
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f"xmqr-oracle-installer-{version}.zip"
    if archive.exists():
        parser.error(f"Arquivo ja existe; nao sobrescrever candidato: {archive}")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as stream:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if name.endswith((".sh", ".py")) else 0o100644) << 16
            stream.writestr(info, data)
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{digest(archive.read_bytes())}  {archive.name}\n", encoding="utf-8")
    print(archive)
    print(checksum)


if __name__ == "__main__":
    main()
