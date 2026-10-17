#!/usr/bin/env python3
"""P158: client 0.24.0 reports the distinct MQTT 5 CONNACK 0x8C reason."""
import socket
import subprocess
import threading
from pathlib import Path


CLIENT = Path(__file__).resolve().parents[2] / "xmqr-client/target/release/mqtt-client"


def main():
    assert CLIENT.is_file(), "build the published Linux client first"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        received = []

        def refuse():
            with listener.accept()[0] as stream:
                stream.settimeout(4)
                received.append(stream.recv(1024))
                stream.sendall(b"\x20\x03\x00\x8c\x00")

        worker = threading.Thread(target=refuse, daemon=True)
        worker.start()
        result = subprocess.run(
            [str(CLIENT), "sub", "--open-lab", "--protocol-version", "5",
             "--host", "127.0.0.1", "--port", str(port), "--topic", "p158/check",
             "--count", "1"],
            capture_output=True, timeout=6,
        )
        worker.join(timeout=4)
        assert not worker.is_alive(), "fixture connection did not finish"
        assert received and received[0][0] == 0x10 and b"MQTT\x05" in received[0]
        assert result.returncode != 0 and b"0x8C" in result.stderr, result.stderr
    print("P158_CLIENT_PASS MQTT 5 bad authentication method is explicit")


if __name__ == "__main__":
    main()
