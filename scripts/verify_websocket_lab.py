#!/usr/bin/env python3
"""P210: bounded loopback WebSocket MQTT interop and negative wire checks."""
import argparse
import base64
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from verify_mqtt5_sessions import packet as tcp_packet


ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / "target/debug/mqtt-broker"
CLIENT = ROOT.parent / "xmqr-client/target/release/mqtt-client"


def reserve_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def run_client(command, port, version, websocket, extra):
    args = [str(CLIENT), command, "--open-lab", "--protocol-version", version,
            "--topic", "p210/check", "--client-id", f"p210-{command}-{time.monotonic_ns() % 100000000:08d}"]
    args += (["--ws-url", f"ws://127.0.0.1:{port}/mqtt"] if websocket
             else ["--port", str(port)])
    result = subprocess.run(args + extra, capture_output=True, timeout=10)
    assert result.returncode == 0, (args, result.stderr.decode(errors="replace"))
    return result.stdout


def exact(stream, count):
    data = bytearray()
    while len(data) < count:
        chunk = stream.recv(count - len(data))
        if not chunk:
            raise AssertionError("WebSocket closed before expected bytes")
        data.extend(chunk)
    return bytes(data)


def handshake(port, path="/mqtt", protocol="mqtt", origin=None):
    stream = socket.create_connection(("127.0.0.1", port), timeout=4)
    stream.settimeout(4)
    try:
        request = (f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                   "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                   f"Sec-WebSocket-Key: {base64.b64encode(os.urandom(16)).decode()}\r\n"
                   "Sec-WebSocket-Version: 13\r\n"
                   f"Sec-WebSocket-Protocol: {protocol}\r\n"
                   + (f"Origin: {origin}\r\n" if origin else "") + "\r\n")
        stream.sendall(request.encode())
        response = bytearray()
        while not response.endswith(b"\r\n\r\n"):
            response.extend(exact(stream, 1))
            assert len(response) < 4096
        return stream, bytes(response)
    except BaseException:
        stream.close()
        raise


def send_frame(stream, opcode, payload, fin=True):
    head = bytes([(0x80 if fin else 0) | opcode])
    length = len(payload)
    if length < 126:
        head += bytes([0x80 | length])
    elif length < 65536:
        head += b"\xfe" + length.to_bytes(2, "big")
    else:
        head += b"\xff" + length.to_bytes(8, "big")
    mask = os.urandom(4)
    stream.sendall(head + mask + bytes(byte ^ mask[index % 4]
                                       for index, byte in enumerate(payload)))


def receive_frame(stream):
    first, second = exact(stream, 2)
    length = second & 127
    if length == 126:
        length = int.from_bytes(exact(stream, 2), "big")
    elif length == 127:
        length = int.from_bytes(exact(stream, 8), "big")
    assert second & 0x80 == 0, "server frame must be unmasked"
    assert length < 100000, length
    return first & 15, exact(stream, length)


def mqtt_packet(stream, pending):
    while True:
        if len(pending) >= 2:
            size = 0
            multiplier = 1
            offset = 1
            while offset < len(pending):
                digit = pending[offset]
                size += (digit & 127) * multiplier
                offset += 1
                if digit & 128 == 0:
                    if len(pending) >= offset + size:
                        packet = bytes(pending[:offset + size])
                        del pending[:offset + size]
                        return packet
                    break
                multiplier *= 128
        opcode, payload = receive_frame(stream)
        assert opcode == 2, (opcode, payload)
        pending.extend(payload)


def mqtt_connect(version, identifier):
    body = (b"\x00\x04MQTT" + bytes([version, 2, 0, 30])
            + (b"\x00" if version == 5 else b"")
            + len(identifier).to_bytes(2, "big") + identifier)
    return bytes([0x10, len(body)]) + body


