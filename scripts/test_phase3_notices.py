# SPDX-License-Identifier: MIT
"""Synthetic notice payload negatives; no Docker/WSL/operator credentials."""
import io
import json
import tarfile
import unittest
from unittest.mock import patch

import verify_phase3_notices as qa


class NoticePayloadTests(unittest.TestCase):
    def setUp(self):
        self.originals = {"sample-1/LICENSE-MIT": b"original third-party MIT text\n"}
        self.manifest = {"schema_version": 1, "packages": [{"name": "sample", "version": "1", "files": [
            {"path": "sample-1/LICENSE-MIT", "sha256": qa.sha(self.originals["sample-1/LICENSE-MIT"]), "size": 30}]}]}
        self.content = {"LICENSE": b"own MIT\n", "copyright": b"own MIT\n",
                        "third-party/manifest.json": json.dumps(self.manifest).encode(),
                        "third-party/sample-1/LICENSE-MIT": self.originals["sample-1/LICENSE-MIT"]}

    def verify(self):
        return qa.verify_payload(self.content, self.manifest, self.originals, b"own MIT\n", deb=True)

    def test_original_text_exact_and_mit_copyright_pass(self):
        self.assertEqual(self.verify()["status"], "PASS")

    def test_tampered_text_cannot_be_hidden_by_same_packaged_manifest(self):
        self.content["third-party/sample-1/LICENSE-MIT"] += b"tampered"
        with self.assertRaisesRegex(ValueError, "SHA"):
            self.verify()

    def test_missing_dependency_license_fails(self):
        del self.content["third-party/sample-1/LICENSE-MIT"]
        with self.assertRaisesRegex(ValueError, "missing"):
            self.verify()

    def test_extra_unreviewed_notice_fails(self):
        self.content["third-party/unreviewed/NOTICE"] = b"unknown"
        with self.assertRaisesRegex(ValueError, "extra"):
            self.verify()

    def test_changed_manifest_cannot_replace_expected_source(self):
        self.content["third-party/manifest.json"] = b'{"schema_version":1,"packages":[]}'
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.verify()

    def test_mit_copyright_is_required_in_deb(self):
        del self.content["copyright"]
        with self.assertRaisesRegex(ValueError, "MIT"):
            self.verify()

    def test_own_mit_crlf_only_difference_passes_and_keeps_raw_hash(self):
        self.content["LICENSE"] = b"own MIT\r\n"
        self.content["copyright"] = b"own MIT\r\n"
        report = self.verify()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["own_mit_packaged_raw_sha256"]["LICENSE"], qa.sha(b"own MIT\r\n"))
        self.assertEqual(report["own_mit_canonical_lf_sha256"], qa.sha(b"own MIT\n"))
        self.assertNotEqual(report["own_mit_source_raw_sha256"], report["own_mit_packaged_raw_sha256"]["LICENSE"])

    def test_changed_own_copyright_terms_fail_even_with_crlf(self):
        for name in ["LICENSE", "copyright"]:
            with self.subTest(name=name):
                original = self.content[name]
                self.content[name] = b"changed own MIT terms/copyright\r\n"
                with self.assertRaisesRegex(ValueError, "MIT"):
                    self.verify()
                self.content[name] = original

    def test_third_party_eol_change_is_not_normalized(self):
        self.content["third-party/sample-1/LICENSE-MIT"] = self.originals["sample-1/LICENSE-MIT"].replace(b"\n", b"\r\n")
        with self.assertRaisesRegex(ValueError, "SHA"):
            self.verify()

    def archive(self, name, link=False, duplicate=False):
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode="w") as stream:
            for _ in range(2 if duplicate else 1):
                member = tarfile.TarInfo(name)
                if link:
                    member.type = tarfile.SYMTYPE
                    member.linkname = "/outside"
                else:
                    member.size = 1
                stream.addfile(member, None if link else io.BytesIO(b"x"))
        return result.getvalue()

    def test_tar_does_not_follow_symlinks(self):
        with self.assertRaisesRegex(ValueError, "regular"):
            qa.read_archive(self.archive("root/LICENSE", link=True), "root")

    def test_tar_traversal_and_duplicate_are_rejected(self):
        for name in ["root/../outside", "/root/LICENSE", "root\\LICENSE"]:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unsafe"):
                qa.read_archive(self.archive(name), "root")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            qa.read_archive(self.archive("root/LICENSE", duplicate=True), "root")

    def test_tar_regular_file_is_read_in_memory(self):
        self.assertEqual(qa.read_archive(self.archive("./root/LICENSE"), "root"), {"LICENSE": b"x"})

    def test_tar_aggregate_content_limit_is_enforced(self):
        with patch.object(qa, "CONTENT_LIMIT", 0), self.assertRaisesRegex(ValueError, "aggregate"):
            qa.read_archive(self.archive("root/LICENSE"), "root")

    def test_tar_member_count_limit_is_enforced(self):
        with patch.object(qa, "MEMBER_LIMIT", 0), self.assertRaisesRegex(ValueError, "count"):
            qa.read_archive(self.archive("root/LICENSE"), "root")


if __name__ == "__main__":
    unittest.main()
