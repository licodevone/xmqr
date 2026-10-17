#!/usr/bin/env python3
"""P142/C78: check PUBLISH request properties over real TCP and restart."""
import socket
import subprocess
import tempfile
import time

from verify_mqtt5_sessions import BROKER, CLIENT, connect, packet, start, stop
from verify_mqtt5_publish_metadata import subscribe

PROPERTIES = (
    b"\x08\x00\x07reply/t"
    b"\x09\x00\x03\x00\xff\x07"
    b"\x26\x00\x05trace\x00\x03one"
    b"\x26\x00\x05trace\x00\x03two"
)


def publish_client(port, topic, payload, qos=1, retain=False):
    result = subprocess.run([
        str(CLIENT), "pub", "--open-lab", "--port", str(port),
        "--protocol-version", "5", "--topic", topic.decode(),
        "--message", payload.decode(), "--qos", str(qos),
        "--retain", str(retain).lower(), "--response-topic", "reply/t",
        "--correlation-data-hex", "00ff07",
        "--publish-user-property", "trace=one",
        "--publish-user-property", "trace=two",
    ], capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


def receive(stream, topic, payload, qos, retained=False, properties=PROPERTIES):
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
    assert body[cursor:cursor + size] == properties, body
    assert body[cursor + size:] == payload, body
    if qos == 1:
        stream.sendall(b"\x40\x02" + identifier)
    elif qos == 2:
        stream.sendall(b"\x50\x02" + identifier)
        assert packet(stream) == (0x62, identifier)
        stream.sendall(b"\x70\x02" + identifier)


def main():
    assert BROKER.is_file() and CLIENT.is_file(), "build Linux broker/client first"
    with tempfile.TemporaryDirectory(prefix="xmqr-v5-request-props-") as state:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        broker = start(port, state)
        try:
            live, _ = connect(port, True, 0, b"request-live")
            subscribe(live, b"request/live")
            for qos in (0, 1, 2):
                payload = f"qos-{qos}".encode()
                publish_client(port, b"request/live", payload, qos)
                receive(live, b"request/live", payload, qos)
            live.close()

            offline, _ = connect(port, True, 0xFFFFFFFF, b"request-offline")
            subscribe(offline, b"request/offline", qos=1)
            offline.sendall(b"\xe0\x00")
            offline.close()
            publish_client(port, b"request/offline", b"offline")
            publish_client(port, b"request/retained", b"retained", retain=True)

            external = subprocess.Popen([
                "mosquitto_sub", "-V", "mqttv311", "-i", "request-v311",
                "-h", "127.0.0.1", "-p", str(port), "-t", "request/live", "-C", "1",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(0.3)
                assert external.poll() is None
                publish_client(port, b"request/live", b"mqtt311")
                out, err = external.communicate(timeout=8)
                assert external.returncode == 0 and out == b"mqtt311\n", (out, err)
            finally:
                if external.poll() is None:
                    external.kill()
                    external.wait(timeout=4)

            external_sub, _ = connect(port, True, 0, b"request-mosquitto-sub")
            subscribe(external_sub, b"request/external", qos=1)
            external_pub = subprocess.run([
                "mosquitto_pub", "-V", "mqttv5", "-i", "request-mosquitto-pub",
                "-h", "127.0.0.1", "-p", str(port), "-t", "request/external",
                "-m", "external", "-q", "1",
                "-D", "publish", "response-topic", "reply/t",
                "-D", "publish", "correlation-data", "00ff07",
                "-D", "publish", "user-property", "trace", "one",
                "-D", "publish", "user-property", "trace", "two",
            ], capture_output=True, timeout=8)
            assert external_pub.returncode == 0, external_pub.stderr
            external_properties = (
                b"\x08\x00\x07reply/t\x09\x00\x0600ff07"
                b"\x26\x00\x05trace\x00\x03one"
                b"\x26\x00\x05trace\x00\x03two"
            )
            receive(external_sub, b"request/external", b"external", 1,
                    properties=external_properties)
            external_sub.close()
        finally:
            stop(broker)
        broker = start(port, state)
        try:
            offline, present = connect(port, False, 0xFFFFFFFF, b"request-offline")
            assert present
            receive(offline, b"request/offline", b"offline", 1)
            offline.close()
            retained, _ = connect(port, True, 0, b"request-retained")
            subscribe(retained, b"request/retained", qos=1)
            receive(retained, b"request/retained", b"retained", 1, retained=True)
            retained.close()
        finally:
            stop(broker)
    print("PASS: MQTT 5 request properties QoS0/1/2, retained, offline/restart, MQTT3 subscriber, Mosquitto publisher")


if __name__ == "__main__":
    main()
