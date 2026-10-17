#!/usr/bin/env python3
"""Check MQTT 5 payload-format/content-type forwarding and durable replay."""
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, connect, packet, start, stop


def subscribe(stream, topic, qos=2):
    body = b"\x00\x01\x00" + len(topic).to_bytes(2, "big") + topic + bytes([qos])
    stream.sendall(bytes([0x82, len(body)]) + body)
    assert packet(stream) == (0x90, b"\x00\x01\x00" + bytes([qos]))


def publish_client(port, topic, payload, qos=1, retain=False):
    result = subprocess.run([
        str(CLIENT), "pub", "--open-lab", "--port", str(port),
        "--protocol-version", "5", "--topic", topic.decode(),
        "--message", payload.decode(), "--qos", str(qos),
        "--retain", str(retain).lower(), "--payload-format", "1",
        "--content-type", "text/plain",
    ], capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


def receive(stream, topic, payload, qos, retained=False):
    header, body = packet(stream)
    assert header >> 4 == 3 and (header >> 1) & 3 == qos, (header, body)
    assert bool(header & 1) == retained, header
    length = int.from_bytes(body[:2], "big")
    assert body[2:2 + length] == topic, body
    cursor = 2 + length
    identifier = None
    if qos:
        identifier = body[cursor:cursor + 2]
        cursor += 2
    size = body[cursor]
    cursor += 1
    properties = body[cursor:cursor + size]
    assert properties == b"\x01\x01\x03\x00\x0atext/plain", properties
    assert body[cursor + size:] == payload, body
    if qos == 1:
        stream.sendall(b"\x40\x02" + identifier)
    elif qos == 2:
        stream.sendall(b"\x50\x02" + identifier)
        assert packet(stream) == (0x62, identifier)
        stream.sendall(b"\x70\x02" + identifier)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-publish-metadata-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            live, _ = connect(port, True, 0, b"meta-live")
            subscribe(live, b"meta/live")
            for qos in (0, 1, 2):
                payload = f"qos-{qos}".encode()
                publish_client(port, b"meta/live", payload, qos)
                receive(live, b"meta/live", payload, qos)
            live.close()

            offline, _ = connect(port, True, 0xFFFFFFFF, b"meta-offline")
            subscribe(offline, b"meta/offline", qos=1)
            offline.sendall(b"\xe0\x00")
            offline.close()
            publish_client(port, b"meta/offline", b"offline", qos=1)
            publish_client(port, b"meta/retained", b"retained", qos=1, retain=True)

            external = subprocess.Popen([
                "mosquitto_sub", "-V", "mqttv311", "-i", "meta-v311",
                "-h", "127.0.0.1", "-p", str(port), "-t", "meta/live", "-C", "1",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(0.3)
                assert external.poll() is None
                publish_client(port, b"meta/live", b"mqtt311", qos=1)
                out, err = external.communicate(timeout=8)
                assert external.returncode == 0 and out == b"mqtt311\n", (out, err)
            finally:
                if external.poll() is None:
                    external.kill()
                    external.wait(timeout=4)

            external_sub, _ = connect(port, True, 0, b"meta-mosquitto-sub")
            subscribe(external_sub, b"meta/mosquitto", qos=1)
            external_pub = subprocess.run([
                "mosquitto_pub", "-V", "mqttv5", "-i", "meta-mosquitto-pub",
                "-h", "127.0.0.1", "-p", str(port), "-t", "meta/mosquitto",
                "-m", "external", "-q", "1",
                "-D", "publish", "payload-format-indicator", "1",
                "-D", "publish", "content-type", "text/plain",
            ], capture_output=True, timeout=8)
            assert external_pub.returncode == 0, external_pub.stderr
            receive(external_sub, b"meta/mosquitto", b"external", 1)
            external_sub.close()
        finally:
            stop(broker)
        broker = start(port, state)
        try:
            offline, present = connect(port, False, 0xFFFFFFFF, b"meta-offline")
            assert present
            receive(offline, b"meta/offline", b"offline", 1)
            offline.close()
            retained, _ = connect(port, True, 0, b"meta-retained")
            subscribe(retained, b"meta/retained", qos=1)
            receive(retained, b"meta/retained", b"retained", 1, retained=True)
            retained.close()
        finally:
            stop(broker)
    print("PASS: MQTT 5 PFI/Content Type QoS0/1/2, retained, offline/restart, MQTT3 subscriber, Mosquitto publisher")


if __name__ == "__main__":
    main()
