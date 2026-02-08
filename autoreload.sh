#!/bin/bash

# Activate virtual environment (adjust the path as needed)
source venv/bin/activate || source .venv/bin/activate || {
    echo "Error: Could not find virtual environment"
    exit 1
}

echo "Starting auto-reload (Press Ctrl+C to stop)"

while true; do
    # Refresh reading.md if last update was more than a day ago (with 5 min cooldown after failed attempts)
    if python -c "
import os
from datetime import datetime, timedelta
stamp = '.reading_last_updated'
attempt_stamp = '.reading_last_attempt'
# Skip if we tried recently (prevents loop when reading.py fails)
if os.path.exists(attempt_stamp):
    attempt_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(attempt_stamp))
    if attempt_age < timedelta(minutes=5):
        exit(1)
# Run if stamp missing or stale
if not os.path.exists(stamp):
    exit(0)
age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(stamp))
exit(0) if age > timedelta(days=1) else exit(1)
" 2>/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Refreshing reading (stale or missing)..."
        touch .reading_last_attempt 2>/dev/null || true
        python reading.py 2>/dev/null || true
    fi
    python -m build
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Build successful..."
    sleep 2
done

# Deactivate venv when script is stopped
deactivate