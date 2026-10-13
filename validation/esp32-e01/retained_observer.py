# SPDX-License-Identifier: MIT
"""Bounded MQTT3.1.1 wire observer; no Rust/ESP-IDF codec or third-party client."""
import socket
import ssl
import struct
import time

BYTES_TOPIC = b"e01/board/bytes"
RETAINED_TOPIC = b"e01/board/retained"
CONTROL_TOPIC = b"e01/board/control"
MAX_PACKET = 4096
MAX_FRAMES = 32


def field(value):
    if not isinstance(value, bytes) or len(value) > 1024:
        raise ValueError("invalid bounded field")
    return struct.pack("!H", len(value)) + value


def packet(header, body):
    length = len(body)
    if length + 5 > MAX_PACKET:
        raise ValueError("packet limit")
    encoded = bytearray([header])
    while True:
        digit = length % 128
        length //= 128
        encoded.append(digit | (128 if length else 0))
        if not length:
            break
    return bytes(encoded) + body


def payload(sequence):
    if not 0 <= sequence <= 4:
        raise ValueError("invalid synthetic sequence")
    return bytes([sequence]) + bytes(i % 251 for i in range(1, 1024))


def publication(header, body):
    # Observer requests QoS1; receiving QoS2 would violate the granted maximum.
    qos = (header >> 1) & 3
    if header >> 4 != 3 or qos not in (0, 1) or (qos == 0 and header & 8) or len(body) < 2:
        raise ValueError("invalid publication")
    length = int.from_bytes(body[:2], "big")
    end = 2 + length
    if not 0 < length <= 1024 or end > len(body):
        raise ValueError("invalid publication topic")
    topic = body[2:end]
    identifier = None
    if qos:
        if end + 2 > len(body):
            raise ValueError("missing packet identifier")
        identifier = int.from_bytes(body[end:end + 2], "big")
        if not identifier:
            raise ValueError("invalid packet identifier")
        end += 2
    return topic, qos, bool(header & 1), body[end:], identifier


