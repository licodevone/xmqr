#!/usr/bin/env python3
"""P152/C89: unsupported shared subscriptions are announced and refused."""
import subprocess
import tempfile
from pathlib import Path

from verify_mqtt5_sessions import packet, start, stop
from verify_mqtt5_subscribe_options import connect, free_port


CLIENT = Path(__file__).resolve().parents[2] / "xmqr-client/target/release/mqtt-client"
TOPIC = b"p152/value"
SHARED = b"$share/workers/p152/value"


def subscribe_frame(filters):
    body = b"\x00\x01\x00"
    for item in filters:
        body += len(item).to_bytes(2, "big") + item + b"\x00"
    return bytes([0x82, len(body)]) + body


def main():
    assert CLIENT.is_file(), "build Linux client C89 release binary first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p152-") as state:
        port = free_port()
        broker = start(port, state)
        try:
            with connect(port, b"p152-raw", persistent=True)[0] as stream:
                stream.sendall(subscribe_frame((TOPIC, SHARED)))
                assert packet(stream) == (0xe0, b"\x9e\x00")
            result = subprocess.run(
                [str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
                 "--port", str(port), "--topic", SHARED.decode(), "--count", "1"],
                capture_output=True, timeout=8,
            )
            assert result.returncode != 0 and b"shared subscriptions" in result.stderr, result.stderr
        finally:
            stop(broker)
        snapshot = (Path(state) / "state.snapshot").read_bytes()
        assert SHARED not in snapshot and TOPIC not in snapshot, "shared SUBSCRIBE partially committed"
        broker = start(port, state)
        try:
            with connect(port, b"p152-normal")[0] as normal:
                normal.sendall(subscribe_frame((TOPIC,)))
                assert packet(normal) == (0x90, b"\x00\x01\x00\x00")
                with connect(port, b"p152-publisher")[0] as publisher:
                    body = len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00ok"
                    publisher.sendall(bytes([0x30, len(body)]) + body)
                header, body = packet(normal)
                assert header == 0x30 and body.endswith(b"\x00ok"), (header, body)
        finally:
            stop(broker)
    print("P152_C89_PASS CONNACK unavailable, DISCONNECT 0x9E, no partial state, normal delivery")


if __name__ == "__main__":
    main()
