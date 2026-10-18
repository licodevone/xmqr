#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P227J contracts: binary provenance hashing stays bounded and byte exact."""
import ast
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_phase6_alias_reason as alias
import verify_phase6_shared_will as shared
import verify_phase6_vbi as vbi


class GuardedStream:
    """No readall/getbuffer shortcut; all input here is a tiny synthetic value."""
    def __init__(self, value, fail=False):
        self.value = value
        self.position = 0
        self.buffers = []
        self.closed = False
        self.fail = fail

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def readable(self):
        return True

    def read(self, *_):
        raise AssertionError('whole-file reads are forbidden by the contract')

    def readinto(self, buffer):
        if not 0 < len(buffer) <= 262_144:
            raise AssertionError('digest buffer exceeds fixed 256KiB bound')
        self.buffers.append(len(buffer))
        if self.fail:
            raise OSError(5, 'synthetic owned reader failure')
        count = min(len(buffer), len(self.value) - self.position, 1024)
        buffer[:count] = self.value[self.position:self.position + count]
        self.position += count
        return count


class BinaryDigestContracts(unittest.TestCase):
    def test_known_sha256_vectors_match_real_small_files(self):
        vectors = [
            (b'', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
            (b'abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'),
        ]
        with tempfile.TemporaryDirectory(prefix='xmqr-p227j-contract-', dir='/var/tmp') as temporary:
            path = Path(temporary) / 'owned-input'
            for value, expected in vectors:
                path.write_bytes(value)
                with patch.object(Path, 'read_bytes', side_effect=AssertionError('readall forbidden')):
                    self.assertEqual(vbi.binary_digest(path), expected)

    def test_guarded_stream_matches_independent_small_reference_and_is_closed(self):
        value = bytes(range(256)) * 19 + b'owned-finite-input'
        expected = hashlib.sha256(value).hexdigest()  # Small oracle, never an ELF.
        stream = GuardedStream(value)
        with patch.object(Path, 'open', return_value=stream) as opened, \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('readall forbidden')):
            self.assertEqual(vbi.binary_digest(Path('owned-input')), expected)
        opened.assert_called_once_with('rb')
        self.assertTrue(stream.closed)
        self.assertEqual(stream.position, len(value))
        self.assertGreater(len(stream.buffers), 2)
        self.assertTrue(all(0 < size <= 262_144 for size in stream.buffers))

    def test_io_failure_is_not_a_digest_and_still_closes_stream(self):
        stream = GuardedStream(b'owned', fail=True)
        with patch.object(Path, 'open', return_value=stream):
            with self.assertRaises(OSError) as failure:
                vbi.binary_digest(Path('owned-input'))
        self.assertEqual(failure.exception.errno, 5)
        self.assertTrue(stream.closed)

    def test_all_three_binary_hash_sites_use_the_shared_stream_helper(self):
        for module in (vbi, alias, shared):
            with self.subTest(module=module.__name__):
                self.assertIs(module.binary_digest, vbi.binary_digest)
                tree = ast.parse(Path(module.__file__).read_text(encoding='utf-8'))
                sites = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Subscript)
                                 and isinstance(target.slice, ast.Constant)
                                 and target.slice.value == 'broker_binary_sha256'
                                 for target in node.targets)]
                self.assertEqual(len(sites), 1)
                self.assertIsInstance(sites[0].value, ast.Call)
                self.assertIsInstance(sites[0].value.func, ast.Name)
                self.assertEqual(sites[0].value.func.id, 'binary_digest')
                self.assertEqual(ast.dump(sites[0].value.args[0]), ast.dump(ast.Name(id='binary', ctx=ast.Load())))


if __name__ == '__main__':
    unittest.main()
