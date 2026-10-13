# SPDX-License-Identifier: MIT
from collections import deque
import socket
import struct
import time
import unittest
from unittest.mock import Mock, patch

from retained_observer import BYTES_TOPIC, CONTROL_TOPIC, MAX_FRAMES, MAX_PACKET, Observer, Peer, RETAINED_TOPIC, field, packet, payload, publication


class Stream:
    def __init__(self, data=b"", failures=()):
        self.data = data
        self.failures = deque(failures)
        self.sent = []
        self.closed = False

    def recv(self, count):
        if self.failures:
            raise self.failures.popleft()
        value, self.data = self.data[:min(count, 7)], self.data[min(count, 7):]
        return value

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, seconds):
        self.timeout = seconds

    def close(self):
        self.closed = True


def peer(data=b"", failures=()):
    value = Peer.__new__(Peer)
    value.stream = Stream(data, failures)
    value.deadline = float("inf")
    value.pending = []
    value.identifier = 0
    return value


class WireObserver(unittest.TestCase):
    def test_fragmented_binary_publication_and_ack(self):
        body = field(BYTES_TOPIC) + b"\0\x05" + payload(2)
        value = peer(packet(0x32, body))
        self.assertEqual(value.message(), (BYTES_TOPIC, 1, False, payload(2)))
        self.assertEqual(value.stream.sent, [b"\x40\x02\0\x05"])

    def test_replay_before_suback_is_preserved(self):
        body = field(RETAINED_TOPIC) + b"\0\x05" + payload(3)
        value = peer(packet(0x33, body) + packet(0x90, b"\0\x01\x01"))
        value.subscribe(RETAINED_TOPIC)
        self.assertEqual(value.message(), (RETAINED_TOPIC, 1, True, payload(3)))

    def test_wrong_suback_or_identifier_is_rejected(self):
        for body in (b"\0\x01\x80", b"\0\x02\x01", b"\0\x01\x02"):
            with self.assertRaises(ValueError):
                peer(packet(0x90, body)).subscribe(RETAINED_TOPIC)

    def test_noncanonical_or_overlarge_frame_refused(self):
        for data in (b"\x30\x80\0", b"\x30\xff\xff\xff\xff", b"\x30\x80\x20"):
            with self.assertRaises(ValueError):
                peer(data).receive(time.monotonic() + 1)
        with self.assertRaises(ValueError):
            packet(0x30, b"x" * MAX_PACKET)

    def test_eof_is_not_absence(self):
        with self.assertRaises(EOFError):
            peer().assert_no_replay()
        with self.assertRaises(EOFError):
            peer(b"\x30\x01").receive(time.monotonic() + 1)

    def test_absence_requires_a_live_ping_and_no_pending_replay(self):
        value = peer(b"\xd0\0", failures=[socket.timeout()])
        value.assert_no_replay()
        self.assertEqual(value.stream.sent, [b"\xc0\0"])
        with self.assertRaises(EOFError):
            peer(failures=[socket.timeout()]).assert_no_replay()

    def test_late_replay_during_ping_vetoes_absence(self):
        body = field(RETAINED_TOPIC) + b"\0\x05" + payload(3)
        value = peer(packet(0x33, body) + b"\xd0\0", failures=[socket.timeout()])
        with self.assertRaises(ValueError):
            value.assert_no_replay()

    def test_immediate_packet_vetoes_absence(self):
        with self.assertRaises(ValueError):
            peer(b"\x30").assert_no_replay()

    def test_publication_flags_lengths_and_identifiers(self):
        for header, body in ((0x36, field(BYTES_TOPIC)), (0x34, field(BYTES_TOPIC)),
                             (0x38, field(BYTES_TOPIC)), (0x32, field(BYTES_TOPIC) + b"\0\0"),
                             (0x30, b"\0\x10x"), (0x30, b"\0\0")):
            with self.assertRaises(ValueError):
                publication(header, body)

    def test_global_deadline_bounds_operations(self):
        value = peer()
        value.deadline = time.monotonic() - 1
        with self.assertRaises(TimeoutError):
            value.send(0xc0)
        with self.assertRaises(TimeoutError):
            value.exact(1, time.monotonic() + 10)
        self.assertEqual(value.stream.sent, [])

    def test_frame_queue_and_identifier_budgets(self):
        data = packet(0x30, field(BYTES_TOPIC) + b"x") * MAX_FRAMES
        with self.assertRaises(ValueError):
            peer(data).subscribe(BYTES_TOPIC)
        value = peer()
        value.identifier = 65535
        with self.assertRaises(ValueError):
            value.next_id()

    def test_confirmation_is_qos1_with_exact_sequence(self):
        value = peer(b"\x40\x02\0\x01")
        value.confirm(3)
        self.assertEqual(value.stream.sent, [packet(0x32, field(CONTROL_TOPIC) + b"\0\x01\x03")])

    def test_wrong_loopback_bytes_or_retain_flag_vetoes(self):
        observer = Observer.__new__(Observer)
        observer.results = []
        for data in ((BYTES_TOPIC, 1, False, payload(0)), (BYTES_TOPIC, 0, True, payload(0)),
                     (BYTES_TOPIC, 0, False, b"bad")):
            with patch.object(Peer, "message", return_value=data):
                observer.base = peer()
                with self.assertRaises(ValueError):
                    observer.event("E01_LOOPBACK_PASS qos=0 bytes=1024")
        self.assertEqual(observer.results, [])

    def test_completeness_requires_all_six_wire_results_in_order(self):
        observer = Observer.__new__(Observer)
        observer.results = [*(f"WIRE_LOOPBACK_QOS{q}_1024_PASS" for q in range(3)),
                            *(f"WIRE_RETAINED_{s}_PASS" for s in (3, 4, 5))]
        self.assertTrue(observer.complete())
        for index in range(6):
            old = observer.results[:]
            observer.results.pop(index)
            self.assertFalse(observer.complete())
            observer.results = old

    def test_wrong_replay_bytes_version_or_retain_never_confirms(self):
        observer = Observer.__new__(Observer)
        observer.arguments = ("synthetic", 28883, None, "synthetic-user", "synthetic-password")
        observer.deadline = float("inf")
        observer.results = []
        for message in ((RETAINED_TOPIC, 1, False, payload(4)),
                        (RETAINED_TOPIC, 1, True, payload(3)),
                        (RETAINED_TOPIC, 1, True, b"bad")):
            fake = Mock(spec=Peer)
            fake.message.return_value = message
            with patch("retained_observer.Peer", return_value=fake):
                with self.assertRaises(ValueError):
                    observer.event("E01_RETAINED_STORED version=2 bytes=1024")
            fake.confirm.assert_not_called()
            fake.close.assert_called_once()
        self.assertEqual(observer.results, [])

    def test_failed_absence_never_confirms_delete(self):
        observer = Observer.__new__(Observer)
        observer.arguments = ("synthetic", 28883, None, "synthetic-user", "synthetic-password")
        observer.deadline = float("inf")
        observer.results = []
        fake = Mock(spec=Peer)
        fake.assert_no_replay.side_effect = EOFError("synthetic closed connection")
        with patch("retained_observer.Peer", return_value=fake):
            with self.assertRaises(EOFError):
                observer.event("E01_RETAINED_DELETED")
        fake.confirm.assert_not_called()
        fake.close.assert_called_once()
        self.assertEqual(observer.results, [])


if __name__ == "__main__":
    unittest.main()
