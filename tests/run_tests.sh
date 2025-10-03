#!/usr/bin/env bash
# usage: ./tests/run_tests.sh [duration_seconds]
# default duration: 6 seconds (if no duration is specified)

set -e

DUR=${1:-6}         # duration in seconds (default 6)
LOG="data/hub.log"

echo "TEST: running sensorhub for ${DUR}s (log file is at ${LOG})"

# remove old log
rm -f "${LOG}"

# run the program (will exit after --test-duration)
./sensorhub --test-duration "${DUR}"

# run the Python checker
python3 tools/check_log.py "${LOG}" "${DUR}"
RC=$?

if [ $RC -eq 0 ]; then
  echo "TEST: SUCCESS"
else
  echo "TEST: FAILURE (exit code $RC)"
fi

exit $RC