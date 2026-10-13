#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare an exclusive lab case; do not overwrite earlier lab credentials."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import secrets
import ssl
import sys
import uuid
from urllib.parse import urlsplit

from prepare_lab import run
from prepare_retained import load as load_retained
from sync_wifi import REPO, private_file, read_bounded

MOSQUITTO = "eclipse-mosquitto:2.0.22@sha256:199ea8ef2e35ec2b1b37e59cfd1dbae538ed4dfa4a2251a121a52215a6248a21"


def phc(password):
    linux_repo = "/mnt/" + REPO.drive[0].lower() + REPO.as_posix()[2:]
    helper = ("import sys;from pathlib import Path;sys.path.insert(0,'scripts');"
              "import benchmark_fanout as f;f.PASSWORD=sys.stdin.buffer.read();"
              "print(f.fixture_hash(Path('target/release/mqtt-admin').resolve()))")
    value = run(["wsl", "-d", "Ubuntu-26.04", "--cd", linux_repo, "--", "python3", "-c", helper],
                input=password.encode()).decode().strip()
    if not re.fullmatch(r"\$argon2id\$v=19\$m=19456,t=2,p=1\$[A-Za-z0-9+/]+\$[A-Za-z0-9+/]+", value):
        raise ValueError("invalid lab hash")
    return value


def write(path, value):
    with path.open("xb") as stream:
        stream.write(value if isinstance(value, bytes) else value.encode())


def leaf(directory, prefix, ca, purpose, sans, openssl):
    run([openssl, "req", "-newkey", "rsa:2048", "-nodes", "-sha256", "-subj",
         f"/CN=XMQR E01 {prefix}", "-keyout", str(directory / f"{prefix}.key"),
         "-out", str(directory / f"{prefix}.csr")])
    ext = "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\n"
    ext += f"extendedKeyUsage={purpose}\n"
    if sans:
        ext += f"subjectAltName={sans}\n"
    write(directory / f"{prefix}.ext", ext)
    run([openssl, "x509", "-req", "-in", str(directory / f"{prefix}.csr"), "-CA",
         str(private_file(ca, "ca.crt")), "-CAkey", str(private_file(ca, "ca.key")),
         "-set_serial", str(secrets.randbits(128)), "-days", "3", "-sha256", "-extfile",
         str(directory / f"{prefix}.ext"), "-out", str(directory / f"{prefix}.crt")])


def prepare(root, openssl):
    root = root.resolve(strict=True)
    if root.is_relative_to(REPO) or (root / "p85-case.json").exists():
        raise ValueError("new private case required")
    previous, observer = load_retained(root)
    config = json.loads(read_bounded(private_file(root, "firmware-config.json")))
    url = urlsplit(config["mqtt_url"])
    address = str(ipaddress.IPv4Address(url.hostname))
    if url.scheme != "mqtts" or url.username or not 1024 <= url.port <= 65535:
        raise ValueError("unexpected lab endpoint")
    certs = (root / "certs").resolve(strict=True)
    if certs.parent != root:
        raise ValueError("private certificates escaped")
    case = root / ("p85-case-" + uuid.uuid4().hex)
    case.mkdir(mode=0o700)
    for name in ("normal", "san", "observer", "external"):
        (case / name).mkdir(mode=0o700)
    for name in ("ca.crt", "observer.crt", "observer.key"):
        write(case / "observer" / name, read_bounded(private_file(previous / "observer", name)))
    password = secrets.token_urlsafe(32)
    password_hash = phc(password)
    external = case / "external"
    write(external / "ca.crt", read_bounded(private_file(certs, "ca.crt")))
    leaf(external, "external", certs, "clientAuth", None, openssl)
    # Alias filenames for the existing bounded Peer, identity remains external.
    for suffix in ("crt", "key"):
        write(external / f"observer.{suffix}", (external / f"external.{suffix}").read_bytes())
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert((external / "external.crt").read_text())).hexdigest()
    users = read_bounded(private_file(previous / "broker", "users.toml"))
    users += (f'\n[[users]]\nusername="e01-external"\ncert_sha256="sha256:{fingerprint}"\npassword_hash="{password_hash}"\n').encode()
    acl = ('[[rules]]\nusername="e01-board"\npublish=["e01/board/bytes","e01/board/retained","e01/board/will"]\nsubscribe=["e01/board/bytes","e01/board/control"]\n'
           '[[rules]]\nusername="e01-observer"\npublish=["e01/board/control"]\nsubscribe=["e01/board/bytes","e01/board/retained","e01/board/will"]\n'
           '[[rules]]\nusername="e01-external"\npublish=["e01/board/bytes"]\nsubscribe=["e01/board/retained"]\n')
    # External principal publishes bytes for the controlled DUP QoS1 injection.
    for name, ip in (("normal", address), ("san", "192.0.2.1")):
        directory = case / name
        write(directory / "ca.crt", read_bounded(private_file(certs, "ca.crt")))
        write(directory / "users.toml", users)
        write(directory / "acl.toml", acl)
        leaf(directory, "server", certs, "serverAuth", f"IP:{ip},DNS:e01-broker", openssl)
    run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", "3",
         "-subj", "/CN=XMQR E01 untrusted CA", "-keyout", str(case / "bad-ca.key"),
         "-out", str(case / "bad-ca.crt"), "-addext", "basicConstraints=critical,CA:TRUE"])
    for program in ("mosquitto_pub", "mosquitto_sub"):
        options = (f'-u e01-external\n-P {password}\n--cafile /run/test/ca.crt\n'
                   '--cert /run/test/external.crt\n--key /run/test/external.key\n')
        write(external / program, options)
    write(external / "payload-12.bin", bytes([12]) + bytes(i % 251 for i in range(1, 1024)))
    write(root / "p85-case.json", json.dumps(dict(case_directory=case.name, username=observer["username"],
                                                 password=observer["password"], external_password=password)))


def load(root):
    root = root.resolve(strict=True)
    if root.is_relative_to(REPO):
        raise ValueError("private directory required")
    config = json.loads(read_bounded(private_file(root, "p85-case.json")))
    name = config["case_directory"]
    if not isinstance(name, str) or not re.fullmatch(r"p85-case-[a-f0-9]{32}", name):
        raise ValueError("invalid case directory")
    case = (root / name).resolve(strict=True)
    if case.parent != root:
        raise ValueError("private case escaped")
    for directory in ("normal", "san", "observer", "external"):
        if (case / directory).resolve(strict=True).parent != case:
            raise ValueError("private profile escaped")
    if config["username"] != "e01-observer" or not 32 <= len(config["password"]) <= 64:
        raise ValueError("invalid observer")
    return case, config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.private_dir, "C:/Program Files/Git/usr/bin/openssl.exe")
        print("P85_PRIVATE_CASE_READY")
    except Exception:
        print("P85_PRIVATE_CASE_FAILED (details suppressed)", file=sys.stderr)
        sys.exit(1)
