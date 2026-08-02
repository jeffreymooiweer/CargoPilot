# Development

CargoPilot is one product with two processes: a **FastAPI** backend on Python 3.12 and a
**React 18 + TypeScript** frontend built with Vite. Data lives in a file-based SQLite
database; there is no separate database service.

- [Running from source](#running-from-source)
- [Tests](#tests)
- [Project layout](#project-layout)
- [How documents are produced](#how-documents-are-produced)
- [Versioning](#versioning)
- [Releasing](#releasing)

## Running from source

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
mkdir -p ../data

DATABASE_URL=sqlite:////absolute/path/to/repo/data/cargopilot.db \
DATA_DIR=/absolute/path/to/repo/data \
APP_SECRET_KEY=dev-secret \
ADMIN_USERNAME=admin ADMIN_EMAIL=admin@example.local ADMIN_PASSWORD=cargopilot123 \
CATALOG_AUTO_SYNC=false \
  uvicorn app.main:app --reload --port 8080
```

Two things catch people out:

- **The repo `.env` is not picked up when you run uvicorn from `backend/`.** Pydantic
  resolves `env_file=".env"` relative to the working directory, and there is no
  `backend/.env`. Pass the variables explicitly, as above.
- **`DATA_DIR` and `DATABASE_URL` default to `/data`,** which is usually not writable
  outside Docker. Point them at a folder in the repo.

`CATALOG_AUTO_SYNC=false` skips the startup fetch of external catalogues. It makes
startup much faster and does not affect weight calculations.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on port 5173 and proxies `/api` to `http://localhost:8080`.

## Tests

```bash
cd backend
DATABASE_URL=sqlite:////absolute/path/to/repo/data/test.db \
DATA_DIR=/absolute/path/to/repo/data \
  python -m pytest
```

Typecheck and build the frontend (no ESLint is configured):

```bash
cd frontend
npm run build      # tsc -b && vite build
```

A few notes on the test suite:

- **Import format for manual testing.** The wizard expects one line per row as
  `description | quantity | unit`, pipe- or tab-separated, with dimensions inside the
  description: `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks`. Free text without
  dimensions yields `status=error` and 0 kg. The steel regression set totals ~7,534 kg.
- **The equipment library is empty by design.** Seed tests use generic `DEMO-*` items.
- **Regulatory tables are pinned verbatim.** The IMDG segregation table, the class 1
  compatibility matrix and samples from the EmS index are asserted literally, so an
  accidental edit fails a test instead of silently shipping.
- **The AVC overlay is tested by coordinate.** `test_avc_waybill.py` checks where text
  lands on the page, not just that it is present.

## Project layout

```
backend/
  app/
    api/routes/         FastAPI endpoints
    config/             document_registry.json, dg_compliance.json, dg_instructions.json
    services/
      documents/        PDF filling and generation
      dg/               dangerous goods: enrichment, autofill, compliance
  seed/                 bundled reference data (materials, locations, dg)
  tests/
frontend/
  src/components/       wizard steps and panels
  src/pages/            routed pages
  src/i18n/             nl.json, en.json
templates/forms/        official PDF forms that get filled in
docs/                   this documentation
unraid/                 Unraid Community Applications template
```

## How documents are produced

Three paths, chosen by the `exporter` field in `document_registry.json`:

| `exporter` | How it works | Used by |
|---|---|---|
| `pdf_template` | Writes into the template's AcroForm fields, via PyMuPDF (falling back to pypdf) | CMR, CIM, IATA |
| `avc` | Draws a reportlab text layer and merges it onto a flat template | AVC waybill |
| `generic` | Generates a PDF from scratch with reportlab | Everything else |

The AVC form has no form fields at all, which is why it needs the overlay. Its
coordinate grid is derived from the template's own ruling and documented at the top of
`backend/app/services/documents/avc_form.py`.

`document_registry.json` is the single source of truth for which documents exist, which
sections and fields they have, which status each field carries (`USER_REQUIRED`,
`CONDITIONAL`, `CARRIER_PROVIDED`, `OPERATIONAL`, `SIGNATURE_REQUIRED`) and which
dangerous goods profile applies. Adding a document usually means editing that file plus
one exporter.

## Versioning

[Semantic Versioning](https://semver.org/) from 1.0.0 onwards. Version numbers are bumped
**conservatively** — collect small fixes into one patch release rather than reaching for
a minor.

| Bump | When | Example |
|---|---|---|
| **PATCH** `1.13.1` → `1.13.2` | Bug fixes, text and label corrections, small data fixes, documentation. No new functionality. | Wrong button label, missing translation, corrected density |
| **MINOR** `1.13.2` → `1.14.0` | New functionality that leaves existing shipments alone | New wizard step, new document, new endpoint |
| **MAJOR** `1.x` → `2.0.0` | Breaking changes: incompatible APIs or data formats, a different wizard structure, a required migration | Reserved for major overhauls |

When in doubt, take the smaller bump.

The version number lives in `VERSION` (and `backend/VERSION`), in `frontend/package.json`,
in the git tag `v*`, in the Docker tag, and is returned by `GET /api/health`.

## Releasing

1. Update `VERSION`, `frontend/package.json` and `CHANGELOG.md`.
2. Merge to `main`.
3. Run the **Tag release** workflow from GitHub Actions with the version number. It
   creates the tag and the GitHub Release from the changelog entry.
4. The **dockerhub** workflow builds and pushes `jeffersonmouze/cargopilot:latest` and
   `:v<version>` on pushes to `main` and on `v*` tags.

Required secrets: `DOCKER_USERNAME`, `DOCKER_TOKEN`.

Workflows live in `.github/workflows/`: `dockerhub.yml`, `tag-release.yml`,
`release.yml` and `cleanup-dockerhub.yml`.
