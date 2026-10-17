#!/usr/bin/env python3
"""Isolate Mosquitto 2.x subscriber alias parsing from the XMQR broker."""
import socket
import subprocess
import time

from verify_mqtt5_sessions import packet


def main():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        client = subprocess.Popen([
            "mosquitto_sub", "-V", "mqttv5", "-i", "alias-isolated", "-h", "127.0.0.1",
            "-p", str(port), "-t", "alias/one", "-C", "2", "-D", "connect",
            "topic-alias-maximum", "1", "-d",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            peer, _ = server.accept()
            with peer:
                peer.settimeout(4)
                assert packet(peer)[0] == 0x10
                peer.sendall(b"\x20\x03\x00\x00\x00")
                header, subscribe = packet(peer)
                assert header == 0x82
                peer.sendall(b"\x90\x04" + subscribe[:2] + b"\x00\x00")
                time.sleep(0.2)
                name = b"alias/one"
                first = (len(name).to_bytes(2, "big") + name + b"\x03\x23\x00\x01"
                         + b"external-one")
                second = b"\x00\x00\x03\x23\x00\x01external-two"
                peer.sendall(bytes([0x30, len(first)]) + first)
                time.sleep(0.1)
                peer.sendall(bytes([0x30, len(second)]) + second)
                out, err = client.communicate(timeout=5)
                assert client.returncode == 2 and b"external-one\n" in out
                assert b"network protocol error" in err.lower(), err
                print("EXPECTED_LIMITATION: Mosquitto 2.0.22 rejects valid established Topic Alias on second PUBLISH")
        finally:
            if client.poll() is None:
                client.kill()
                client.wait(timeout=4)


if __name__ == "__main__":
    main()
