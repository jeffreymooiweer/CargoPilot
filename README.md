# CargoPilot

**Versie 1.0.0** — webapplicatie om bouwmaterialen en posities te analyseren en als ingevulde Appendix A1 (Excel) te exporteren.

**English:** CargoPilot parses material lines (paste or file import), calculates weight/volume, and exports a filled Appendix A1 Excel file from your official template.

Zie ook [CHANGELOG.md](CHANGELOG.md) en [ROADMAP.md](ROADMAP.md).

## Functionaliteiten (v1.0.0)

- Review-first wizard: regels invoeren met cataloguszoeken of vrije omschrijving
- Import via plakken of bestand (.xlsx, .csv, .txt) met downloadbare templates
- Herkenning van materiaal, producttype en afmetingen (NL/EN) met synoniemen
- Berekening gewicht, materiaalvolume en transportvolume; handmatige gewichtscorrectie
- Appendix A1-vlaggen (Y/N) met invulinstructies uit het template
- Appendix D (gevaarlijke stoffen) met ADR UN-lookup
- Export naar `intern-formulier.xlsx` (opmaak en formules behouden)
- **Overzicht materieel** — lege bibliotheek; beheerder vult via template-import
- Automatische materialen-/profielcatalogus (openbare referentiedata)
- Donkere modus, NL/EN, Docker/Unraid, geen appendix-historie op de server

## Versiebeleid

Vanaf **1.0.0** geldt [Semantic Versioning](https://semver.org/):

| Onderdeel | Locatie |
|-----------|---------|
| Versienummer | `VERSION`, `backend/VERSION` |
| Git-release | tag `v1.0.0`, `v1.1.0`, … |
| Docker Hub | `jeffersonmouze/cargopilot:latest` en `jeffersonmouze/cargopilot:v1.0.0` |
| API | `GET /api/health` → `version` |

## Snelle start (Docker Compose)

```bash
cp .env.example .env
# Pas APP_SECRET_KEY en ADMIN_PASSWORD aan
docker compose up -d --build
```

Open: http://localhost:8080

## Installatie op Unraid

1. Community Applications of `unraid/CargoPilot.xml`
2. Volume: `/mnt/user/appdata/cargopilot` → `/data`
3. Image: `jeffersonmouze/cargopilot:v1.0.0` (of `latest` na bevestigde update)
4. Environment: `APP_SECRET_KEY`, `ADMIN_*`
5. WebUI op gekozen poort (bijv. `http://<ip>:9935`)

**Permissies:** container zet eigenaar van `/data` op `PUID`/`PGID` (standaard `1000`).

## Eerste admin

Bij eerste start met environment variables:

- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

## Environment variables

| Variabele | Beschrijving | Default |
|---|---|---|
| `TZ` | Tijdzone | `Europe/Amsterdam` |
| `APP_SECRET_KEY` | JWT/sessie secret | verplicht in productie |
| `DATABASE_URL` | SQLite pad | `sqlite:////data/cargopilot.db` |
| `ADMIN_USERNAME` | Bootstrap admin | - |
| `ADMIN_EMAIL` | Bootstrap e-mail | - |
| `ADMIN_PASSWORD` | Bootstrap wachtwoord | - |
| `LOG_LEVEL` | Logging | `INFO` |
| `CORS_ALLOWED_ORIGINS` | CORS | `*` |
| `CATALOG_AUTO_SYNC` | Catalogus sync bij opstart | `true` |
| `CATALOG_SYNC_TIMEOUT_SECONDS` | HTTP-timeout sync | `20` |

## Catalogus (openbare bronnen)

Materialen (dichtheid) en profielen (kg/m) worden automatisch gesynchroniseerd — geen handmatig beheer.

| Gegeven | Bron |
|---|---|
| UPN, IPE, HEA, HEB, … | [steelprofiles_api](https://github.com/timskovjacobsen/steelprofiles_api) |
| SHS, RHS, CHS | [eurocodepy](https://github.com/kristapsfreibergs/eurocodepy) |
| Staal/hout/beton-dichtheid | eurocodepy + EN 1991 referentie |
| Metaaldichtheden | Wikidata SPARQL |
| Aliassen detectie | `seed/materials.json` |

`CATALOG_AUTO_SYNC=false` voor offline/snellere dev-start.

## Gevaarlijke stoffen (Appendix D)

- Invulinstructies in `backend/app/config/dg_instructions.json`
- UN-detectie in omschrijving → vlag DG + DG-stap
- Lookup: `GET /api/dg/lookup?un=1203` (FreightUtils ADR)

## Overzicht materieel

De materieelbibliotheek is **bewust leeg** bij installatie. Beheerders vullen deze via **Template downloaden** en **Importeren** (geen export van gevoelige lijsten).

Bij upgrade naar v1.0.0 worden items met bron `overzicht_materieel` automatisch verwijderd uit de database.

## Privacy en gegevensopslag

- Geen appendix-historie of job-database met materiaallijsten
- Exports: tijdelijk bestand → browser → verwijderd
- Geen operationele materieeldata in GitHub-repo of Docker-image (vanaf v1.0.0)
- Persistent op `/data`: gebruikers, catalogus-referenties, template, sync-status, **door u geïmporteerde** materieel

**Let op:** oudere Docker-images (vóór v1.0.0, juli 2026) kunnen nog geseede materieeldata bevatten. Na upgrade:

1. Gebruik alleen images gebouwd **na** de privacy-release (`v1.0.0` op schone git-historie).
2. Verwijder oude Docker-tags via GitHub → **Actions** → **Cleanup Docker Hub tags** → **Run workflow**  
   - `keep_tags`: `latest,v1.0.0,1.0.0,43c1732` (pas `43c1732` aan naar de huidige schone main-SHA)  
   - Of lokaal: `DOCKER_USERNAME=... DOCKER_TOKEN=... KEEP_TAGS=latest,v1.0.0,1.0.0 ./scripts/cleanup-dockerhub-tags.sh`
3. `docker pull jeffersonmouze/cargopilot:v1.0.0` en container herstarten

## Docker Hub

`jeffersonmouze/cargopilot:latest` · `jeffersonmouze/cargopilot:v1.0.0`

GitHub Actions: `.github/workflows/dockerhub.yml` (push `main` + tags `v*`).

Secrets: `DOCKER_USERNAME`, `DOCKER_TOKEN`.

## Appendix-template

`templates/intern-formulier.xlsx` → gekopieerd naar `/data/templates/`.

Mapping: `backend/app/config/appendix_mapping.json`.

## Development

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
cp ../.env.example ../.env
mkdir -p ../data/templates
cp ../templates/intern-formulier.xlsx ../data/templates/
export DATABASE_URL=sqlite:///$(pwd)/../data/cargopilot.db
uvicorn app.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
pytest
```

## Roadmap (samenvatting)

Volledig overzicht: [ROADMAP.md](ROADMAP.md).

### v1.0.0 ✓

- Appendix-wizard, import/templates, gewichtsaanpassing, lege materieelbibliotheek

### v1.1 (gepland) — Multimodale transportkeuze

- Keuze transportmodus (weg, lucht, zee)
- Bijbehorende formulieren en export, o.a. **CMR** (weg) en **IATA** / luchtvrachtdocumenten
- Template-download per modus

### v1.2 (gepland)

- Kolommapping-UI
- Duitse taal

## Licentie

MIT — zie [LICENSE](LICENSE).
