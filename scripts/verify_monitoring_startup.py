# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Luis E. S. Pinheiro
"""P43 process-level invalid configuration checks; Windows and Unix supported.

Does not start a usable broker or bypass Unix storage requirements.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def verify(broker):
    cases = [
        ("yes", "127.0.0.1:9090", "MQTT_MONITOR_ENABLED must be true or false"),
        ("true", "127.0.0.1:0", "loopback address and nonzero port"),
        ("true", "0.0.0.0:9090", "loopback address and nonzero port"),
        ("true", "192.0.2.1:9090", "loopback address and nonzero port"),
        ("true", "[::]:9090", "loopback address and nonzero port"),
        ("false", "invalid-address", "invalid monitoring bind"),
    ]
    with tempfile.TemporaryDirectory(prefix="xmqr-p43-startup-") as directory:
        for index, (enabled, bind, expected) in enumerate(cases):
            state = Path(directory) / f"state-{index}"
            env = {k: v for k, v in os.environ.items() if not k.startswith("MQTT_")}
            env.update(MQTT_MODE="open-lab", MQTT_BIND="127.0.0.1:0",
                       MQTT_STATE_DIR=str(state), MQTT_MONITOR_ENABLED=enabled,
                       MQTT_MONITOR_BIND=bind, RUST_LOG="error")
            result = subprocess.run([str(broker)], env=env, capture_output=True, timeout=8)
            assert result.returncode != 0, "invalid configuration accepted"
            assert expected.encode() in result.stderr, "unexpected startup error"
            assert not state.exists(), "configuration failed only after touching state"
            print(f"PASS invalid configuration {index + 1}: early refusal; state untouched")
    print("6 process-level configuration cases PASS; MQTT/HTTP serving not tested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", type=Path, required=True)
    args = parser.parse_args()
    if not args.broker.is_file():
        parser.error("broker binary missing")
    verify(args.broker.resolve())
