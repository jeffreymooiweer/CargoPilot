#!/bin/bash
set -euo pipefail

mkdir -p /data/templates /data/exports /data/logs

if [ ! -f /data/templates/intern-formulier.xlsx ] && [ -f /app/templates/intern-formulier.xlsx ]; then
  cp /app/templates/intern-formulier.xlsx /data/templates/
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8080
