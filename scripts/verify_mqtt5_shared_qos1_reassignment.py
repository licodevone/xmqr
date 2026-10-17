#!/usr/bin/env python3
"""P156: TCP QoS1 shared copy moves after its unacked member ends."""
import select
import tempfile

from verify_mqtt5_sessions import packet, start, stop
from verify_mqtt5_subscribe_options import connect, free_port
from verify_mqtt5_shared_durable import SHARED, TOPIC, publish, receive, subscribe


def main():
    with tempfile.TemporaryDirectory(prefix="xmqr-p156-") as state:
        port = free_port()
        broker = start(port, state)
        first = second = publisher = None
        try:
            first, _ = connect(port, b"p156-first")
            second, _ = connect(port, b"p156-second")
            publisher, _ = connect(port, b"p156-publisher")
            subscribe(first, SHARED, qos=1, identifier=7)
            subscribe(second, SHARED, qos=1, identifier=9)
            publish(publisher, b"unacked-shared", qos=1, packet_id=41)
            ready, _, _ = select.select([first, second], [], [], 4)
            assert len(ready) == 1, "one initial shared recipient expected"
            winner = ready[0]
            survivor = second if winner is first else first
            survivor_id = 9 if survivor is second else 7
            header, body = packet(winner)
            assert header >> 4 == 3 and (header >> 1) & 3 == 1
            assert TOPIC in body and body.endswith(b"unacked-shared")
            # Intentionally omit PUBACK: the selected temporary session ends.
            winner.sendall(b"\xe0\x00")
            winner.close()
            receive(survivor, b"unacked-shared", 1, survivor_id)
            assert not select.select([survivor], [], [], 0.2)[0], "duplicate shared copy"
        finally:
            for stream in (first, second, publisher):
                if stream is not None:
                    stream.close()
            stop(broker)
    print("P156_TCP_PASS unacked QoS1 moves once to surviving group member")


if __name__ == "__main__":
    main()
