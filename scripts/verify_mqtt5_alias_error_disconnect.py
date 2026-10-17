#!/usr/bin/env python3
"""Exercise MQTT 5 Topic Alias invalid DISCONNECT without side effects."""
import socket
import tempfile

from verify_mqtt5_sessions import BROKER, connect, packet, start, stop


TOPIC = b"alias/error"


def publish(stream, name, alias, payload):
    properties = b"\x23" + alias.to_bytes(2, "big")
    body = len(name).to_bytes(2, "big") + name + bytes([len(properties)]) + properties + payload
    stream.sendall(bytes([0x30, len(body)]) + body)


def main():
    assert BROKER.is_file(), "build the Linux broker first"
    with tempfile.TemporaryDirectory(prefix="xmqr-alias-error-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"alias-error-watcher")
            body = b"\x00\x01\x00" + len(TOPIC).to_bytes(2, "big") + TOPIC + b"\x00"
            watcher.sendall(bytes([0x82, len(body)]) + body)
            assert packet(watcher) == (0x90, b"\x00\x01\x00\x00")
            for index, (name, alias) in enumerate(((TOPIC, 0), (TOPIC, 17), (b"", 1))):
                source, _ = connect(port, True, 0, f"alias-error-{index}".encode())
                publish(source, name, alias, b"invalid")
                assert packet(source) == (0xe0, b"\x94\x00")
                assert source.recv(1) == b""
                source.close()
            watcher.settimeout(0.5)
            try:
                unexpected = packet(watcher)
            except socket.timeout:
                pass
            else:
                raise AssertionError(f"invalid alias reached subscriber: {unexpected}")
            watcher.settimeout(4)
            source, _ = connect(port, True, 0, b"alias-error-valid")
            publish(source, TOPIC, 1, b"valid")
            header, delivered = packet(watcher)
            assert header == 0x30 and delivered.endswith(b"\x00valid"), (header, delivered)
            source.sendall(b"\xe0\x00")
            watcher.sendall(b"\xe0\x00")
            source.close()
            watcher.close()
        finally:
            if broker.poll() is None:
                stop(broker)
    print("P176_ALIAS_DISCONNECT_PASS zero, excess, unknown, no delivery, valid alias")


if __name__ == "__main__":
    main()
