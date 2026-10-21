"""Reviewed license-text fallbacks for exact Cargo archive omissions."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil


FALLBACKS = {
    ("asn1-rs-impl", "0.2.0"): {
        "license": "MIT/Apache-2.0",
        "files": ("LICENSE-MIT", "LICENSE-APACHE-2.0"),
        "source": "crates.io source archive asn1-rs 0.7.2; same rusticata/asn1-rs upstream repository",
    },
    ("pharos", "0.5.3"): {
        "license": "Unlicense",
        "files": ("UNLICENSE",),
        "source": "crates.io source archive aho-corasick 1.1.5; its package declares Unlicense OR MIT",
    },
    ("ws_stream_tungstenite", "0.15.0"): {
        "license": "Unlicense",
        "files": ("UNLICENSE",),
        "source": "crates.io source archive aho-corasick 1.1.5; its package declares Unlicense OR MIT",
    },
    ("windows-permissions", "0.2.4"): {
        "license": "MIT",
        "files": (
            "MIT-windows-permissions-0.2.4.txt",
            "windows-permissions-0.2.4-Cargo.toml",
            "windows-permissions-0.2.4-Cargo.toml.orig",
        ),
        "source": (
            "crates.io windows-permissions 0.2.4 source archive "
            "sha256:9e2ccdc3c6bf4d4a094e031b63fadd08d8e42abd259940eb8aa5fdc09d4bf9be; "
            "upstream source revision 8740e4efbd88dd01046ad9c169894f3a52eb6e2c; "
            "the archive and upstream repository contain no standalone license or copyright file; "
            "MIT permission/disclaimer text follows the SPDX License List at https://spdx.org/licenses/MIT.html; "
            "Cargo.toml and Cargo.toml.orig are included byte-for-byte as author/license attribution"
        ),
        "sha256": {
            "MIT-windows-permissions-0.2.4.txt": "508a77d2e7b51d98adeed32648ad124b7b30241a8e70b2e72c99f92d8e5874d1",
            "windows-permissions-0.2.4-Cargo.toml": "7d7095e9b45322206e2e46466eafd90581f34dfab8a9c046ed4a5da1054f88a9",
            "windows-permissions-0.2.4-Cargo.toml.orig": "6b94500e0e663637e2ea697d70b7910ab341c03b2074116d39169aa9c5deac2a",
        },
        "archive_sha256": "9e2ccdc3c6bf4d4a094e031b63fadd08d8e42abd259940eb8aa5fdc09d4bf9be",
    },
}


def fallback_sources(
    name: str, version: str, license_expression: str | None, template_root: Path
) -> dict[str, object] | None:
    """Return byte sources only for a reviewed crate/version/expression tuple."""
    fallback = FALLBACKS.get((name, version))
    if fallback is None or license_expression != fallback["license"]:
        return None
    paths = [template_root / filename for filename in fallback["files"]]
    if not all(path.is_file() for path in paths):
        return None
    digests = {path.name: sha256(path.read_bytes()).hexdigest() for path in paths}
    expected = fallback.get("sha256")
    if expected is not None and digests != expected:
        return None
    return {
        "files": paths,
        "source": fallback["source"],
        "digests": digests,
        "archive_sha256": fallback.get("archive_sha256"),
    }


def copy_fallbacks(fallback: dict[str, object], destination: Path) -> list[Path]:
    """Copy reviewed license bytes and verify the output digest immediately."""
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for source in fallback["files"]:
        target = destination / source.name
        shutil.copy2(source, target)
        if target.read_bytes() != source.read_bytes():
            raise OSError(f"License fallback copy did not preserve bytes: {source.name}")
        copied.append(target)
    return copied
