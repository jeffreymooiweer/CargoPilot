# CargoPilot

CargoPilot is een webapplicatie waarmee bouwmaterialen uit Excel geplakt, automatisch geanalyseerd en als ingevulde Appendix A1 (Excel) geëxporteerd kunnen worden.

**English summary:** CargoPilot parses pasted construction-material lines, calculates weight/volume, and exports a filled Appendix A1 Excel file based on your official template.

## Functionaliteiten

- Plakken van Excel/TSV/pipe-gescheiden data via **importfunctie** (niet meer als hoofdingang)
- Review als startpunt: regels invoeren met materieel-dropdown of vrije omschrijving (staal/profielen)
- Herkenning van materiaal, producttype en afmetingen (NL/EN)
- Berekening van gewicht, materiaalvolume en transportvolume
- Review-stap met inline correcties en appendix A1-vlaggen (Y/N) met invulinstructies uit het template
- Appendix D (gevaarlijke stoffen) met veldhelpteksten en ADR UN-lookup
- Export naar bestaand `Appendix_A1D_template.xlsx` (opmaak en formules behouden)
- Donkere modus
- Geen historie of server-side opslag van appendix-data
- **Overzicht Materieel** — 244 voertuigen/materieel uit appendix-template, herkenning bij input (bijv. Skoda Yeti)
- Login, admin-gebruikersbeheer, automatische materialen-/profielendatabase (achter de schermen)
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
3. Repository: `jeffersonmouze/cargopilot:latest`
4. Configureer environment variables (`APP_SECRET_KEY`, `ADMIN_*`)
5. Open WebUI op je gekozen poort (bijv. `http://<ip>:9935`)

**Permissies:** bij start zet de container automatisch de eigenaar van `/data` op `PUID`/`PGID` (standaard `1000`). Krijg je nog permissiefouten, verwijder de map `/mnt/user/appdata/cargopilot` en start opnieuw, of zet in Unraid (advanced) `PUID=99` en `PGID=100` (nobody op Unraid).

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
| `CATALOG_AUTO_SYNC` | Bij opstarten catalogus syncen vanuit openbare bronnen | `true` |
| `CATALOG_SYNC_TIMEOUT_SECONDS` | Timeout voor HTTP-downloads (seconden) | `20` |

## Catalogus uit openbare bronnen

CargoPilot beheert **materialen** (dichtheid) en **profielen** (kg/m) volledig automatisch. Er is geen menu of handmatige invoer — bij opstarten (en bij elke herstart) wordt alles gesynchroniseerd vanuit meerdere openbare bronnen.

