#!/bin/bash

# Activate virtual environment (adjust the path as needed)
source venv/bin/activate || source .venv/bin/activate || {
    echo "Error: Could not find virtual environment"
    exit 1
}

echo "Starting auto-reload (Press Ctrl+C to stop)"

while true; do
    # Refresh reading.md if last update was more than a day ago
    if python -c "
import os
from datetime import datetime, timedelta
stamp = '.reading_last_updated'
if not os.path.exists(stamp):
    exit(0)
age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(stamp))
exit(0) if age > timedelta(days=1) else exit(1)
" 2>/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Refreshing reading (stale or missing)..."
        python reading.py 2>/dev/null || true
    fi
    python -m build
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Build successful..."
    sleep 2
done

# Deactivate venv when script is stopped
deactivate