# CargoPilot

**Versie 1.9.0** — webapplicatie om colli en materialen te analyseren en als transportdocumenten (PDF) te exporteren, per transportmodaliteit. Uitsluitend bedoeld voor civiele instanties.

**English:** CargoPilot parses package lines (paste or file import), calculates weight/volume, and exports transport documents per modality — CMR, CIM, IMO/IATA dangerous goods declarations, VGM and shipping instructions. For civilian use only.

Zie ook [CHANGELOG.md](CHANGELOG.md) en [ROADMAP.md](ROADMAP.md).

## Functionaliteiten (v1.9.0)

- **Modaliteitskeuze bij start**: wegtransport, spoor, zeevracht, binnenvaart, luchtvracht of multimodaal
- **Formulierenselectie per modaliteit**: alleen relevante documenten; bij multimodaal alles beschikbaar
- **Eén wizard voor alle formulieren**: zendinggegevens één keer invullen, daarna per formulier een eigen sub-stap met alleen de nog benodigde velden ("Formulier x van y") — geen dubbele invoer
- **Adres-autocomplete** (Photon/OpenStreetMap, instelbaar via `GEO_ADDRESS_API_URL`) en **locatie-autocomplete** voor 4.500+ luchthavens (IATA/ICAO), 17.500+ UN/LOCODE-havens en 750+ Europese hoofdstations, afgestemd op de gekozen modaliteit
- **Goederendatabase met 400 materialen/goederen** (bouw, metaal, hout, brandstoffen, chemie, agri, voeding, papier, ertsen, recycling, stukgoed) met dichtheden en NL/EN-aliassen; blokvormige goederen worden automatisch op dichtheid doorgerekend
- **Handtekening tekenen of uploaden** (of overslaan voor ondertekening met pen): geplaatst in CMR vak 22, het IATA-handtekeningveld en de gegenereerde PDF's; carrier- en ontvangsthandtekeningen blijven altijd leeg
- **UN-nummer-autocomplete** met offline ADR-database (2.928 vermeldingen: klasse, verpakkingsgroep, etiketten, verpakkingsinstructies, vervoerscategorie, tunnelcode) en **verpakkingskeuze** uit alle 107 UN-verpakkingscodes (ADR 6.1/6.5/6.6)
- **Officiële PDF-formulieren**: CMR (IRU-model 2007) en IATA Shipper's Declaration worden als originele invulbare PDF-templates ingevuld en als PDF gedownload
- Documenten: CMR (PDF), CIM (PDF), IMO Multimodal DG Form, IATA Shipper's Declaration (PDF), VGM-verklaring, AWB/B-L Shipping Instructions, ADR/ADN-document, paklijst, afleverbon
- **Veldstatussen per document**: gebruikersinvoer, carriergegevens, operationele velden en handtekeningen worden onderscheiden; handtekeningen worden alleen geplaatst als u er zelf één tekent of uploadt
- **DG-exportblokkades** per modaliteitsprofiel (ADR/RID/ADN/IMDG/IATA DGR) bij onvolledige classificatie
- **Nalevingsbegeleiding gevaarlijke stoffen**: ADR 1.1.3.6-puntencalculator (1000-puntenregel), samenladingscontrole (ADR 7.5.2/CV28), IATA-segregatie (Table 9.3.A incl. lithiumregel) en Q-waardeberekening (IATA 5.0.2.11) met live waarschuwingen
- Colli-invoer met cataloguszoeken of vrije omschrijving; per collo een gevaarlijke-stoffenmarkering
- Import via plakken of bestand (.xlsx, .csv, .txt) met downloadbare templates
- Herkenning van materiaal, producttype en afmetingen (NL/EN) met synoniemen
- Berekening gewicht, materiaalvolume en transportvolume; handmatige gewichtscorrectie
- Gevaarlijke-stoffenstap met ADR UN-lookup en automatische UN-detectie in omschrijvingen
- **Overzicht materieel** — lege bibliotheek; beheerder vult via template-import
- Automatische materialen-/profielcatalogus (openbare referentiedata)

## Versiebeleid

