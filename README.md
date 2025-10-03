# Virtual Sensor Hub

This is a multi-threaded C program that simulates sensors, produces time-stamped samples, computes moving averages and emits alerts. It is designed as a software-only demo of embedded/IoT-oriented C development. It is a compact, testable C project that demonstrates systems-oriented skills relevant to embedded/IoT software such as concurrency, deterministic sampling, simple protocol framing, log-based verification and a small test harness. No hardware required.

## Key files
- `src/main.c` - program entry, duration handling, shutdown logic
- `src/sensor.c`, `sensor.h` - deterministic sensor threads
- `src/hub.c`, `hub.h` - logging, in-memory queue, processor (moving average + alerts)
- `Makefile` - one-command build (make)
- `data/hub.log` - runtime outputs
- `tools/check_log.py` - Python validator for data/hub.log
- `tests/run_tests.sh` — orchestrated test harness (runs app + validator)


## Design
- **Sensor threads (`sensor.c`)**  
  Each sensor (TEMP, HUM, PRESS) runs in its own thread and produces deterministic sample sequences at a configured interval. Determinism enables reproducible runs and stable automated checks.

- **Submission & queue (`hub.c`)**  
  `hub_submit_sample()` enqueues incoming samples into a fixed-size circular queue and immediately logs a `SAMPLE|...` line to `data/hub.log`. Mutex + condition variable coordinate producer/consumer access.

- **Processor thread (`hub.c`)**  
  A separate processor consumes queued samples, maintains a sliding moving-average window per sensor (configurable window size) and writes `ALERT|...|THRESHOLD_EXCEEDED` lines when a windowed average crosses a threshold.

- **Logging & verification**  
  All samples and alerts are appended to `data/hub.log` (human-readable framed lines). A Python validator (`tools/check_log.py`) inspects the log to verify expected sample counts and alerts for automated testing.

## Prerequisites
Run in **WSL2 (Ubuntu)** or any Linux environment with:
```bash
sudo apt update
sudo apt install -y build-essential make gdb python3
```

## Execution
To build, run from project root:
```bash
make
```

To run indefinitely (Ctrl+C to stop):
```bash
./sensorhub
```

To run for a fixed duration:
```bash
./sensorhub --test-duration 8   # run 8 seconds then exit
```

The program writes trace lines to data/hub.log (SAMPLE and ALERT framed records).

## Test Harness
Run this automated test after building:
```bash
./tests/run_tests.sh          # default duration 6s
# or
./tests/run_tests.sh 8        # specify duration in seconds
```