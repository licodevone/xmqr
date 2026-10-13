"""Real, test-owned subprocess verification for the bounded P90 driver."""
from argparse import Namespace
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("p90_driver", ROOT / "scripts" / "run_fuzz.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


@unittest.skipUnless(sys.platform == "linux", "Linux process-group watchdog")
class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory(prefix="xmqr-fuzz-watchdog-")
        self.binary = Path(self.private.name) / "fixture"
        shutil.copyfile(ROOT / "tests" / "fuzz_watchdog_fixture.py", self.binary)
        self.binary.chmod(0o700)
        destination = ROOT / "dist" / "fuzz"
        destination.mkdir(parents=True, exist_ok=True)
        self.logs = tempfile.TemporaryDirectory(prefix="watchdog-", dir=destination)
        self.args = Namespace(iterations=1, state_iterations=1, router_iterations=1,
                              timeout=5, rss_mib=32)

    def tearDown(self):
        self.logs.cleanup()
        self.private.cleanup()

    def check(self, seed, status):
        result = driver.run_one(self.binary, "frame", seed, self.args, Path(self.logs.name))
        self.assertEqual(result["status"], status)
        self.assertLess(result["elapsed_seconds"], self.args.timeout + 1)
        if status == "PASS":
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["counts"]["cases"], 1)
        else:
            self.assertNotEqual(result["exit_code"], 0)

    def test_normal_completed_target(self):
        self.check(1, "PASS")

    def test_hanging_target_is_killed_at_deadline(self):
        self.args.timeout = 1
        self.check(2, "TIMEOUT")

    def test_over_budget_rss_target_is_killed(self):
        self.check(3, "RSS_LIMIT")

    def test_test_failure_is_not_classified_pass(self):
        self.check(4, "FAIL")


if __name__ == "__main__":
    unittest.main()
