# CargoPilot

CargoPilot is een webapplicatie waarmee bouwmaterialen uit Excel geplakt, automatisch geanalyseerd en als ingevulde Appendix A1 (Excel) geëxporteerd kunnen worden.

**English summary:** CargoPilot parses pasted construction-material lines, calculates weight/volume, and exports a filled Appendix A1 Excel file based on your official template.

## Functionaliteiten

- Plakken van Excel/TSV/pipe-gescheiden data
- Herkenning van materiaal, producttype en afmetingen (NL/EN)
- Berekening van gewicht, materiaalvolume en transportvolume
- Review-stap met inline correcties
- Export naar bestaand `intern-formulier.xlsx` (opmaak en formules behouden)
- Login, admin-gebruikersbeheer, materialen-/profielenbibliotheek
- Docker, DockerHub CI/CD, Unraid-template

## Screenshots

> Placeholder: voeg screenshots toe na eerste deployment.

## Snelle start (Docker Compose)

```bash
cp .env.example .env
# Pas APP_SECRET_KEY en ADMIN_PASSWORD aan
docker compose up -d --build
```

Open: http://localhost:8080

## Installatie op Unraid

1. Installeer via Community Applications of gebruik `unraid/CargoPilot.xml`
2. Stel volume in: `/mnt/user/appdata/cargopilot` → `/data`
3. Configureer environment variables (`APP_SECRET_KEY`, `ADMIN_*`)
4. Open WebUI op poort 8080

## Eerste admin account

Bij eerste start maakt CargoPilot automatisch een admin aan als deze environment variables gezet zijn:

- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Zonder admin-credentials verschijnt een setupmelding in logs en UI.

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

## DockerHub image

`jeffreymooiweer/cargopilot:latest`

### GitHub Secrets voor CI/CD

In GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Waarde |
|---|---|
| `DOCKERHUB_USERNAME` | Je DockerHub gebruikersnaam |
| `DOCKERHUB_TOKEN` | DockerHub access token (niet je wachtwoord) |

Zonder deze secrets bouwt de GitHub Action de Docker-image nog steeds (om te verifiëren dat alles compileert), maar wordt er **niet** naar DockerHub gepusht. Zodra je de secrets instelt, pusht de volgende run automatisch naar `jeffreymooiweer/cargopilot:latest`.

Workflow: `.github/workflows/dockerhub.yml` (push naar `main` en tags `v*`).

## Appendix-template

Het template staat in `templates/intern-formulier.xlsx` en wordt bij start gekopieerd naar `/data/templates/`.

Celmapping is configureerbaar in `backend/app/config/appendix_mapping.json`.

**Aannames v1:**

- Sheet ` A1` wordt gevuld met bouwmaterialen
- Sheet `D` blijft ongewijzigd
- Registratiekolom: `{job_ref}:{regel}`
- Standaard vlaggen: `Loaded=Y`, overige `N`
- Afmetingen in appendix in centimeters

## Meertaligheid

- UI-taal: Nederlands / Engels (`react-i18next`)
- Inputtaal en appendix-outputtaal zijn onafhankelijk
- Materiaal- en productdictionaries zijn uitbreidbaar

## Development

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
cp ../.env.example ../.env
mkdir -p ../data/templates ../data/exports
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
DATABASE_URL=sqlite:////workspace/data/cargopilot.db pytest
```

Regressietest verwacht ~7534 kg totaalgewicht (±2%) voor de standaard staalvoorbeeldset.

## Beveiligingsnotities

- Geen publieke registratie; admin maakt accounts aan
- Wachtwoorden met Argon2 gehasht
- HttpOnly cookie auth
- Rate limiting op login (via slowapi, uitbreidbaar)
- Excel formula injection preventie bij export
- Container draait als non-root user `cargopilot`

## Roadmap

- [ ] Duitse taalondersteuning
- [ ] Appendix D (gevaarlijke stoffen) vullen
- [ ] Uitgebreidere profielcatalogus (IPE, HEA, HEB)
- [ ] Import/export materialenbibliotheek via UI
- [ ] Kolommapping UI bij ambigue headers

## Licentie

MIT — zie [LICENSE](LICENSE).
