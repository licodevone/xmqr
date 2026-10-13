#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create private E01 credentials, never emit secrets or start a listener."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import secrets
import ssl
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    result = subprocess.run(args, capture_output=True, timeout=45, **kwargs)
    if result.returncode:
        # Tool stderr can contain file contents: deliberately do not forward it.
        raise RuntimeError("private lab prerequisite/operation failed")
    return result.stdout


def prepare(root, endpoint, port, openssl):
    root = root.resolve(strict=True)
    if root.is_relative_to(REPO) or not 1024 <= port <= 65535:
        raise ValueError("private directory/port invalid")
    endpoint = str(ipaddress.IPv4Address(endpoint))
    certs = root / "certs"
    if certs.exists() or (root / "firmware-config.json").exists():
        raise ValueError("refusing to overwrite private lab")
    wifi = json.loads((root / "wifi-config.json").read_text(encoding="utf-8-sig"))
    password_path = root / wifi["password_file"]
    if password_path.resolve().parent != root:
        raise ValueError("Wi-Fi password path outside private directory")
    wifi_password = password_path.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if not wifi_password or any(c in wifi_password for c in "\r\n\0"):
        raise ValueError("Wi-Fi password invalid")
    mqtt_password = secrets.token_urlsafe(32)
    linux_repo = "/mnt/" + REPO.drive[0].lower() + REPO.as_posix()[2:]
    helper = (
        "import sys;from pathlib import Path;sys.path.insert(0,'scripts');"
        "import benchmark_fanout as f;f.PASSWORD=sys.stdin.buffer.read();"
        "print(f.fixture_hash(Path('target/release/mqtt-admin').resolve()))"
    )
    phc = run(["wsl", "-d", "Ubuntu-26.04", "--cd", linux_repo,
               "--", "python3", "-c", helper], input=mqtt_password.encode()).decode().strip()
    if not phc.startswith("$argon2id$v=19$m=19456,t=2,p=1$"):
        raise RuntimeError("unexpected admin hash parameters")
    certs.mkdir(mode=0o700)
    run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
         "-days", "5", "-subj", "/CN=XMQR E01 temporary CA",
         "-keyout", str(certs / "ca.key"), "-out", str(certs / "ca.crt"),
         "-addext", "basicConstraints=critical,CA:TRUE",
         "-addext", "keyUsage=critical,keyCertSign,cRLSign"])
    for name, purpose in [("server", "serverAuth"), ("board", "clientAuth")]:
        run([openssl, "req", "-newkey", "rsa:2048", "-nodes", "-sha256",
             "-subj", f"/CN=XMQR E01 {name}", "-keyout", str(certs / f"{name}.key"),
             "-out", str(certs / f"{name}.csr")])
        ext = "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\n"
        ext += f"extendedKeyUsage={purpose}\n"
        if name == "server":
            ext += f"subjectAltName=IP:{endpoint}\n"
        extension_path = certs / f"{name}.ext"
        extension_path.write_text(ext, encoding="ascii")
        run([openssl, "x509", "-req", "-in", str(certs / f"{name}.csr"),
             "-CA", str(certs / "ca.crt"), "-CAkey", str(certs / "ca.key"),
             "-set_serial", str(secrets.randbits(128)), "-days", "5", "-sha256",
             "-extfile", str(extension_path), "-out", str(certs / f"{name}.crt")])
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
        (certs / "board.crt").read_text(encoding="ascii"))).hexdigest()
    (certs / "users.toml").write_text(
        '[[users]]\nusername="e01-board"\n'
        f'cert_sha256="sha256:{fingerprint}"\npassword_hash="{phc}"\n', encoding="ascii")
    (certs / "acl.toml").write_text(
        '[[rules]]\nusername="e01-board"\npublish=["e01/board/bytes"]\n'
        'subscribe=["e01/board/bytes"]\n', encoding="ascii")
    config = dict(ssid=wifi["ssid"], wifi_password=wifi_password,
                  mqtt_url=f"mqtts://{endpoint}:{port}", mqtt_username="e01-board",
                  mqtt_password=mqtt_password)
    (root / "firmware-config.json").write_text(json.dumps(config), encoding="utf-8")
    print("E01_PRIVATE_LAB_READY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", required=True, type=Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--port", type=int, default=28883)
    parser.add_argument("--openssl", default="C:/Program Files/Git/usr/bin/openssl.exe")
    args = parser.parse_args()
    try:
        prepare(args.private_dir, args.endpoint, args.port, args.openssl)
    except Exception:
        print("E01_PRIVATE_LAB_FAILED (details suppressed to protect credentials)", file=sys.stderr)
        sys.exit(1)
