#!/bin/bash
set -euo pipefail

mkdir -p /data/templates /data/exports /data/logs

if [ ! -f /data/templates/Appendix_A1D_template.xlsx ] && [ -f /app/templates/Appendix_A1D_template.xlsx ]; then
  cp /app/templates/Appendix_A1D_template.xlsx /data/templates/
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8080
