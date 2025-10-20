# Virtual Sensor Hub

This is a multi-threaded C program that simulates sensors, produces time-stamped samples, computes moving averages and emits alerts. It is designed as a software-only demo of embedded/IoT-oriented C development. It is a compact, testable C project that demonstrates systems-oriented skills relevant to embedded/IoT software such as concurrency, deterministic sampling, simple protocol framing, log-based verification and a small test harness. No hardware required.

## Key files
- `src/main.c` - program entry, duration handling, shutdown logic
- `src/sensor.c`, `sensor.h` - deterministic sensor threads
- `src/hub.c`, `hub.h` - logging, in-memory queue, processor (moving average + alerts)
- `Makefile` - one-command build (make)
- `data/hub.log` - runtime outputs
- `tools/check_log.py` - Python validator for data/hub.log
- `tests/run_tests.sh` - orchestrated test harness (runs app + validator)
- `tools/parse_logs.py` - generates charts and a CSV summarizing the output


## Design
- **Sensor threads (`sensor.c`)**  
  Each sensor (TEMP, HUM, PRESS) runs in its own thread and produces deterministic sample sequences at a configured interval. Determinism enables reproducible runs and stable automated checks.

- **Submission & queue (`hub.c`)**  
  `hub_submit_sample()` enqueues incoming samples into a fixed-size circular queue and immediately logs a `SAMPLE|...` line to `data/hub.log`. Mutex + condition variable coordinate producer/consumer access.

- **Processor thread (`hub.c`)**  
  A separate processor consumes queued samples, maintains a sliding moving-average window per sensor (configurable window size) and writes `ALERT|...|THRESHOLD_EXCEEDED` lines when a windowed average crosses a threshold.

- **Logging & verification**  
  All samples and alerts are appended to `data/hub.log` (human-readable framed lines). A Python validator (`tools/check_log.py`) inspects the log to verify expected sample counts and alerts for automated testing.

- **Analysis & Visualizations**  
  The logs are analysed by `tools/parse_logs.py` and visualizations (histogram + timseries) are generated for all three sensors, along with a timeline of alerts and a CSV summarizing the sensor readings.

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

## Testing & Analysis
Run this automated test after building:
```bash
./tests/run_tests.sh          # default duration 6s
# or
./tests/run_tests.sh 8        # specify duration in seconds
```

Run this to perform the analysis after the log file has been generated:
```bash
python3 tools/parse_logs.py data/hub.log --outdir outputs --window 5
```

## Visualizations
The following are some sample outputs obtained after executing the program for 35 seconds.
| Histograms | Timeseries |
|:-:|:-:|
| ![Temperature Histogram](https://github.com/user-attachments/assets/0cca0a12-be54-4113-ba74-2908ce29846b) | ![Temperature Timeseries](https://github.com/user-attachments/assets/3d94f572-7b07-4e85-ac2a-6194163b431b) |
| ![Humidity Histogram](https://github.com/user-attachments/assets/d84cdae0-f63f-4438-9a3d-2fa937241607) | ![Humidity Timeseries](https://github.com/user-attachments/assets/ed9d9900-b7d7-4635-aab4-21ea25275e7b) |
| ![Pressure Histogram](https://github.com/user-attachments/assets/7cb4e5ce-7925-4258-8271-3fc43d604fc4) | ![Pressure Timeseries](https://github.com/user-attachments/assets/9f842e65-4c93-4033-9b43-ebe1b5561d53) |

![Alerts Timeline](https://github.com/user-attachments/assets/645daf58-381a-490d-ac4e-a5dbcfe4ee73)

## Architecture Diagram

![Image](https://github.com/user-attachments/assets/dcc12058-dbc7-4ea7-bd95-cac6300ce836)