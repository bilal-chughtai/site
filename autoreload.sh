#!/bin/bash

# Activate virtual environment (adjust the path as needed)
source venv/bin/activate || source .venv/bin/activate || {
    echo "Error: Could not find virtual environment"
    exit 1
}

echo "Starting auto-reload (Press Ctrl+C to stop)"

while true; do
    python -m build
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Build successful..."
    sleep 2
done

# Deactivate venv when script is stopped
deactivate