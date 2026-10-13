#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synchronize only Wi-Fi fields in an existing private firmware configuration."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
import uuid

REPO = Path(__file__).resolve().parents[2]
MAX_INPUT = 65536


def private_file(root, name):
    relative = Path(name)
    if relative.is_absolute() or len(relative.parts) != 1 or relative.name in (".", ".."):
        raise ValueError("invalid private file")
    path = (root / relative).resolve(strict=True)
    if path.parent != root or path.is_relative_to(REPO) or not path.is_file():
        raise ValueError("invalid private file")
    return path


def read_bounded(path):
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        raise ValueError("private input too large")
    return raw


def clean_string(value):
    return isinstance(value, str) and bool(value) and not any(
        ord(character) < 32 or ord(character) == 127 for character in value)


def sync(source_dir, private_dir):
    source = source_dir.resolve(strict=True)
    root = private_dir.resolve(strict=True)
    if any(not path.is_dir() or path.is_relative_to(REPO) for path in (source, root)):
        raise ValueError("private directory required")
    wifi = json.loads(read_bounded(private_file(source, "wifi-config.json")).decode("utf-8-sig"))
    ssid = wifi["ssid"]
    if not clean_string(ssid) or len(ssid.encode("utf-8")) > 32:
        raise ValueError("invalid SSID")
    password = read_bounded(private_file(source, wifi["password_file"])).decode("utf-8-sig").rstrip("\r\n")
    hexadecimal = len(password) == 64 and all(c in "0123456789abcdefABCDEF" for c in password)
    if not clean_string(password) or not (8 <= len(password.encode("utf-8")) <= 63 or hexadecimal):
        raise ValueError("invalid WPA2 password")
    target = private_file(root, "firmware-config.json")
    original = read_bounded(target)
    config = json.loads(original.decode("utf-8-sig"))
    if not isinstance(config, dict) or not all(clean_string(config.get(field)) for field in (
            "ssid", "wifi_password", "mqtt_url", "mqtt_username", "mqtt_password")):
        raise ValueError("invalid existing configuration")
    endpoint = urlsplit(config["mqtt_url"])
    if endpoint.scheme != "mqtts" or not endpoint.hostname or endpoint.username is not None or endpoint.password is not None:
        raise ValueError("invalid existing secure endpoint")
    if config["ssid"] == ssid and config["wifi_password"] == password:
        return False
    config.update(ssid=ssid, wifi_password=password)
    updated = json.dumps(config, ensure_ascii=False).encode("utf-8")
    identifier = uuid.uuid4().hex
    backup = root / f"firmware-config-before-sync-{identifier}.json"
    temporary = root / f"firmware-config-sync-{identifier}.tmp"
    # Exclusive files inherit the private directory ACL; never change host permissions.
    with backup.open("xb") as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        # Refuse a concurrent update or a replaced/symlinked target.
        if private_file(root, "firmware-config.json") != target or read_bounded(target) != original:
            raise ValueError("configuration changed during synchronization")
        os.replace(temporary, target)
    finally:
        if created and temporary.exists():
            temporary.unlink()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--private-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        changed = sync(args.source_dir, args.private_dir)
        print("E01_WIFI_CONFIG_UPDATED" if changed else "E01_WIFI_CONFIG_UNCHANGED")
    except Exception:
        print("E01_WIFI_CONFIG_FAILED (private details suppressed)", file=sys.stderr)
        sys.exit(1)
