# AGENTS.md

## Cursor Cloud specific instructions

CargoPilot is a single product with two dev processes: a Python 3.12 FastAPI backend
(`backend/`, port 8080) and a React/Vite/TypeScript frontend (`frontend/`, Vite dev
server on port 5173 that proxies `/api` → `http://localhost:8080`). Data is stored in
file-based SQLite; there is no separate database service. Standard commands live in
`README.md` (see "Development"), `backend/requirements.txt`, and `frontend/package.json`.

Python dependencies are installed into a virtualenv at `/workspace/.venv` (the startup
update script creates it and installs `backend/requirements.txt`; frontend deps via
`npm install`). Use `/workspace/.venv/bin/python` / `/workspace/.venv/bin/uvicorn` /
`/workspace/.venv/bin/pytest` when running the backend.

Non-obvious gotchas for running/testing:

- **Env vars are NOT auto-loaded from the repo `.env` when running uvicorn from `backend/`.**
  Pydantic settings use `env_file=".env"` resolved relative to the current working
  directory, and there is no `backend/.env`. Pass config explicitly when running dev.
- **`DATA_DIR`/`DATABASE_URL` default to `/data` (not writable in this environment).**
  For local dev, point them at the repo, e.g. `DATA_DIR=/workspace/data` and
  `DATABASE_URL=sqlite:////workspace/data/cargopilot.db`. Create `data/` if missing;
  the backend auto-copies the Excel template and seeds catalogs on startup.
- **Admin bootstrap:** there is no public registration. The first admin is created on
  startup only if `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` are set. Log in
  with those credentials.
- **`CATALOG_AUTO_SYNC` defaults to `true`** and fetches reference catalogs from external
  URLs at every startup (with per-source HTTP timeouts). Set `CATALOG_AUTO_SYNC=false`
  for faster/offline dev startup — it falls back to the bundled seeds in `backend/seed/`
  and does not affect weight calculations.
- **Material recognition input format (important for manual testing):** the wizard's
  Excel/text import expects one line per row as `description | quantity | unit`
  (pipe- or tab-separated), with dimensions embedded in the description, e.g.
  `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks`. Free-text descriptions without
  dimensions yield `status=error` and 0 kg. The steel regression set totals ~7534 kg.
- **Equipment library starts empty in v1.0.0.** Seed tests use generic `DEMO-*` items;
  no operational equipment JSON ships with the repo.

Example dev run (from repo root):

```bash
# Backend
cd backend
DATABASE_URL=sqlite:////workspace/data/cargopilot.db DATA_DIR=/workspace/data \
  APP_SECRET_KEY=dev-secret ADMIN_USERNAME=admin ADMIN_EMAIL=admin@example.local \
  ADMIN_PASSWORD=cargopilot123 CATALOG_AUTO_SYNC=false \
  /workspace/.venv/bin/uvicorn app.main:app --reload --port 8080

# Frontend (separate shell)
cd frontend && npm run dev
```

- **Tests:** `cd backend && DATABASE_URL=sqlite:////workspace/data/cargopilot_test.db DATA_DIR=/workspace/data /workspace/.venv/bin/python -m pytest`
- **Typecheck/build (no ESLint configured):** `cd frontend && npm run build` (`tsc -b && vite build`).
