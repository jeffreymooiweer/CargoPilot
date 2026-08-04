# Data sources

CargoPilot ships with reference data so that most of it works without internet access.
This page lists where each dataset comes from.

Only **factual data** is included — a UN number mapped to a code, a material mapped to a
density. Regulatory texts themselves are copyrighted and are not in this repository.

- [Goods and densities](#goods-and-densities)
- [Steel and timber profiles](#steel-and-timber-profiles)
- [Locations](#locations)
- [Dangerous goods regulations](#dangerous-goods-regulations)
- [Official form templates](#official-form-templates)

## Goods and densities

**400 goods** with bulk or solid densities, min/max ranges, search aliases and names in
Dutch, English and German, in `backend/seed/materials.json`. Each entry states whether the figure is a bulk
density, a solid density, a liquid density or an effective pallet density.

Coverage spans construction materials and natural stone, metals (including precious and
speciality metals), timber species and sheet material, fuels, chemicals and liquefied
gases, fertilisers, grain, seed and animal feed, fruit and vegetables, foodstuffs, ores
and minerals, plastics, paper, textiles, waste and recycling streams, and practical
averages for general cargo such as pallets, white goods and machinery.

Every alias is unique across the whole database, so a description always resolves to
exactly one entry.

## Steel and timber profiles

Synchronised automatically at startup — no manual maintenance.

| Data | Source |
|---|---|
| UPN, IPE, HEA, HEB and similar | [steelprofiles_api](https://github.com/timskovjacobsen/steelprofiles_api) |
| SHS, RHS, CHS | [eurocodepy](https://github.com/kristapsfreibergs/eurocodepy) |
| Steel, timber and concrete densities | eurocodepy + EN 1991 reference values |
| Metal densities | Wikidata SPARQL |

Set `CATALOG_AUTO_SYNC=false` to use the bundled copies instead.

## Locations

Location autocomplete works fully offline from the seeds in
`backend/seed/locations/`.

| Data | Source | Licence |
|---|---|---|
| 4,500+ airports (IATA/ICAO) | [OurAirports](https://ourairports.com/data/) | Public domain |
| 17,500+ ports (UN/LOCODE) | [UNECE UN/LOCODE](https://unece.org/trade/uncefact/unlocode) | Freely reusable |
| 750+ European railway stations | [Trainline EU stations](https://github.com/trainline-eu/stations) | ODbL |

Address autocomplete is the one feature that calls out: it uses a Photon geocoder on
OpenStreetMap data (`photon.komoot.io` by default, configurable). Without internet it
goes quiet; typing an address by hand always works.

## Dangerous goods regulations

| Data | Source |
|---|---|
| Classification per UN number — class, packing group, labels, LQ/EQ, packing instruction, transport category, tunnel code, Kemler number | ADR Table A via [rkstgr/adr-substances](https://github.com/rkstgr/adr-substances), based on the official UNECE publication |
| Proper shipping names, English and German | The same ADR Table A export — it carries `name_en` and `name_de` per UN number. There is no Dutch column, so Dutch readers get the English name |
| English proper shipping names, cross-check | 49 CFR 172.101 (eCFR / GovInfo, public domain) |
| UN packaging codes (107) | ADR 6.1.2 / 6.5.1.4 / 6.6.2 |
| EmS emergency schedules per UN number, and the schedule descriptions | IMO **MSC.1/Circ.1588/Rev.3** — EmS Guide (IMO circular, freely distributable) |
| Class segregation table and class 1 compatibility matrix | IMDG Code chapter 7.2, Amendment 40-20 — unchanged in 42-24 |
| Segregation exemption tables 7.2.6.3.1 – 7.2.6.3.4 | IMDG Code chapter 7.2, Amendment 40-20 — unchanged in 42-24 |
| Segregation groups per substance (SGG1–SGG18, 629 entries) | IMDG Code chapter 3.1, section 3.1.4.4 — unchanged in 42-24; the separate SGG1a marking for strong acids was dropped in 41-22 |
| Lithium and sodium-ion batteries in aviation | [IATA Guidance Document for Lithium Batteries and Sodium ion Batteries](https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-guidance-document.pdf), 2026 edition |
| ADR 1.1.3.6 points, loading together 7.5.2, IATA Table 9.3.A, Q value | ADR 2025 (UNECE) and the IATA DGR |
| Stowage codes SW1–SW31, handling codes H1–H5, segregation codes SG1–SG78 with their descriptions | IMDG Code chapters 7.1.5, 7.1.6 and 7.2.8, via IMO resolution **MSC.556(108)** (adopted 23 May 2024), read by `scripts/extract_imdg_codes.py` |
| Dangerous Goods List per UN number — class, subsidiary hazards, packing group, special provisions, LQ/EQ, packing/IBC/tank instructions, EmS, stowage and handling (16a), segregation (16b), properties | IMDG Code chapter 3.2, Amendment 42-24, via IMO resolution **MSC.556(108)**, read by `scripts/extract_imdg_dgl.py` |
| IMDG Amendment 42-24 changes over 41-22 | NCB Hazcheck, *IMDG Code Amendment 42-24 changes detailed summary*, October 2024 v1.0, and IMO **E&T 38/3/9** for the UN 1361 provisions |

## Which edition is running

`GET /api/regulatory` reports, per rule set, the edition, the source, the validity
period, known errata and a SHA-256 over every data file it uses. `GET /api/health`
carries a compact form of the same thing, so a bug report can say what the installation
actually computes with.

Two things it answers that documentation cannot:

- **Whether an edition has expired.** The IATA DGR is replaced every year and the 67th
  edition runs to 31 December 2026. From 1 January 2027 the manifest reports `iata` under
  `expired` instead of quietly carrying on. The UN cards (41-22) are already listed as
  expired — they are still used, but only for marine pollutant and bulk carriage.
- **Whether two installations hold the same data.** The `manifest_id` is a hash over all
  seed files together. Same id, same data.

Where the data lives:

| File | Contents |
|---|---|
| `backend/seed/dg/un_numbers.json` | 2,928 UN entries |
| `backend/seed/dg/ems.json` | 2,338 UN numbers with fire and spillage schedules |
| `backend/seed/dg/segregation_groups.json` | 18 groups, 629 substance entries |
| `backend/seed/dg/packagings.json` | 107 UN packaging codes |
| `backend/seed/dg/imdg_42_24.json` | The IMDG Amendment 42-24 difference layer over the 41-22 data |
| `backend/seed/dg/imdg_codes.json` | 110 stowage, handling and segregation code descriptions |
| `backend/seed/dg/imdg_dgl.json` | The Dangerous Goods List: 2,860 rows over 2,347 UN numbers |
| `backend/app/config/dg_compliance.json` | Segregation tables and compliance rules |
| `backend/app/config/dg_instructions.json` | Field help text |

Where internet is available, the UN lookup enriches entries live from an ADR 2025 source
and falls back to the offline database automatically.

## UN cards

`un_cards/` holds one reference card per UN number, named after the number it describes.
The folder is empty in a fresh checkout and is filled once by the **Fetch UN cards**
workflow.

| Data | Source |
|---|---|
| IMDG UN cards, one per UN number | Cantell, 2023 edition (IMDG 41-22) — `imdg_2023_-_en_part<n>.pdf` |

The part number is not the UN number (`part1` is UN 0004), so the workflow reads the
number out of each card rather than trusting the filename. `un_cards/manifest.json`
records where each file came from and how it was identified.

The cards carry more than emergency information, and that has been extracted into
`backend/seed/dg/card_data.json` by `scripts/extract_un_card_data.py`: marine pollutant
status (column 4), stowage codes (SW, column 16a), segregation codes (SG, column 16b) and
bulk carriage, for all 2,336 UN numbers.

Since v1.23.0 columns 16a and 16b come from the Dangerous Goods List of Amendment 42-24
instead, so what the cards still supply is marine pollutant status and bulk carriage.
They no longer carry a class: nothing in the application read it, and the card parser had
it wrong for eleven substances (see the v1.27.1 entry in the changelog).

The extraction cross-checks its own EmS readings against `ems.json`, which comes from the
official EmS Guide and remains the authority: **2,282 agreed, none disagreed**.

## Official form templates

The filled-in official forms live in `templates/forms/`:

| File | Form |
|---|---|
| `cmr.pdf` | CMR consignment note, IRU model 2007 |
| `cim.pdf` | CIM consignment note, CIT CIM/CUV 2019 |
| `iata_dgd.pdf` | IATA Shipper's Declaration, open format |
| `avc.pdf` | AVC waybill, sVa / Stichting Vervoeradres |

If you fork this repository publicly, check the redistribution terms of each form first.
