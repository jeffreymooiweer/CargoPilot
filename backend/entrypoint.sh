#!/bin/bash
set -euo pipefail

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Align container user with volume ownership (common on Unraid).
if [ "$(id -u)" -eq 0 ]; then
  if ! getent group cargopilot >/dev/null 2>&1; then
    groupadd -g "$PGID" cargopilot
  else
    groupmod -o -g "$PGID" cargopilot 2>/dev/null || true
  fi
  if ! id cargopilot >/dev/null 2>&1; then
    useradd -u "$PUID" -g "$PGID" -s /bin/bash cargopilot
  else
    usermod -o -u "$PUID" -g "$PGID" cargopilot 2>/dev/null || true
  fi

  mkdir -p /data/templates /data/exports /data/logs
  chown -R "${PUID}:${PGID}" /data

  exec gosu cargopilot uvicorn app.main:app --host 0.0.0.0 --port 8080
fi

mkdir -p /data/templates /data/exports /data/logs

exec uvicorn app.main:app --host 0.0.0.0 --port 8080
