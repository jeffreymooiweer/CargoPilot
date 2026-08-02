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

**400 goods** with bulk or solid densities, min/max ranges and Dutch/English aliases,
in `backend/seed/materials.json`. Each entry states whether the figure is a bulk
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
| English proper shipping names | 49 CFR 172.101 (eCFR / GovInfo, public domain) |
| UN packaging codes (107) | ADR 6.1.2 / 6.5.1.4 / 6.6.2 |
| EmS emergency schedules per UN number, and the schedule descriptions | IMO **MSC.1/Circ.1588/Rev.3** — EmS Guide (IMO circular, freely distributable) |
| Class segregation table and class 1 compatibility matrix | IMDG Code chapter 7.2, Amendment 40-20 |
| Segregation groups per substance (SGG1–SGG18, 632 entries) | IMDG Code chapter 3.1, section 3.1.4.4 |
| Lithium and sodium-ion batteries in aviation | [IATA Guidance Document for Lithium Batteries and Sodium ion Batteries](https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-guidance-document.pdf), 2026 edition |
| ADR 1.1.3.6 points, loading together 7.5.2, IATA Table 9.3.A, Q value | ADR 2025 (UNECE) and the IATA DGR |

Where the data lives:

| File | Contents |
|---|---|
| `backend/seed/dg/un_numbers.json` | 2,928 UN entries |
| `backend/seed/dg/ems.json` | 2,338 UN numbers with fire and spillage schedules |
| `backend/seed/dg/segregation_groups.json` | 18 groups, 632 substance entries |
| `backend/seed/dg/packagings.json` | 107 UN packaging codes |
| `backend/app/config/dg_compliance.json` | Segregation tables and compliance rules |
| `backend/app/config/dg_instructions.json` | Field help text |

Where internet is available, the UN lookup enriches entries live from an ADR 2025 source
and falls back to the offline database automatically.

## Official form templates

The filled-in official forms live in `templates/forms/`:

| File | Form |
|---|---|
| `cmr.pdf` | CMR consignment note, IRU model 2007 |
| `cim.pdf` | CIM consignment note, CIT CIM/CUV 2019 |
| `iata_dgd.pdf` | IATA Shipper's Declaration, open format |
| `avc.pdf` | AVC waybill, sVa / Stichting Vervoeradres |

If you fork this repository publicly, check the redistribution terms of each form first.