Vanaf **1.0.0** geldt [Semantic Versioning](https://semver.org/). Het versienummer wordt bewust terughoudend opgehoogd:

| Ophoging | Wanneer | Voorbeeld |
|---|---|---|
| **PATCH** (`1.8.0` → `1.8.1`) | Foutherstel, tekst- en labelcorrecties, kleine datacorrecties, documentatie — geen nieuwe functionaliteit | Verkeerd knoplabel, ontbrekende vertaling, dichtheid gecorrigeerd |
| **MINOR** (`1.8.1` → `1.9.0`) | Nieuwe functionaliteit die bestaande zendingen ongemoeid laat | Nieuwe wizardstap, nieuw document, nieuw endpoint |
| **MAJOR** (`1.x` → `2.0.0`) | Ingrijpende wijzigingen: incompatibele API's of dataformaten, een andere wizardopzet, verplichte migratie | Gereserveerd voor grote herzieningen |

Bij twijfel geldt de kleinste ophoging. Verzamel losse correcties bij voorkeur in één patchrelease.

| Onderdeel | Locatie |
|-----------|---------|
| Versienummer | `VERSION`, `backend/VERSION` |
| Git-release | tag `v1.0.0`, `v1.1.0`, … |
| Docker Hub | `jeffersonmouze/cargopilot:latest` en `jeffersonmouze/cargopilot:v1.9.0` |
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
3. Image: `jeffersonmouze/cargopilot:v1.9.0` (of `latest` na bevestigde update)
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
| `GEO_ADDRESS_API_URL` | Photon-compatibele adres-API voor autocomplete | `https://photon.komoot.io/api` |
| `GEO_ADDRESS_TIMEOUT_SECONDS` | HTTP-timeout adres-API | `8` |

## Catalogus (openbare bronnen)

Materialen (dichtheid) en profielen (kg/m) worden automatisch gesynchroniseerd — geen handmatig beheer.

| Gegeven | Bron |
|---|---|
| UPN, IPE, HEA, HEB, … | [steelprofiles_api](https://github.com/timskovjacobsen/steelprofiles_api) |
| SHS, RHS, CHS | [eurocodepy](https://github.com/kristapsfreibergs/eurocodepy) |
| Staal/hout/beton-dichtheid | eurocodepy + EN 1991 referentie |
| Metaaldichtheden | Wikidata SPARQL |
| **400 transportgoederen** met (stort)dichtheid en NL/EN-aliassen | `seed/materials.json` |

De goederendatabase dekt o.a. bouwmaterialen en natuursteen, metalen (incl. edel- en speciaalmetalen), houtsoorten en plaatmateriaal, brandstoffen, chemicaliën en gassen (vloeibaar gemaakt), meststoffen, granen/zaden/veevoer, groente en fruit, levensmiddelen, ertsen en mineralen, kunststoffen, papier, textiel, afval- en recyclingstromen en stukgoed-praktijkgemiddelden (pallets, witgoed, machines).

`CATALOG_AUTO_SYNC=false` voor offline/snellere dev-start.

## Geodata (openbare bronnen)

Locatie-autocomplete werkt volledig offline op meegeleverde seeds in `backend/seed/locations/`:

| Gegeven | Bron | Licentie |
|---|---|---|
| Luchthavens (IATA/ICAO) | [OurAirports](https://ourairports.com/data/) | Public domain |
| Havens (UN/LOCODE) | [UNECE UN/LOCODE](https://unece.org/trade/uncefact/unlocode) | Vrij herbruikbaar |
| Treinstations (EU) | [Trainline EU stations](https://github.com/trainline-eu/stations) | ODbL |

Adres-autocomplete gebruikt een externe Photon-geocoder (OpenStreetMap-data, standaard `photon.komoot.io`). Zonder internettoegang valt deze functie stil; handmatig invullen blijft altijd mogelijk.

## Gevaarlijke stoffen

- Invulinstructies in `backend/app/config/dg_instructions.json`; nalevingsregels in `dg_compliance.json`
- UN-detectie in omschrijving of DG-vinkje per collo → gevaarlijke-stoffenstap
- **Offline UN-database** (`backend/seed/dg/un_numbers.json`, 2.928 vermeldingen): autocomplete via `GET /api/dg/search?q=`; regelgevende kolommen (klasse, classificatiecode, verpakkingsgroep, etiketten, LQ/EQ, verpakkingsinstructies, vervoerscategorie, tunnelcode, Kemler-nummer) uit ADR Tabel A ([rkstgr/adr-substances](https://github.com/rkstgr/adr-substances), op basis van de officiële UNECE-publicatie); Engelse namen uit de 49 CFR 172.101-tabel (eCFR/GovInfo, public domain)
- **UN-verpakkingscodes** (`backend/seed/dg/packagings.json`, 107 codes volgens ADR 6.1.2/6.5.1.4/6.6.2): `GET /api/dg/packagings?q=`
- Lookup: `GET /api/dg/lookup?un=1203` (FreightUtils ADR 2025, met automatische offline terugval); nalevingscontrole: `POST /api/dg/compliance`
- **Automatische invulling** (`POST /api/dg/prepare`): uit het UN-nummer volgen de juiste vervoersnaam, klasse **en divisie** (bij gassen uit de etikettenkolom, bij explosieven uit de classificatiecode zoals `1.4S`), de nevengevaren, verpakkingsgroep, vervoerscategorie, tunnelcode, Kemler-nummer, LQ/EQ-limieten, de **EmS-code** voor zeevervoer en de **luchtvrachtregels** (Cargo Aircraft Only en IATA PI voor lithiumbatterijen, verbod op klasse 2.3). Aantallen, verpakkingssoort en massa's komen uit de al ingevoerde colli. Alleen lege velden worden gevuld — handmatige correcties blijven staan.
- **Officiële documentregels** worden per profiel samengesteld: ADR/RID/ADN 5.4.1.1.1 (`UN 1203, BENZINE, 3, II, (D/E), 10 jerrycan, 200 L`) inclusief de totale hoeveelheid per vervoerscategorie (5.4.1.1.1.1), IMDG met EmS en marine pollutant, IATA met verpakkingsinstructie en CAO-markering
- **EmS-noodschema's**: 305 UN-nummers hebben een exacte EmS-code (`backend/seed/dg/ems.json`, brand- en lekkageschema met gevarenprofiel); overige stoffen krijgen een indicatieve klassestandaard die als suggestie wordt getoond en niet automatisch wordt ingevuld
- **Vervoersverboden**: stoffen die ADR Tabel A niet ten vervoer toelaat worden herkend, in de wizard rood gemeld en geblokkeerd voor export
- **Segregatie zeevervoer**: volledige IMDG 7.2.4-klassescheidingstabel (codes 1-4 "away from" t/m "separated longitudinally"), inclusief nevengevaren; scheidingsgroepen (7.2.5) en kolom 16b van de Dangerous Goods List blijven de verantwoordelijkheid van de afzender
- Klasse-specifieke documentvereisten worden benoemd (netto explosieve massa bij klasse 1, temperatuurbeheersing bij 4.1/5.2, verantwoordelijke persoon bij 6.2, transportindex en collo-categorie bij klasse 7)
- De offline database is een feitelijke invulhulp; de actuele ADR/RID/ADN/IMDG/IATA-uitgave blijft altijd leidend

## Overzicht materieel

De materieelbibliotheek is **bewust leeg** bij installatie. Beheerders vullen deze via **Template downloaden** en **Importeren** (geen export van gevoelige lijsten).

Bij upgrade naar v1.0.0 worden items met bron `overzicht_materieel` automatisch verwijderd uit de database.

## Privacy en gegevensopslag

- Geen documenthistorie of job-database met materiaallijsten
- Exports: tijdelijk bestand → browser → verwijderd
- Geen operationele materieeldata in GitHub-repo of Docker-image (vanaf v1.0.0)
- Persistent op `/data`: gebruikers, catalogus-referenties, sync-status, **door u geïmporteerde** materieel

**Let op:** Docker-images ouder dan v1.4.0 bevatten nog een intern formulier dat niet voor civiel gebruik is bedoeld. Na upgrade:

1. Gebruik alleen `v1.4.0` of nieuwer (of `latest` na de 1.4.0-build).
2. Verwijder oude Docker-tags via GitHub → **Actions** → **Cleanup Docker Hub tags** → **Run workflow** met `keep_tags`: `latest,v1.9.0,1.9.0`.
3. `docker pull jeffersonmouze/cargopilot:v1.9.0` en container herstarten.

## Docker Hub

`jeffersonmouze/cargopilot:latest` · `jeffersonmouze/cargopilot:v1.9.0`

GitHub Actions: `.github/workflows/dockerhub.yml` (push `main` + tags `v*`).

Secrets: `DOCKER_USERNAME`, `DOCKER_TOKEN`.

## Development

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
cp ../.env.example ../.env
mkdir -p ../data
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

### v1.2.0 ✓ — Multimodale transportkeuze, officiële PDF-formulieren

- Modaliteitskeuze, formulierenselectie, documentregister en export per document
- CMR, CIM, IMO/IATA DG-verklaringen, VGM, shipping instructions, paklijst, afleverbon

### v1.0.0 ✓


### v1.2 (gepland)

- Kolommapping-UI
- Duitse taal

## Officiële formulier-templates

Alle documenten worden als **PDF** geëxporteerd. Officiële invulbare formulieren staan in `templates/forms/` en worden door de backend ingevuld (niet nagebouwd); de overige worden als nette PDF gegenereerd met reportlab.

| Document | Type | Bron / template |
|---|---|---|
| CMR-vrachtbrief | Ingevuld officieel PDF | IRU-model 2007 (`templates/forms/cmr.pdf`, 4 doorslagen) |
| IATA Shipper's Declaration | Ingevuld officieel PDF | IATA open-formaat (`templates/forms/iata_dgd.pdf`) |
| CIM-vrachtbrief | Ingevuld officieel PDF | CIT CIM/CUV (`templates/forms/cim.pdf`) |
| IMO MDG Form, VGM, AWB/B-L SI, ADR/ADN, paklijst, afleverbon | Gegenereerde PDF (reportlab) | Eigen opmaak met vaste wettelijke teksten |

Carrier- en operationele velden worden nooit vooraf ingevuld; een handtekening wordt alleen geplaatst wanneer de gebruiker die zelf tekent of uploadt. Officiële formulieren: controleer vóór opname in een publieke repository de herdistributievoorwaarden van elk formulier.

## Disclaimer en aansprakelijkheid

Gegenereerde documenten zijn **concepten**; controleer, vul aan en onderteken door een bevoegde persoon vóór gebruik. De maker(s) aanvaarden **geen enkele aansprakelijkheid**. Volledige tekst: [DISCLAIMER.md](DISCLAIMER.md) en in de app onder **Disclaimer**.

## Licentie

Apache License 2.0 with Commons Clause — zie [LICENSE](LICENSE) en [DISCLAIMER.md](DISCLAIMER.md).

Commercial use of this software within your own organization is permitted. Selling, reselling, hosting, or commercially redistributing the software itself requires prior written permission from the copyright holder.