| Gegeven | Bron | Opmerking |
|---|---|---|
| UPN/UNP, IPE, HEA, HEB, HEM, IPN (kg/m) | [steelprofiles_api](https://github.com/timskovjacobsen/steelprofiles_api) | EN 10365, CSV op GitHub |
| SHS, RHS, CHS koker/buisprofielen (kg/m) | [eurocodepy](https://github.com/kristapsfreibergs/eurocodepy) | EN 10210/10219 hollow sections JSON |
| Staal-, hout-, betondichtheid | [eurocodepy](https://github.com/kristapsfreibergs/eurocodepy) `eurocodes.json` | Eurocode 2/3/5 materiaalparameters |
| Metaaldichtheden (alu, koper, messing, …) | [Wikidata](https://www.wikidata.org/) SPARQL (P2054) | Open linked data, live ophalen |
| Bouwmaterialen (baksteen, glas, mortel, …) | EN 1991-1-1 referentietabel | Gebundeld in `seed/external/eurocode_materials.json` |
| Basis aliassen (staal, hout, PVC, …) | `seed/materials.json` | Alleen aliassen/detectie, geen handmatige UI |

**Niet gebruikt (bewust):**

| Bron | Reden |
|---|---|
| [MatWeb](https://www.matweb.com/) | Geen open API; scraping niet toegestaan in ToS |
| [Engineering Toolbox](https://www.engineeringtoolbox.com/) | Geen API; scraping niet toegestaan |
| [CalcSteel API](https://calcsteel.com/docs/api-reference) | Geen publiek JSON-endpoint zonder webapp |
| [2050 Materials API](https://2050-materials.com/) | Vereist registratie/API-token (niet volledig open) |
| [EPiC Database](https://www.epicdatabase.com.au/) | Feather-bestand via Python-package; geen stabiele open HTTP-API |

**Gedrag:**

- `CATALOG_AUTO_SYNC=true` (standaard): sync bij elke containerstart.
- Sync-status wordt opgeslagen in `/data/catalog_sync_status.json`.
- Bij netwerkuitval: fallback naar gebundelde kopieën in `backend/seed/external/`.
- Na deploy op Unraid: container herstarten is voldoende — geen handmatige catalogusstappen.

## Gevaarlijke stoffen (Appendix D)

Invulinstructies uit het tabblad **Invulinstructie** van `Appendix_A1D_template.xlsx` zijn overgenomen in `backend/app/config/dg_instructions.json`. De wizard toont deze als helptekst bij:

- **Appendix A1-vlaggen** (beladen, stapelbaar, DG, ITAR, TBB, …) in de review-stap
- **Appendix D-velden** (UN-nummer, PSN, klasse, verpakkingsgroep, …) in de DG-stap

**Automatische detectie:** een UN- of ID-nummer in de omschrijving zet de vlag *Dangerous goods* op `Y` en opent de DG-stap.

**ADR-lookup:** via `GET /api/dg/lookup?un=1203` (FreightUtils ADR-database, geen authenticatie). De frontend vult PSN, klasse en verpakkingsgroep automatisch in.

**Export:** bij regels met DG wordt tabblad `D` ingevuld (metadata + productkolommen). Het tabblad *Invulinstructie* blijft ongewijzigd.

## Overzicht Materieel

De tabel onderaan het tabblad **Overzicht Materieel** in `Appendix_A1D_template.xlsx` (SAP MATNR, specifications, afmetingen, gewicht) wordt bij eerste opstarten geladen in de database (`equipment_items`). Beheer via menu **Overzicht materieel** (admin).

Bij het plakken in de wizard herkent CargoPilot materieel op basis van SAP-code, specifications en aliassen — bijvoorbeeld `skoda yeti` → gewicht 1370 kg, afmetingen en appendix-omschrijving `VEHICLE SKODA YETI`.

## Privacy en gegevensopslag

CargoPilot is ontworpen om **geen gevoelige operationele data** te bewaren:

- **Geen historie** — er is geen overzicht van eerdere appendixen.
- **Geen job-database** — geplakte materiaallijsten, berekende regels en metadata worden niet opgeslagen in SQLite.
- **Geen appendix-bestanden op schijf** — exports worden in een tijdelijk bestand gemaakt, naar de browser gestuurd en daarna verwijderd.
- **Opschoning bij opstart** — eventuele oude jobs of exportbestanden van eerdere versies worden bij containerstart gewist.

Wat wél persistent blijft op `/data`: gebruikersaccounts, de materiaal-/profielencatalogus (openbare referentiedata), het Excel-template en catalogus-sync status.

## DockerHub image

`jeffersonmouze/cargopilot:latest`

### GitHub Secrets voor CI/CD

In GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Waarde |
|---|---|
| `DOCKER_USERNAME` | `jeffersonmouze` |
| `DOCKER_TOKEN` | DockerHub **Access Token** voor dat account |

**Belangrijk:**
1. De image staat op [jeffersonmouze/cargopilot](https://hub.docker.com/repository/docker/jeffersonmouze/cargopilot/general)
2. `DOCKER_USERNAME` in GitHub Secrets moet `jeffersonmouze` zijn
3. Gebruik een [Access Token](https://hub.docker.com/settings/security) als `DOCKER_TOKEN`

Zonder deze secrets bouwt CI nog steeds, maar pusht niet. Na correcte secrets wordt `jeffersonmouze/cargopilot:latest` bijgewerkt (gebruikt door Unraid).

Workflow: `.github/workflows/dockerhub.yml` (push naar `main` en tags `v*`).

## Appendix-template

Het template staat in `templates/Appendix_A1D_template.xlsx` en wordt bij start gekopieerd naar `/data/templates/`.

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
cp ../templates/Appendix_A1D_template.xlsx ../data/templates/
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
- [x] Appendix D (gevaarlijke stoffen) vullen
- [x] Uitgebreidere profielcatalogus (IPE, HEA, HEB) — via openbare sync
- [ ] Import/export materialenbibliotheek via UI
- [ ] Kolommapping UI bij ambigue headers

## Licentie

MIT — zie [LICENSE](LICENSE).