class Peer:
    def __init__(self, host, port, certs, username, password, client_id, deadline=float("inf")):
        self.deadline = deadline
        context = ssl.create_default_context(cafile=str(certs / "ca.crt"))
        context.load_cert_chain(certs / "observer.crt", certs / "observer.key")
        raw = socket.create_connection((host, port), timeout=self.timeout(3))
        try:
            self.stream = context.wrap_socket(raw, server_hostname=host)
        except Exception:
            raw.close()
            raise
        self.pending = []
        self.identifier = 0
        try:
            body = field(b"MQTT") + b"\x04\xc2" + struct.pack("!H", 300)
            body += field(client_id.encode("ascii")) + field(username.encode()) + field(password.encode())
            self.send(0x10, body)
            if self.receive(time.monotonic() + 3) != (0x20, b"\0\0"):
                raise ValueError("observer CONNECT rejected")
        except Exception:
            self.stream.close()
            raise

    def send(self, header, body=b""):
        self.stream.settimeout(self.timeout(3))
        self.stream.sendall(packet(header, body))

    def timeout(self, seconds):
        remaining = min(seconds, self.deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError("observer global deadline")
        return remaining

    def exact(self, count, deadline):
        result = bytearray()
        while len(result) < count:
            remaining = min(deadline, self.deadline) - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("observer deadline")
            self.stream.settimeout(remaining)
            value = self.stream.recv(count - len(result))
            if not value:
                raise EOFError("observer closed")
            result.extend(value)
        return bytes(result)

    def receive(self, deadline):
        header = self.exact(1, deadline)[0]
        length = 0
        for index in range(4):
            digit = self.exact(1, deadline)[0]
            length += (digit & 127) * 128 ** index
            if length + index + 2 > MAX_PACKET:
                raise ValueError("observer packet limit")
            if digit < 128:
                if index and digit == 0:
                    raise ValueError("noncanonical remaining length")
                return header, self.exact(length, deadline)
        raise ValueError("invalid remaining length")

    def next_id(self):
        self.identifier += 1
        if self.identifier > 65535:
            raise ValueError("observer identifier limit")
        return struct.pack("!H", self.identifier)

    def await_packet(self, header, expected):
        deadline = time.monotonic() + 3
        for _ in range(MAX_FRAMES):
            received, body = self.receive(deadline)
            if received == header:
                if body != expected:
                    raise ValueError("observer acknowledgment mismatch")
                return
            if received >> 4 == 3:
                if len(self.pending) >= MAX_FRAMES:
                    raise ValueError("observer queue limit")
                self.pending.append(self.decode(received, body))
            else:
                raise ValueError("unexpected observer packet")
        raise ValueError("observer frame limit")

    def decode(self, header, body):
        topic, qos, retained, data, identifier = publication(header, body)
        if identifier is not None:
            self.send(0x40, struct.pack("!H", identifier))
        return topic, qos, retained, data

    def subscribe(self, topic):
        identifier = self.next_id()
        self.send(0x82, identifier + field(topic) + b"\x01")
        self.await_packet(0x90, identifier + b"\x01")

    def message(self):
        if self.pending:
            return self.pending.pop(0)
        header, body = self.receive(time.monotonic() + 3)
        return self.decode(header, body)

    def confirm(self, sequence):
        identifier = self.next_id()
        self.send(0x32, field(CONTROL_TOPIC) + identifier + bytes([sequence]))
        self.await_packet(0x40, identifier)

    def assert_no_replay(self, seconds=2):
        if self.pending:
            raise ValueError("unexpected retained replay")
        self.stream.settimeout(self.timeout(seconds))
        try:
            first = self.stream.recv(1)
        except socket.timeout:
            # Absence is only an observation window on a still-responsive peer.
            self.send(0xc0)
            self.await_packet(0xd0, b"")
            if self.pending:
                raise ValueError("late retained replay")
            return
        if not first:
            raise EOFError("observer closed during absence check")
        raise ValueError("unexpected packet during absence check")

    def close(self):
        try:
            self.send(0xe0)
        finally:
            self.stream.close()


class Observer:
    def __init__(self, host, port, certs, config):
        self.arguments = (host, port, certs, config["username"], config["password"])
        self.deadline = float("inf")
        self.results = []
        self.base = Peer(*self.arguments, "e01-wire-base")
        try:
            self.base.subscribe(BYTES_TOPIC)
        except Exception:
            self.base.close()
            raise

    def event(self, line):
        if line.startswith("E01_LOOPBACK_PASS qos="):
            sequence = int(line.split("qos=", 1)[1][0])
            actual = self.base.message()
            if actual != (BYTES_TOPIC, min(sequence, 1), False, payload(sequence)):
                raise ValueError("observer loopback mismatch")
            self.results.append(f"WIRE_LOOPBACK_QOS{sequence}_1024_PASS")
        elif line.startswith("E01_RETAINED_STORED version=") or line == "E01_RETAINED_DELETED":
            sequence = 5 if line == "E01_RETAINED_DELETED" else int(line.split("version=", 1)[1][0]) + 2
            peer = Peer(*self.arguments, f"e01-wire-retained-{sequence}", deadline=self.deadline)
            try:
                peer.subscribe(RETAINED_TOPIC)
                if sequence == 5:
                    peer.assert_no_replay()
                elif peer.message() != (RETAINED_TOPIC, 1, True, payload(sequence)):
                    raise ValueError("observer retained mismatch")
                peer.confirm(sequence)
                self.results.append(f"WIRE_RETAINED_{sequence}_PASS")
            finally:
                peer.close()

    def complete(self):
        return self.results == [*(f"WIRE_LOOPBACK_QOS{q}_1024_PASS" for q in range(3)),
                                *(f"WIRE_RETAINED_{s}_PASS" for s in (3, 4, 5))]

    def close(self):
        self.base.close()
