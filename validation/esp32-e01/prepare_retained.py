#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""New private lab case with distinct observer identity; originals remain intact."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import ssl
import sys
import tomllib
from urllib.parse import urlsplit
import uuid

from prepare_lab import run
from sync_wifi import REPO, private_file, read_bounded


def prepare(root, openssl):
    root = root.resolve(strict=True)
    if root.is_relative_to(REPO) or (root / "p84-observer.json").exists():
        raise ValueError("private new lab case required")
    config = json.loads(read_bounded(private_file(root, "firmware-config.json")))
    url = urlsplit(config["mqtt_url"])
    if config["mqtt_username"] != "e01-board" or url.scheme != "mqtts" or not url.hostname or url.username:
        raise ValueError("unexpected lab identity")
    certs = (root / "certs").resolve(strict=True)
    if certs.parent != root or certs.is_relative_to(REPO):
        raise ValueError("private certificates required")
    users = read_bounded(private_file(certs, "users.toml"))
    parsed = tomllib.loads(users.decode("utf-8"))
    if len(parsed.get("users", [])) != 1 or parsed["users"][0]["username"] != "e01-board":
        raise ValueError("unexpected lab users")
    password = secrets.token_urlsafe(32)
    linux_repo = "/mnt/" + REPO.drive[0].lower() + REPO.as_posix()[2:]
    helper = (
        "import sys;from pathlib import Path;sys.path.insert(0,'scripts');"
        "import benchmark_fanout as f;f.PASSWORD=sys.stdin.buffer.read();"
        "print(f.fixture_hash(Path('target/release/mqtt-admin').resolve()))")
    phc = run(["wsl", "-d", "Ubuntu-26.04", "--cd", linux_repo, "--", "python3", "-c", helper],
              input=password.encode()).decode().strip()
    if not re.fullmatch(r"\$argon2id\$v=19\$m=19456,t=2,p=1\$[A-Za-z0-9+/]+\$[A-Za-z0-9+/]+", phc):
        raise ValueError("invalid lab hash")
    case = root / ("p84-case-" + uuid.uuid4().hex)
    case.mkdir(mode=0o700)
    broker, observer = case / "broker", case / "observer"
    broker.mkdir(mode=0o700)
    observer.mkdir(mode=0o700)
    for name in ("ca.crt", "server.crt", "server.key"):
        with (broker / name).open("xb") as stream:
            stream.write(read_bounded(private_file(certs, name)))
    with (observer / "ca.crt").open("xb") as stream:
        stream.write(read_bounded(private_file(certs, "ca.crt")))
    run([openssl, "req", "-newkey", "rsa:2048", "-nodes", "-sha256", "-subj",
         "/CN=XMQR E01 retained observer", "-keyout", str(observer / "observer.key"),
         "-out", str(observer / "observer.csr")])
    with (observer / "observer.ext").open("x", encoding="ascii") as stream:
        stream.write("basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=clientAuth\n")
    run([openssl, "x509", "-req", "-in", str(observer / "observer.csr"), "-CA",
         str(private_file(certs, "ca.crt")), "-CAkey", str(private_file(certs, "ca.key")),
         "-set_serial", str(secrets.randbits(128)), "-days", "3", "-sha256", "-extfile",
         str(observer / "observer.ext"), "-out", str(observer / "observer.crt")])
    run([openssl, "verify", "-CAfile", str(certs / "ca.crt"), str(observer / "observer.crt")])
    context = ssl.create_default_context(cafile=str(observer / "ca.crt"))
    context.load_cert_chain(observer / "observer.crt", observer / "observer.key")
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
        (observer / "observer.crt").read_text(encoding="ascii"))).hexdigest()
    with (broker / "users.toml").open("xb") as stream:
        stream.write(users + (f'\n[[users]]\nusername="e01-observer"\ncert_sha256="sha256:{fingerprint}"\npassword_hash="{phc}"\n').encode())
    with (broker / "acl.toml").open("x", encoding="ascii") as stream:
        stream.write('[[rules]]\nusername="e01-board"\npublish=["e01/board/bytes","e01/board/retained"]\nsubscribe=["e01/board/bytes","e01/board/control"]\n'
                     '[[rules]]\nusername="e01-observer"\npublish=["e01/board/control"]\nsubscribe=["e01/board/bytes","e01/board/retained"]\n')
    with (root / "p84-observer.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(case_directory=case.name, username="e01-observer", password=password), stream)


def load(root):
    root = root.resolve(strict=True)
    if root.is_relative_to(REPO):
        raise ValueError("private directory required")
    config = json.loads(read_bounded(private_file(root, "p84-observer.json")))
    name = config["case_directory"]
    if not isinstance(name, str) or not re.fullmatch(r"p84-case-[a-f0-9]{32}", name):
        raise ValueError("invalid case directory")
    case = (root / name).resolve(strict=True)
    if case.parent != root or case.is_relative_to(REPO):
        raise ValueError("case outside private directory")
    if config["username"] != "e01-observer" or not isinstance(config["password"], str) or not 32 <= len(config["password"]) <= 64:
        raise ValueError("invalid observer identity")
    for directory in ("broker", "observer"):
        resolved = (case / directory).resolve(strict=True)
        if resolved.parent != case or not resolved.is_dir():
            raise ValueError("case directory escaped")
    return case, config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", required=True, type=Path)
    parser.add_argument("--openssl", default="C:/Program Files/Git/usr/bin/openssl.exe")
    args = parser.parse_args()
    try:
        prepare(args.private_dir, args.openssl)
        print("E01_RETAINED_PRIVATE_CASE_READY")
    except Exception:
        print("E01_RETAINED_PRIVATE_CASE_FAILED (details suppressed)", file=sys.stderr)
        sys.exit(1)