def raw_checks(ws_port, tcp_port):
    stalled = socket.create_connection(("127.0.0.1", ws_port), timeout=4)
    stalled.settimeout(5)
    stalled.sendall(b"GET /mqtt HTTP/1.1\r\nHost: 127.0.0.1\r\n")
    assert stalled.recv(1) == b"", "partial WebSocket handshake exceeded deadline"
    stalled.close()
    stalled, response = handshake(ws_port)
    assert response.startswith(b"HTTP/1.1 101"), response
    stalled.settimeout(5)
    assert stalled.recv(1) == b"", "missing initial MQTT bytes exceeded deadline"
    stalled.close()
    for path, protocol in (("/bad", "mqtt"), ("/mqtt", "other"),
                           ("/mqtt?x=1", "mqtt")):
        stream, response = handshake(ws_port, path, protocol)
        assert response.startswith(b"HTTP/1.1 400"), response
        stream.close()
    stream, response = handshake(ws_port, origin="https://example.invalid")
    assert response.startswith(b"HTTP/1.1 400"), response
    stream.close()

    for version in (4, 5):
        stream, response = handshake(ws_port)
        assert response.startswith(b"HTTP/1.1 101"), response
        assert b"sec-websocket-protocol: mqtt" in response.lower(), response
        connect = mqtt_connect(version, b"p210-raw")
        middle = len(connect) // 2
        send_frame(stream, 2, connect[:middle], fin=False)
        send_frame(stream, 0, connect[middle:])
        connack = mqtt_packet(stream, bytearray())
        assert connack[0] == 0x20, connack
        length = connack[1]
        assert length == len(connack) - 2 and connack[2:4] == b"\x00\x00", connack
        assert length >= (3 if version == 5 else 2), connack
        send_frame(stream, 1, "texto não é MQTT".encode())
        try:
            opcode, _ = receive_frame(stream)
            assert opcode == 8, opcode
        except ConnectionResetError:
            pass
        except AssertionError as error:
            assert str(error) == "WebSocket closed before expected bytes", error
        stream.close()

    stream, response = handshake(ws_port)
    assert response.startswith(b"HTTP/1.1 101"), response
    send_frame(stream, 2, b"x" * (64 * 1024 + 1))
    try:
        opcode, _ = receive_frame(stream)
        assert opcode == 8, opcode
    except ConnectionResetError:
        pass
    except AssertionError as error:
        assert str(error) == "WebSocket closed before expected bytes", error
    stream.close()

    for version in (4, 5):
        ws, response = handshake(ws_port)
        assert response.startswith(b"HTTP/1.1 101"), response
        tcp = socket.create_connection(("127.0.0.1", tcp_port), timeout=4)
        tcp.settimeout(4)
        pending = bytearray()
        try:
            send_frame(ws, 2, mqtt_connect(version, b"p210-ws"))
            tcp.sendall(mqtt_connect(version, b"p210-tcp"))
            assert mqtt_packet(ws, pending)[0] == 0x20
            assert tcp_packet(tcp)[0] == 0x20
            topic = b"p210/check"
            subscribe = (b"\x00\x01" + (b"\x00" if version == 5 else b"")
                         + len(topic).to_bytes(2, "big") + topic + b"\x00")
            send_frame(ws, 2, bytes([0x82, len(subscribe)]) + subscribe)
            tcp.sendall(bytes([0x82, len(subscribe)]) + subscribe)
            assert mqtt_packet(ws, pending)[0] == 0x90
            assert tcp_packet(tcp)[0] == 0x90
            for source, payload in (("tcp", b"to-ws"), ("ws", b"to-tcp")):
                body = (len(topic).to_bytes(2, "big") + topic
                        + (b"\x00" if version == 5 else b"") + payload)
                publish = bytes([0x30, len(body)]) + body
                if source == "tcp":
                    tcp.sendall(publish)
                else:
                    send_frame(ws, 2, publish)
                delivered_ws = mqtt_packet(ws, pending)
                delivered_tcp = tcp_packet(tcp)
                assert delivered_ws[0] == 0x30 and delivered_ws.endswith(payload), delivered_ws
                assert delivered_tcp[0] == 0x30 and delivered_tcp[1].endswith(payload), delivered_tcp
            send_frame(ws, 2, b"\xe0\x00")
            tcp.sendall(b"\xe0\x00")
        finally:
            ws.close()
            tcp.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-only", action="store_true", help="CI checks without sibling client binary")
    options = parser.parse_args()
    assert BROKER.is_file() and (options.raw_only or CLIENT.is_file()), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-p210-") as root:
        tcp_port, ws_port = reserve_port(), reserve_port()
        assert tcp_port != ws_port
        env = {key: value for key, value in os.environ.items() if not key.startswith("MQTT_")}
        env.update(MQTT_MODE="open-lab", MQTT_BIND=f"127.0.0.1:{tcp_port}",
                   MQTT_WS_BIND=f"127.0.0.1:{ws_port}", MQTT_STATE_DIR=root,
                   RUST_LOG="error")
        for overrides in (
            {"MQTT_WS_BIND": f"0.0.0.0:{ws_port}"},
            {"MQTT_WS_BIND": "127.0.0.1:0"},
            {"MQTT_WS_BIND": f"127.0.0.1:{tcp_port}"},
            {"MQTT_MODE": "password-lab"},
        ):
            denied = subprocess.run([str(BROKER)], env=dict(env, **overrides),
                                    capture_output=True, timeout=4)
            assert denied.returncode != 0 and b"MQTT_WS_BIND requires open-lab" in denied.stderr, denied.stderr
        broker = subprocess.Popen([str(BROKER)], env=env, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if broker.poll() is not None:
                    raise AssertionError(broker.stderr.read().decode())
                try:
                    with socket.create_connection(("127.0.0.1", ws_port), timeout=.1):
                        break
                except OSError:
                    time.sleep(.05)
            else:
                raise AssertionError("WS listener readiness timeout")
            raw_checks(ws_port, tcp_port)
            if not options.raw_only:
                for version in ("3.1.1", "5"):
                    run_client("pub", ws_port, version, True,
                               ["--message", "from-ws", "--retain", "true"])
                    received = run_client("sub", tcp_port, version, False, ["--count", "1"])
                    assert b"from-ws" in received, received
                    run_client("pub", tcp_port, version, False,
                               ["--message", "from-tcp", "--retain", "true"])
                    received = run_client("sub", ws_port, version, True, ["--count", "1"])
                    assert b"from-tcp" in received, received
        finally:
            if broker.poll() is None:
                broker.terminate()
            broker.wait(timeout=8)
            broker.stderr.close()
        admission_env = dict(env, MQTT_MAX_CONNECTIONS="1")
        admission = subprocess.Popen([str(BROKER)], env=admission_env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                try:
                    held, response = handshake(ws_port)
                    if response.startswith(b"HTTP/1.1 101"):
                        break
                    held.close()
                except OSError:
                    time.sleep(.05)
            else:
                raise AssertionError("admission broker readiness timeout")
            send_frame(held, 2, mqtt_connect(4, b"p210-held"))
            assert mqtt_packet(held, bytearray())[0] == 0x20
            blocked = socket.create_connection(("127.0.0.1", tcp_port), timeout=4)
            blocked.settimeout(4)
            assert blocked.recv(1) == b"", "TCP exceeded shared admission limit"
            blocked.close()
            held.close()
            for _ in range(100):
                recovered = socket.create_connection(("127.0.0.1", tcp_port), timeout=4)
                recovered.settimeout(.2)
                recovered.sendall(mqtt_connect(4, b"p210-free"))
                try:
                    if tcp_packet(recovered)[0] == 0x20:
                        recovered.sendall(b"\xe0\x00")
                        recovered.close()
                        break
                except (OSError, AssertionError):
                    pass
                recovered.close()
                time.sleep(.02)
            else:
                raise AssertionError("shared admission slot was not released")
            for _ in range(100):
                try:
                    draining, response = handshake(ws_port)
                    assert response.startswith(b"HTTP/1.1 101"), response
                    break
                except OSError:
                    time.sleep(.02)
                except AssertionError as error:
                    assert str(error) == "WebSocket closed before expected bytes", error
                    time.sleep(.02)
            else:
                raise AssertionError("shared admission slot did not drain after TCP DISCONNECT")
            send_frame(draining, 2, mqtt_connect(4, b"p210-drain"))
            assert mqtt_packet(draining, bytearray())[0] == 0x20
            admission.terminate()
            send_frame(draining, 2, b"\xe0\x00")
            draining.close()
            assert admission.wait(timeout=8) == 0, "broker shutdown with WS client failed"
        finally:
            if admission.poll() is None:
                admission.terminate()
            admission.wait(timeout=8)
            admission.stderr.close()
        config = Path(root) / "websocket.toml"
        config.write_text(
            "version = 1\n[broker]\nmode = 'open-lab'\n"
            f"bind = '127.0.0.1:{tcp_port}'\nws_bind = '127.0.0.1:{ws_port}'\n"
            f"state_dir = '{Path(root) / 'toml-state'}'\n"
        )
        from_file = subprocess.Popen(
            [str(BROKER)],
            env={**{key: value for key, value in os.environ.items()
                    if not key.startswith("MQTT_")}, "MQTT_CONFIG": str(config)},
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            for _ in range(100):
                if from_file.poll() is not None:
                    raise AssertionError(from_file.stderr.read().decode())
                try:
                    stream, response = handshake(ws_port)
                    assert response.startswith(b"HTTP/1.1 101"), response
                    stream.close()
                    break
                except OSError:
                    time.sleep(.05)
            else:
                raise AssertionError("TOML WebSocket listener readiness timeout")
        finally:
            if from_file.poll() is None:
                from_file.terminate()
            from_file.wait(timeout=8)
            from_file.stderr.close()
    print("P210_WEBSOCKET_LAB_PASS MQTT311/5, TCP crossing, fragmented binary, text, size, handshake")


if __name__ == "__main__":
    main()
