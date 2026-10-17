#!/usr/bin/env python3
"""Real TCP MQTT 5 Will Delay, cancellation, expiry and restart."""
import select
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, connect, packet, start, stop


def subscribe(stream, topic=b"will/check"):
    body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + b"\x00"
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00\x00")


def connect_will(port, identity, delay, session_expiry, payload, clean=True):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    topic = b"will/check"
    props = bytes([0x18]) + delay.to_bytes(4, "big")
    body = (b"\x00\x04MQTT\x05" + bytes([0x06 if clean else 0x04]) + b"\x00\x1e"
            + b"\x05\x11" + session_expiry.to_bytes(4, "big")
            + len(identity).to_bytes(2, "big") + identity
            + bytes([len(props)]) + props
            + len(topic).to_bytes(2, "big") + topic
            + len(payload).to_bytes(2, "big") + payload)
    assert len(body) < 128
    stream.sendall(bytes([0x10, len(body)]) + body)
    ack_header, ack = packet(stream)
    assert ack_header == 0x20 and ack[1] == 0, (ack_header, ack)
    return stream


def expect_will(stream, payload):
    header, body = packet(stream)
    assert header & 0xf0 == 0x30, (header, body)
    assert body.endswith(payload), body


def expect_silence(stream, seconds):
    stream.settimeout(seconds)
    try:
        packet(stream)
        raise AssertionError("Will published before deadline or after cancellation")
    except socket.timeout:
        pass
    finally:
        stream.settimeout(4)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-will-delay-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            watcher, _ = connect(port, True, 0, b"will-watcher")
            subscribe(watcher)

            source = connect_will(port, b"will-delayed", 1, 0xFFFFFFFF, b"delayed")
            source.close()
            expect_silence(watcher, 0.4)
            expect_will(watcher, b"delayed")

            source = connect_will(port, b"will-cancelled", 2, 0xFFFFFFFF, b"cancelled")
            source.close()
            resumed, present = connect(port, False, 0xFFFFFFFF, b"will-cancelled")
            assert present
            resumed.sendall(b"\xe0\x00")
            resumed.close()
            expect_silence(watcher, 2.2)

            source = connect_will(port, b"will-clean", 10, 0xFFFFFFFF, b"clean")
            source.close()
            fresh, present = connect(port, True, 0, b"will-clean")
            assert not present
            expect_will(watcher, b"clean")
            fresh.sendall(b"\xe0\x00")
            fresh.close()

            source = connect_will(port, b"will-short", 10, 1, b"session-end")
            source.close()
            expect_silence(watcher, 0.4)
            expect_will(watcher, b"session-end")

            source = connect_will(port, b"will-zero", 10, 0, b"zero-session")
            source.close()
            expect_will(watcher, b"zero-session")

            source = connect_will(port, b"will-normal", 1, 0xFFFFFFFF, b"normal")
            source.sendall(b"\xe0\x00")
            source.close()
            expect_silence(watcher, 1.2)

            source = connect_will(port, b"will-restart", 2, 0xFFFFFFFF, b"restart")
            source.close()
            time.sleep(0.2)
            watcher.close()
            stop(broker)
            broker = start(port, state)
            watcher, _ = connect(port, True, 0, b"will-watcher")
            subscribe(watcher)
            expect_will(watcher, b"restart")

            source = connect_will(port, b"will-crash", 1, 0xFFFFFFFF, b"crash")
            watcher.close()
            broker.kill()
            broker.wait(timeout=8)
            source.close()
            broker = start(port, state)
            watcher, _ = connect(port, True, 0, b"will-watcher")
            subscribe(watcher)
            expect_will(watcher, b"crash")

            child = subprocess.Popen([
                CLIENT, "sub", "--open-lab", "--protocol-version", "5",
                "--port", str(port), "--topic", "will/idle", "--client-id", "will-client", "--output", "jsonl",
                "--session-expiry-seconds", "never", "--will-topic", "will/check",
                "--will-message", "from-client", "--will-delay-seconds", "1",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                assert select.select([child.stderr], [], [], 5)[0], "client SUBACK readiness timeout"
                ready = child.stderr.readline()
                assert b"Assinatura ativa" in ready, ready
                child.kill()
                child.wait(timeout=4)
                expect_will(watcher, b"from-client")
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=4)
            external = subprocess.Popen([
                "mosquitto_sub", "-d", "-V", "mqttv5", "-i", "will-mosquitto",
                "-h", "127.0.0.1", "-p", str(port), "-t", "will/idle",
                "--will-topic", "will/check", "--will-payload", "from-mosquitto",
                "-D", "will", "will-delay-interval", "1",
                "-D", "connect", "session-expiry-interval", "10",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                time.sleep(0.5)
                assert external.poll() is None, external.stderr.read()
                external.kill()
                external.wait(timeout=4)
                expect_will(watcher, b"from-mosquitto")
            finally:
                if external.poll() is None:
                    external.kill()
                    external.wait(timeout=4)
            watcher.sendall(b"\xe0\x00")
            watcher.close()
            print("PASS: MQTT 5 Will Delay, reconnect cancel, Clean Start, Session Expiry, restart, client C70 and Mosquitto")
        finally:
            if broker.poll() is None:
                stop(broker)


if __name__ == "__main__":
    main()
