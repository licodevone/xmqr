# SPDX-License-Identifier: MIT
"""Closed, bounded serial transcript collector. It does not prove wire MQTT."""
import re
import time

MAX_LINE_BYTES = 512
MAX_TOTAL_BYTES = 65536
MAX_MARKERS = 128
BOOT = "E01_BOOT fixture=0.1.0 payload=1024"
MILESTONES = (
    BOOT, "E01_WIFI_UP", "E01_SNTP_SYNC", "E01_MTLS_CONNECTED",
    *(f"E01_LOOPBACK_PASS qos={q} bytes=1024" for q in range(3)),
    "E01_INITIAL_SLICE_PASS", "E01_STOP",
)
RETAINED_MILESTONES = (*MILESTONES[:-2],
    "E01_RETAINED_STORED version=1 bytes=1024",
    "E01_RETAINED_REPLAY_PASS version=1 bytes=1024",
    "E01_RETAINED_STORED version=2 bytes=1024",
    "E01_RETAINED_REPLAY_PASS version=2 bytes=1024",
    "E01_RETAINED_DELETED", "E01_RETAINED_DELETE_PASS", *MILESTONES[-2:])
ALL_MILESTONES = frozenset((*MILESTONES, *RETAINED_MILESTONES))
CAMPAIGN_MILESTONES = (*MILESTONES[:3], "P85_CONNECTED", "P85_WILL_READY",
    "P85_WIFI_DOWN", "P85_WIFI_RECONNECT_PASS", "P85_RESTART_READY",
    "P85_BROKER_RECONNECT_PASS", "P85_RESTART_DELETE", "P85_DUPLICATE_READY",
    "P85_DUPLICATE_PASS", "P85_EXTERNAL_SUB_READY", "P85_EXTERNAL_PUB_READY",
    "P85_EXTERNAL_PASS", "P85_NEGATIVE_CA_PASS", "P85_NEGATIVE_PASSWORD_PASS",
    "P85_NEGATIVE_ACL_PASS", "P85_SAN_READY", "P85_SAN_ARMED",
    "P85_NEGATIVE_SAN_PASS", "P85_SAN_RESTORED", "P85_FINAL_PASS", "E01_STOP")
ALL_MILESTONES = frozenset((*ALL_MILESTONES, *CAMPAIGN_MILESTONES))
FAIL_STAGES = frozenset((
    "PERIPHERALS", "EVENT_LOOP", "WIFI_OBSERVER", "WIFI_DRIVER", "SSID_LENGTH",
    "PASSWORD_LENGTH", "WIFI_CONFIG", "WIFI_START", "WIFI_START_TIMEOUT",
    "WIFI_SCAN_START", "WIFI_SCAN_TIMEOUT", "WIFI_SCAN_RESULTS",
    "WIFI_TARGET_NOT_FOUND_24GHZ", "WIFI_CONNECT", "WIFI_ASSOCIATION_TIMEOUT",
    "WIFI_IP_TIMEOUT", "SNTP_START", "SNTP_TIMEOUT", "MQTT_CREATE",
    "MQTT_CONNECT_TIMEOUT", "SUBSCRIBE", "SUBSCRIBE_TIMEOUT", "PUBLISH",
    "PUBLISH_ACK_TIMEOUT", "BYTES_OR_DELIVERY", "WIFI_STOP",
    "CONTROL_SUBSCRIBE", "CONTROL_SUBSCRIBE_TIMEOUT", "RETAINED_PUBLISH",
    "RETAINED_ACK_TIMEOUT", "OBSERVER_CONFIRM_TIMEOUT", "RETAINED_DELETE",
    "P85_MQTT_CREATE", "P85_RECONNECT_LIMIT", "P85_SUBSCRIBE", "P85_SUBSCRIBE_TIMEOUT",
    "P85_PUBLISH", "P85_ACK_TIMEOUT", "P85_CONFIRM_TIMEOUT", "P85_MEMORY_LOW",
    "P85_NEGATIVE_NOT_REJECTED", "P85_WIFI_DISCONNECT", "P85_WIFI_DOWN_TIMEOUT",
    "P85_WIFI_RECONNECT", "P85_WIFI_RECONNECT_LIMIT", "P85_RESTART_NOT_OBSERVED",
    "P85_DUPLICATE_BYTES", "P85_EXTERNAL_BYTES", "P85_DENIED_SEND",
    "P85_ACL_NOT_REJECTED", "P85_MEMORY_DRIFT",
))
AUTH_METHODS = frozenset((
    "None", "WEP", "WPA", "WPA2Personal", "WPAWPA2Personal", "WPA2Enterprise",
    "WPA3Personal", "WPA2WPA3Personal", "WAPIPersonal",
))


