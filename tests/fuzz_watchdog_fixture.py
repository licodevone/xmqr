#!/usr/bin/env python3
"""Synthetic subprocess fixture for P90 watchdog tests; not broker code."""
import json
import os
import sys
import time

seed = int(os.environ["XMQR_FUZZ_SEED"])
if seed == 2:
    time.sleep(8)
elif seed == 3:
    allocated = bytearray(64 * 1024 * 1024)
    time.sleep(8)
elif seed == 4:
    raise SystemExit(19)
else:
    time.sleep(0.1)
target = sys.argv[1].split("::")[-1].removeprefix("fuzz_").removesuffix("_campaign")
print("XMQR_FUZZ_RESULT " + json.dumps({"target": target, "seed": seed, "cases": 1,
      "accepted": 1, "max_input_bytes": 1, "elapsed_ms": 100}), flush=True)
