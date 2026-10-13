#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Luis E. S. Pinheiro
"""P92: verify original notice bytes in .deb and existing Docker images.

No service is started. A test-owned, unstarted Docker container is copied and
removed. TAR is read in memory, never extracted to the workstation filesystem.
The expected notice collection must come from locked source, outside artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_LIMIT = 64 * 1024 * 1024
FILE_LIMIT = 4 * 1024 * 1024
CONTENT_LIMIT = 64 * 1024 * 1024
MEMBER_LIMIT = 20_000


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or "\0" in name:
        raise ValueError("unsafe notice path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("unsafe notice path")
    normalized = path.as_posix()
    if normalized == ".":
        return ""
    return normalized


def read_archive(data: bytes, prefix: str) -> dict[str, bytes]:
    if len(data) > ARCHIVE_LIMIT:
        raise ValueError("archive exceeds QA limit")
    prefix = safe_path(prefix).rstrip("/")
    content = {}
    read_bytes = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for count, member in enumerate(archive, 1):
            if count > MEMBER_LIMIT:
                raise ValueError("archive member count exceeds QA limit")
            path = safe_path(member.name)
            if path == prefix or not path.startswith(prefix + "/"):
                continue
            path = path[len(prefix) + 1:]
            if member.isdir():
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError("notice member is not a regular file")
            if path in content or not (0 <= member.size <= FILE_LIMIT):
                raise ValueError("duplicate or oversized notice file")
            read_bytes += member.size
            if read_bytes > CONTENT_LIMIT:
                raise ValueError("aggregate notice content exceeds QA limit")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("notice member unreadable")
            value = source.read(FILE_LIMIT + 1)
            if len(value) != member.size:
                raise ValueError("notice member length mismatch")
            content[path] = value
    return content


def expected_collection(manifest_path: Path) -> tuple[dict, dict[str, bytes]]:
    manifest_path = manifest_path.resolve(strict=True)
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 1 or not manifest.get("packages"):
        raise ValueError("invalid expected notice manifest")
    files = {}
    for package in manifest["packages"]:
        if not package.get("files"):
            raise ValueError("dependency has no expected original text")
        for file in package["files"]:
            relative = safe_path(file["path"])
            expected = root / relative
            if expected.is_symlink() or not expected.is_file():
                raise ValueError("expected notice is not a regular file")
            expected.resolve(strict=True).relative_to(root)
            if relative in files or not re.fullmatch(r"[a-f0-9]{64}", file["sha256"]):
                raise ValueError("invalid expected notice entry")
            if expected.stat().st_size > FILE_LIMIT:
                raise ValueError("expected notice exceeds QA limit")
            value = expected.read_bytes()
            if sha(value) != file["sha256"] or len(value) != file["size"]:
                raise ValueError("expected source notice hash/size mismatch")
            files[relative] = value
    return manifest, files


def verify_payload(content: dict[str, bytes], manifest: dict,
                   originals: dict[str, bytes], own_license: bytes, deb: bool) -> dict:
    canonical_mit = own_license.replace(b"\r\n", b"\n")
    packaged_mit = {}
    for name in (["LICENSE", "copyright"] if deb else ["LICENSE"]):
        value = content.get(name)
        if value is None or value.replace(b"\r\n", b"\n") != canonical_mit:
            raise ValueError("own MIT copyright/LICENSE differs from source")
        packaged_mit[name] = sha(value)
    raw_manifest = content.get("third-party/manifest.json")
    if raw_manifest is None or json.loads(raw_manifest) != manifest:
        raise ValueError("packaged notice manifest differs from locked source collection")
    expected = {"third-party/" + relative for relative in originals}
    actual = {path for path in content if path.startswith("third-party/")
              and path != "third-party/manifest.json"}
    if actual != expected:
        raise ValueError("missing or extra packaged original notice")
    for relative, value in originals.items():
        packaged = content["third-party/" + relative]
        if packaged != value or sha(packaged) != sha(value):
            raise ValueError("packaged original text SHA mismatch")
    return {"status": "PASS", "packages": len(manifest["packages"]),
            "original_texts": len(originals), "original_bytes": sum(map(len, originals.values())),
            "own_mit_source_raw_sha256": sha(own_license),
            "own_mit_packaged_raw_sha256": packaged_mit,
            "own_mit_canonical_lf_sha256": sha(canonical_mit),
            "own_mit_comparison": "CRLF-to-LF only; no changes to terms/copyright",
            "third_party_comparison": "strict original bytes; no EOL normalization",
            "expected_manifest_sha256": sha(json.dumps(manifest, sort_keys=True).encode())}


def command(arguments: list[str]) -> bytes:
    result = subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if result.returncode:
        # Only the tool's failure classification is printed, not raw binary text.
        raise RuntimeError("artifact read command failed")
    return result.stdout


def deb_payload(path: Path, distro: str, package: str) -> dict[str, bytes]:
    path = path.resolve(strict=True)
    if os.name == "nt":
        linux_path = command(["wsl.exe", "-d", distro, "--exec", "wslpath", "-a", str(path)]).decode().strip()
        raw = command(["wsl.exe", "-d", distro, "--exec", "dpkg-deb", "--fsys-tarfile", linux_path])
    else:
        raw = command(["dpkg-deb", "--fsys-tarfile", str(path)])
    return read_archive(raw, f"usr/share/doc/{package}")


def image_payload(image: str, path: str) -> tuple[dict[str, bytes], str]:
    image_id = command(["docker", "image", "inspect", "--format", "{{.Id}}", image]).decode().strip()
    name = "xmqr-p92-notices-" + uuid.uuid4().hex[:12]
    container = command(["docker", "create", "--pull", "never", "--name", name,
                         "--network", "none", "--read-only", "--entrypoint", "/bin/true", image_id]).decode().strip()
    if not re.fullmatch(r"[a-f0-9]{64}", container):
        raise RuntimeError("unexpected test container identity")
    try:
        raw = command(["docker", "cp", container + ":" + path, "-"])
        return read_archive(raw, PurePosixPath(path).name), image_id
    finally:
        command(["docker", "rm", "-v", container])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-notices", type=Path, required=True, help="source collected manifest.json")
    parser.add_argument("--client-notices", type=Path, required=True, help="source collected manifest.json")
    parser.add_argument("--broker-deb", type=Path, required=True)
    parser.add_argument("--client-deb", type=Path, required=True)
    parser.add_argument("--broker-image", required=True)
    parser.add_argument("--admin-image", required=True, help="legacy mqtt-admin image for this broker")
    parser.add_argument("--client-image", required=True)
    parser.add_argument("--distro", default="Ubuntu-26.04")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "dist"):
        parser.error("use a new output file within this repository's ignored dist")
    jobs = [
        ("broker-deb", "broker", lambda: (deb_payload(args.broker_deb, args.distro, "xmqr-broker"), None)),
        ("client-deb", "client", lambda: (deb_payload(args.client_deb, args.distro, "xmqr-client"), None)),
        ("broker-image", "broker", lambda: image_payload(args.broker_image, "/usr/share/licenses/xmqr")),
        ("admin-image", "broker", lambda: image_payload(args.admin_image, "/usr/share/licenses/xmqr")),
        ("client-image", "client", lambda: image_payload(args.client_image, "/usr/share/licenses/xmqr-client")),
    ]
    sources = {
        "broker": (*expected_collection(args.broker_notices), (ROOT / "LICENSE").read_bytes()),
        "client": (*expected_collection(args.client_notices), (ROOT.parent / "xmqr-client" / "LICENSE").read_bytes()),
    }
    results = []
    for label, source, read in jobs:
        try:
            content, image_id = read()
            result = verify_payload(content, *sources[source], deb=label.endswith("-deb"))
            if image_id:
                result["image_id"] = image_id
        except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired, tarfile.TarError) as error:
            result = {"status": "FAIL", "reason": str(error)}
        result["artifact"] = label
        results.append(result)
        print(json.dumps(result), flush=True)
    report = {"schema": 1, "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
              "scope": "original notice text/paths/SHA and own MIT in package payload; no relicensing or complete legal audit",
              "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
