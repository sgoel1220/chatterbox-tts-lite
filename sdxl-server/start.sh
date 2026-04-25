#!/bin/bash
set -e

mkdir -p /models /loras

# Run startup downloads (idempotent — skips files that already exist)
python3 /app/download.py

# If download.py resolved a local base model, export it for uvicorn
if [ -f /tmp/env_extra ]; then
    set -a
    source /tmp/env_extra
    set +a
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
