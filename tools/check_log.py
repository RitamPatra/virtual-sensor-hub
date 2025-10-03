#!/usr/bin/env python3
"""
Simple log checker for virtual-sensor-hub. Meant to be called by run_tests.sh, but can also be directly used.

Usage:
    python3 tools/check_log.py data/hub.log [duration in seconds]

Checks:
1. There are an expected minimum number of SAMPLE lines per sensor
   based on duration and sampling rates.
2. If the run duration is long enough to fill the moving-average window
   for TEMP, ensures at least one TEMP ALERT was produced.
Returns 0 on success, non-zero on failure.
"""

import sys
import math

if len(sys.argv) < 3:
    print("Usage: python3 tools/check_log.py <logfile> <duration_seconds>", file=sys.stderr)
    sys.exit(2)

logfile = sys.argv[1]
try:
    duration_s = float(sys.argv[2])
except ValueError:
    print("Invalid duration_seconds", file=sys.stderr)
    sys.exit(2)

# sensor sampling rates
RATES_MS = {
    "TEMP": 500,
    "HUM": 700,
    "PRESS": 1200
}

# moving average window size
WINDOW_SIZE = 5

# calculate expected minimal sample counts: floor(duration_ms / rate_ms) - 1 (allow minor timing variance)
duration_ms = int(duration_s * 1000)
expected = {}
for k, ms in RATES_MS.items():
    raw = duration_ms // ms
    expected[k] = max(1, raw - 1)  # require at least (raw-1) samples, can't be less than 1

# counts
sample_counts = {"TEMP":0, "HUM":0, "PRESS":0}
alert_counts = {"TEMP":0, "HUM":0, "PRESS":0}
total_lines = 0

try:
    with open(logfile, "r") as f:
        for line in f:
            total_lines += 1
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if parts[0] == "SAMPLE" and len(parts) >= 4:
                typ = parts[1]
                if typ in sample_counts:
                    sample_counts[typ] += 1
            elif parts[0] == "ALERT" and len(parts) >= 5:
                typ = parts[1]
                if typ in alert_counts:
                    alert_counts[typ] += 1
except FileNotFoundError:
    print(f"Log file not found: {logfile}", file=sys.stderr)
    sys.exit(3)
except Exception as e:
    print("Error reading log:", e, file=sys.stderr)
    sys.exit(4)

# report
print(f"Log: {logfile}")
print(f"Duration (s): {duration_s:.1f}, duration_ms: {duration_ms}")
print(f"Total log lines: {total_lines}")
print("")
print("Sample counts:")
for k in ("TEMP","HUM","PRESS"):
    print(f"  {k}: {sample_counts[k]}  (expected >= {expected[k]})")
print("")
print("Alert counts:")
for k in ("TEMP","HUM","PRESS"):
    print(f"  {k}: {alert_counts[k]}")

# Check sample counts (check 1)
ok = True
for k in ("TEMP","HUM","PRESS"):
    if sample_counts[k] < expected[k]:
        print(f"ERROR: {k} sample count too low: got {sample_counts[k]}, expected >= {expected[k]}", file=sys.stderr)
        ok = False

# If duration long enough to fill window for TEMP, require at least one TEMP alert (check 2)
min_ms_for_window_temp = WINDOW_SIZE * RATES_MS["TEMP"]
if duration_ms >= min_ms_for_window_temp:
    if alert_counts["TEMP"] < 1:
        print(f"ERROR: No TEMP ALERT found, but duration {duration_ms}ms >= {min_ms_for_window_temp}ms (window size).", file=sys.stderr)
        ok = False
    else:
        print(f"OK: TEMP ALERTs found: {alert_counts['TEMP']}")

# Final result
if not ok:
    print("\nCHECK FAILED", file=sys.stderr)
    sys.exit(1)

print("\nCHECK PASSED")
sys.exit(0)