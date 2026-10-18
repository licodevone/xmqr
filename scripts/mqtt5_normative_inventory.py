#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P231: index numbered OASIS references, never infer protocol conformance.

Input is a separately downloaded official HTML file. No network, broker, build,
or external service is started. The standard itself is not redistributed.
"""
import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

SOURCE_URL = "https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html"
MAX_SOURCE_BYTES = 8 * 1024 * 1024
REQUIREMENT = re.compile(
    r"\[\s*MQTT-\s*(\d+(?:\s*\.\s*\d+)+)\s*-\s*(\d+)\s*\]"
)


class DocumentText(HTMLParser):
    """Keep inline text joined, ignoring comments, scripts and style sheets."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif not self.hidden and tag in {
            "p", "div", "br", "td", "th", "li", "h1", "h2", "h3", "h4"
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif not self.hidden and tag in {"p", "div", "td", "th", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


class CharsetMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.charsets = []

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        elif tag == "meta" and self.in_head:
            values = dict(attrs)
            if values.get("charset"):
                self.charsets.append(values["charset"].lower())
            if values.get("http-equiv", "").lower() == "content-type":
                match = re.search(r"charset\s*=\s*([a-zA-Z0-9_-]+)",
                                  values.get("content", ""), re.I)
                if match:
                    self.charsets.append(match[1].lower())

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False


def decode_source(raw):
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("source must contain 1..8388608 bytes")
    header = raw[:16384].decode("ascii", errors="ignore")
    metadata = CharsetMetadata()
    metadata.feed(header)
    metadata.close()
    declared = set(metadata.charsets)
    if len(declared) != 1:
        raise ValueError("HTML head must declare one unambiguous charset")
    charset = declared.pop()
    encodings = {"utf-8": "utf-8-sig", "windows-1252": "cp1252"}
    if charset not in encodings:
        raise ValueError(f"unsupported declared charset: {charset}")
    return raw.decode(encodings[charset], errors="strict"), charset


def visible_text(html):
    parser = DocumentText()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts)


def extract_ids(text):
    found = Counter()
    for section, number in REQUIREMENT.findall(text):
        section = re.sub(r"\s", "", section)
        found[f"MQTT-{section}-{number}"] += 1
    return found


def numeric_key(identifier):
    return tuple(int(part) for part in re.split(r"[.-]", identifier[5:]))


def build_catalog(raw):
    html, charset = decode_source(raw)
    text = visible_text(html)
    flat = " ".join(text.split())
    if "MQTT Version 5.0" not in flat or "07 March 2019" not in flat:
        raise ValueError("source lacks expected MQTT 5.0 OS title/date")
    counts = extract_ids(text)
    if not counts:
        raise ValueError("no numbered MQTT references found")
    chapters = Counter(identifier.split("-")[1].split(".")[0] for identifier in counts)
    return {
        "schema_version": 1,
        "source": {
            "url": SOURCE_URL,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "charset": charset,
        },
        "meaning": "Unique numbered references, not a count of applicable MUST obligations",
        "audit_status": "NOT_AUDITED",
        "unique_ids": len(counts),
        "reference_occurrences": sum(counts.values()),
        "unique_ids_by_chapter": dict(sorted(chapters.items(), key=lambda item: int(item[0]))),
        "requirements": [
            {
                "id": identifier,
                "section": identifier.split("-")[1],
                "occurrences": counts[identifier],
                "broker": "UNREVIEWED",
                "client": "UNREVIEWED",
            }
            for identifier in sorted(counts, key=numeric_key)
        ],
    }


def check_catalog(actual, expected):
    # Python equality considers True == 1; canonical JSON retains scalar types.
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(
        expected, sort_keys=True, allow_nan=False
    ):
        raise ValueError("catalog differs from extraction; not a conformance verdict")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    try:
        # Bounded input, including when the file size changes while being read.
        with args.source.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        expected = build_catalog(raw)
        if args.check:
            actual = json.loads(args.check.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
            check_catalog(actual, expected)
            action = "CHECK_PASS"
        else:
            # Never overwrite source, existing catalog, or a symlink target.
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(expected, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            action = "GENERATED"
        print(json.dumps({
            "result": action,
            "unique_ids": expected["unique_ids"],
            "reference_occurrences": expected["reference_occurrences"],
            "audit_status": expected["audit_status"],
            "source_sha256": expected["source"]["sha256"],
        }))
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
