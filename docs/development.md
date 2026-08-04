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

Frontend:

```bash
cd frontend
npm test           # Vitest + Testing Library
npm run build      # tsc -b && vite build (typecheck)
```

No ESLint is configured.

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
  src/i18n/             nl.json, en.json, de.json
templates/forms/        official PDF forms that get filled in
un_cards/               UN reference cards, one per UN number
scripts/                one-off maintenance scripts
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

A release builds the same commit **twice**: once for the push to `main`, which publishes
`latest`, and once for the tag, which publishes the version number. They start seconds
apart, so each ref writes its own buildx cache scope — sharing one `mode=max` scope let
the two exports race, and a build hung for an hour and a half instead of taking three
minutes. Reads still come from `main`'s cache, so the second build stays fast. The docker
job has a 45-minute timeout so a wedged build fails visibly rather than running all day.

Workflows live in `.github/workflows/`: `dockerhub.yml`, `tag-release.yml`,
`release.yml` and `cleanup-dockerhub.yml`.

## The UN cards

`un_cards/` was filled once and is not expected to change until a new edition of the
IMDG Code appears. The workflow that did it has been retired; the two scripts behind it
stay, so a future edition is a matter of running them again:

```bash
# Fetch and rename. ~2,900 downloads, roughly 80 minutes.
python scripts/fetch_un_cards.py --base-url ".../part{n}.pdf" --first 1 --last 2900 \
    --limit 20 --dry-run          # check the identification first
python scripts/fetch_un_cards.py --base-url ".../part{n}.pdf" --first 1 --last 2900

# Re-read the per-substance data out of the cards.
python scripts/extract_un_card_data.py --out backend/seed/dg/card_data.json
```

The identification is deliberately cautious. Each card states its UN number under a
`UN number` label and repeats it in the footer; both are read and must agree, and the
number must be a real entry in `backend/seed/dg/un_numbers.json`. A card is marked
`confirmed` only when the shipping name on it matches the name we hold. Anything weaker
goes to `un_cards/_unidentified/`. Filing a card under the wrong UN number would hand
someone the emergency information for a different substance, so the script would rather
skip than guess.

`extract_un_card_data.py` cross-checks its own EmS readings against `ems.json`, which
comes from the official EmS Guide and remains the authority. On the run that produced the
current data, 2,282 agreed and none disagreed — a useful signal that both datasets are
sound.

`backend/tests/test_un_card_identification.py` covers the ways identification can go
wrong; `backend/tests/test_dg_card_data.py` guards the extracted values.
