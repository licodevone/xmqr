# Offline license-text sources

These files resolve exact license-text omissions in locked Windows dependency
graphs. The listed crates declare the matching licenses but do not ship license
text in their `.crate` source archives. Archive-derived texts are copied
unmodified; the windows-permissions fallback is the canonical MIT permission
and disclaimer text, pinned by SHA-256, with both original Cargo manifest files
retained byte-for-byte as package author/license attribution. Its archive and
upstream repository contain no standalone copyright or license file; no
copyright holder or year is inferred.

| Template | Cargo source archive containing this exact text | Use |
| --- | --- | --- |
| `LICENSE-APACHE-2.0` | `asn1-rs 0.7.2` | `asn1-rs-impl 0.2.0`, same `rusticata/asn1-rs` repository; declared `MIT/Apache-2.0` |
| `LICENSE-MIT` | `asn1-rs 0.7.2` | `asn1-rs-impl 0.2.0`, same `rusticata/asn1-rs` repository; declared `MIT/Apache-2.0` |
| `UNLICENSE` | `aho-corasick 1.1.5` | `pharos 0.5.3` and `ws_stream_tungstenite 0.15.0`; each declares `Unlicense` and its packaged README links to unlicense.org |
| `MIT-windows-permissions-0.2.4.txt` | Canonical SPDX MIT permission/disclaimer text; SHA-256 pinned in `license_fallbacks.py` | `windows-permissions 0.2.4`, which declares `MIT`; the exact crates.io source archive checksum and unmodified `Cargo.toml` / `Cargo.toml.orig` are recorded with its notice |
| `windows-permissions-0.2.4-Cargo.toml*` | Exact files from the `windows-permissions 0.2.4` crates.io source archive | Preserves the crate's author and `MIT` declaration as attribution; source archive SHA-256 is pinned in `license_fallbacks.py` |

The collector only uses these files for the exact crate/version/license pairs
listed above, verifies pinned fallback text hashes, and records the source in
`LICENSE-SOURCE-NOTES.md` in the generated notices directory. Other missing or
undeclared license texts remain a packaging error.
