# Stage 1: Frontend build
# The static bundle is architecture-independent. Build it once on the native
# runner instead of running Node and Vite again through ARM64 QEMU.
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 -s /bin/bash cargopilot

WORKDIR /app

COPY backend/requirements-runtime.txt ./requirements-runtime.txt
RUN pip install -r requirements-runtime.txt && pip check

COPY backend/ ./backend/
COPY templates/ ./templates/
# The changelog the what's-new card serves after an update. Next to /app/backend
# so app/services/changelog.py finds it where a checkout keeps it: one level up.
COPY CHANGELOG.md ./CHANGELOG.md
# The UN card library that the card export serves. This is by far the largest
# thing in the image: 2,849 PDFs, 575 MB, committed to the repository rather
# than fetched at build time. Removing it would shrink the image by roughly
# nine tenths and take the UN card export with it.
COPY un_cards/ ./un_cards/

COPY --from=frontend-build /build/dist ./backend/static/

RUN chmod +x /app/backend/entrypoint.sh && chown -R cargopilot:cargopilot /app

WORKDIR /app/backend

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["/app/backend/entrypoint.sh"]