def marker(raw):
    """No lossy decoding, whitespace/prefix tolerance or arbitrary fields."""
    if len(raw) > MAX_LINE_BYTES or not raw.endswith(b"\n"):
        return None
    try:
        line = raw[:-1].removesuffix(b"\r").decode("ascii")
    except UnicodeDecodeError:
        return None
    if line in ALL_MILESTONES or line == "E01_WIFI_ASSOCIATED":
        return line
    metric = re.fullmatch(r"P85_MEMORY stage=(idle|wifi|restart|final) largest_probe=([0-9]{1,6})", line)
    if metric and 0 <= int(metric[2]) <= 196608 and int(metric[2]) % 4096 == 0 and str(int(metric[2])) == metric[2]:
        return line
    metric = re.fullmatch(r"P85_TIME kind=(wifi|broker) milliseconds=([0-9]{1,5})", line)
    if metric and 0 <= int(metric[2]) <= 60000 and str(int(metric[2])) == metric[2]:
        return line
    if line.startswith("E01_FAIL stage=") and line[15:] in FAIL_STAGES:
        return line
    if line.startswith("E01_WIFI_AP_AUTH method=") and line[24:] in AUTH_METHODS:
        return line
    found = re.fullmatch(r"E01_WIFI_AP_FOUND channel=([1-9]|1[0-4]) rssi=(0|-[1-9][0-9]?|-1[01][0-9]|-12[0-7])", line)
    if found:
        return line
    reason = re.fullmatch(r"E01_WIFI_DISCONNECTED reason=([0-9]{1,5})", line)
    if reason and 0 <= int(reason[1]) <= 65535 and str(int(reason[1])) == reason[1]:
        return line
    return None


class Transcript:
    def __init__(self, milestones=MILESTONES):
        if milestones not in (MILESTONES, RETAINED_MILESTONES, CAMPAIGN_MILESTONES):
            raise ValueError("unknown campaign")
        self.milestones = milestones
        self.markers = []
        self.violations = set()
        self.discarded_lines = 0
        self.total_bytes = 0
        self.progress = 0
        self.failed = False
        self.stopped = False

    def accept(self, raw):
        if len(raw) > MAX_LINE_BYTES:
            self.violations.add("LINE_LIMIT")
            return None
        if not raw.endswith(b"\n"):
            self.violations.add("PARTIAL_LINE")
            return None
        line = marker(raw)
        if line is None:
            self.discarded_lines += 1
            if raw.startswith((b"E01_", b"P85_")):
                self.violations.add("INVALID_MARKER")
            return None
        if len(self.markers) >= MAX_MARKERS:
            self.violations.add("MARKER_LIMIT")
            return None
        self.markers.append(line)
        if self.stopped:
            self.violations.add("AFTER_STOP")
        if line == BOOT and self.progress:
            self.violations.add("REBOOT")
        if line.startswith("E01_FAIL stage="):
            self.failed = True
            if not self.progress:
                self.violations.add("FAIL_BEFORE_BOOT")
        elif line in ALL_MILESTONES:
            if line == "E01_STOP":
                self.stopped = True
                if self.failed:
                    return line
            if self.progress >= len(self.milestones) or line != self.milestones[self.progress]:
                self.violations.add("MILESTONE_ORDER")
            else:
                self.progress += 1
        elif not self.progress:
            self.violations.add("DIAGNOSTIC_BEFORE_BOOT")
        return line

    def result(self):
        if self.violations:
            return "FAIL_TRANSCRIPT"
        if self.failed:
            return "FAIL_INITIAL_SLICE"
        if self.stopped and self.progress == len(self.milestones):
            if self.milestones == CAMPAIGN_MILESTONES:
                return "PASS_PHYSICAL_CAMPAIGN"
            return "PASS_RETAINED_SLICE" if self.milestones == RETAINED_MILESTONES else "PASS_INITIAL_SLICE"
        return "FAIL_INCOMPLETE"

    def summary(self):
        return dict(markers=list(self.markers), result=self.result(),
                    violations=sorted(self.violations), discarded_lines=self.discarded_lines,
                    total_bytes=self.total_bytes, phase2_closed=False)


def collect(stream, seconds=180, clock=time.monotonic, emit=None, milestones=MILESTONES):
    if type(seconds) is not int or not 1 <= seconds <= 180:
        raise ValueError("serial deadline must be 1..180 seconds")
    transcript = Transcript(milestones)
    buffer = bytearray()
    dropping = False
    stopped_at = None
    deadline = clock() + seconds
    while clock() < deadline:
        if stopped_at is not None and clock() - stopped_at >= 1:
            break
        remaining = MAX_TOTAL_BYTES - transcript.total_bytes
        if remaining <= 0:
            transcript.violations.add("BYTE_LIMIT")
            break
        requested = min(128, remaining)
        chunk = stream.read(requested)
        if not isinstance(chunk, bytes) or len(chunk) > requested:
            transcript.violations.add("READ_CONTRACT")
            break
        transcript.total_bytes += len(chunk)
        for byte in chunk:
            if dropping:
                if byte == 10:
                    dropping = False
                continue
            buffer.append(byte)
            if len(buffer) > MAX_LINE_BYTES:
                transcript.violations.add("LINE_LIMIT")
                dropping = byte != 10
                buffer.clear()
                continue
            if byte == 10:
                line = transcript.accept(bytes(buffer))
                buffer.clear()
                if line is not None and emit:
                    emit(line)
        # A bounded tail also catches contradictory markers in subsequent reads.
        if transcript.stopped and stopped_at is None:
            stopped_at = clock()
        if "MARKER_LIMIT" in transcript.violations:
            break
    if buffer:
        transcript.violations.add("PARTIAL_LINE")
    if not transcript.stopped:
        transcript.violations.add("TIMEOUT")
    return transcript
