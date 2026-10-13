#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P91 independent MQTT3.1.1 wire vectors; explicit owned Linux broker only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import time

sys.dont_write_bytecode = True
import benchmark_pressure as pressure

f = pressure.f


def connected(broker, client_id=b'wire-normal', flags=2, keepalive=30, header=0x10, suffix=b''):
    client = f.WireClient.__new__(f.WireClient)
    client.socket = socket.create_connection(('127.0.0.1', broker.port), timeout=4)
    client.send(header, f.text('MQTT') + bytes([4, flags]) + keepalive.to_bytes(2, 'big')
                + len(client_id).to_bytes(2, 'big') + client_id + suffix)
    return client


def closed(client):
    try:
        if client.socket.recv(1) != b'':
            raise AssertionError('malformed packet was not closed without a success response')
    except ConnectionResetError:
        pass


def cases(broker):
    results = []
    def perform(name, clauses, operation):
        began = time.monotonic()
        try:
            operation()
            item = dict(scenario=name, clauses=clauses, status='PASS')
        except Exception as failure:
            item = dict(scenario=name, clauses=clauses, status='FAIL', error_type=type(failure).__name__,
                        error=str(failure) if isinstance(failure, AssertionError) else 'bounded wire operation failed')
        item['seconds'] = round(time.monotonic() - began, 3)
        results.append(item)
        print(json.dumps(item), flush=True)

    def refused_id(clean):
        with connected(broker, b'', flags=2 if clean else 0) as client:
            if client.receive() != (0x20, b'\0\2'):
                raise AssertionError('empty ClientID needs identifier-rejected CONNACK under XMQR policy')
            closed(client)
    for clean in (False, True):
        perform(f'empty_client_id_clean_{clean}', ['MQTT-3.1.3-7', 'MQTT-3.1.3-8', 'MQTT-3.1.3-9'],
                lambda clean=clean: refused_id(clean))

    def invalid_connect(identifier, flags=2, header=0x10):
        with connected(broker, identifier, flags=flags, header=header) as client:
            closed(client)
    for name, identifier, flags, header, clauses in [
        ('connect_reserved_flag', b'valid', 3, 0x10, ['MQTT-3.1.2-3']),
        ('connect_invalid_fixed_flags', b'valid', 2, 0x11, ['MQTT-2.2.2-2']),
        ('password_without_username', b'valid', 0x42, 0x10, ['MQTT-3.1.2-22']),
        ('will_retain_without_will', b'valid', 0x22, 0x10, ['MQTT-3.1.2-15']),
        ('will_reserved_qos', b'valid', 0x1e, 0x10, ['MQTT-3.1.2-14']),
        ('client_id_null_utf8', b'bad\0id', 2, 0x10, ['MQTT-1.5.3-2']),
        ('client_id_invalid_utf8', b'bad\xffid', 2, 0x10, ['MQTT-1.5.3-1'])]:
        perform(name, clauses, lambda identifier=identifier, flags=flags, header=header:
                invalid_connect(identifier, flags, header))

    def malformed_after_connect(header, body):
        with connected(broker) as client:
            if client.receive() != (0x20, b'\0\0'):
                raise AssertionError('valid setup CONNECT failed')
            client.send(header, body)
            closed(client)
    for name, header, body, clauses in [
        ('qos0_duplicate_flag', 0x38, f.text('wire/value') + b'v', ['MQTT-3.3.1-2']),
        ('publish_reserved_qos', 0x36, f.text('wire/value') + b'\0\1v', ['MQTT-3.3.1-4']),
        ('publish_zero_identifier', 0x32, f.text('wire/value') + b'\0\0v', ['MQTT-2.3.1-1']),
        ('subscribe_zero_identifier', 0x82, b'\0\0' + f.text('wire/#') + b'\1', ['MQTT-2.3.1-1']),
        ('puback_zero_identifier', 0x40, b'\0\0', ['MQTT-2.3.1-1']),
        ('topic_null_utf8', 0x30, b'\0\3a\0b' + b'v', ['MQTT-1.5.3-2']),
        ('topic_invalid_utf8', 0x30, b'\0\2a\xff' + b'v', ['MQTT-1.5.3-1']),
        ('subscribe_bad_filter', 0x82, b'\0\1' + f.text('wire/#/bad') + b'\1', ['MQTT-4.7.1-2'])]:
        perform(name, clauses, lambda header=header, body=body: malformed_after_connect(header, body))

    def keepalive_close():
        with connected(broker, keepalive=1) as client:
            if client.receive() != (0x20, b'\0\0'):
                raise AssertionError('keepalive setup refused')
            began = time.monotonic()
            closed(client)
            elapsed = time.monotonic() - began
            if not 1.35 <= elapsed <= 3.2:
                raise AssertionError('keepalive close outside declared 1.5x/deadline tolerance')
    perform('keepalive_one_second_timeout', ['MQTT-3.1.2-24'], keepalive_close)

    def fragmented_and_concatenated():
        client = f.WireClient.__new__(f.WireClient)
        client.socket = socket.create_connection(('127.0.0.1', broker.port), timeout=4)
        with client:
            body = f.text('MQTT') + b'\4\2\0\30' + f.text('wire-fragment')
            packet = bytes([0x10, len(body)]) + body
            for offset in range(0, len(packet), 3):
                client.socket.sendall(packet[offset:offset + 3])
            if client.receive() != (0x20, b'\0\0'):
                raise AssertionError('fragmented CONNECT refused')
            client.socket.sendall(b'\xc0\0\xc0\0')
            if client.receive() != (0xd0, b'') or client.receive() != (0xd0, b''):
                raise AssertionError('concatenated PINGREQ framing lost')
            client.send(0xe0)
    perform('fragmented_connect_concatenated_ping', ['MQTT-2.2.3', 'MQTT-3.12.4-1'], fragmented_and_concatenated)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--label', required=True, choices=['baseline', 'candidate'])
    args = parser.parse_args()
    if sys.platform != 'linux' or args.report.exists() or args.report.is_symlink():
        parser.error('Linux and new report required')
    binary = args.broker.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='xmqr-p91-wire-', dir='/tmp') as temporary:
        broker = pressure.Broker(temporary, binary, None)
        try:
            broker.start()
            results = cases(broker)
        finally:
            broker.shutdown()
    report = dict(schema_version=1, label=args.label,
                  status='PASS' if all(item['status'] == 'PASS' for item in results) else 'FAIL',
                  broker_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scenarios=results,
                  completed_utc=datetime.now(timezone.utc).isoformat(),
                  limitations=['wire fixture is independent, not a complete library or exhaustive conformance suite'])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
