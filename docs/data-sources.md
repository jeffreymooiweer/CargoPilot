# Data sources

CargoPilot ships with reference data so that most of it works without internet access.
This page lists where each dataset comes from.

Only **factual data** is included — a UN number mapped to a code, a material mapped to a
density. Regulatory texts themselves are not in this repository.

That policy is unchanged, but one assumption behind it was wrong and worth correcting.
**ADR and ADN are published free of charge by UNECE, and RID by OTIF** — those three are
not paywalled, only the IMDG Code and the IATA DGR are. What kept them out of reach was a
network policy in the development container, not their price.
`scripts/read_land_regulations.py` therefore reads them on a CI runner and prints the
provisions the application implements to the run log, so a rule can be checked against the
text. It commits nothing: the quoted text stays in the log, and only the values read out of
it — thresholds, limits, multipliers — are stored, each with the provision it came from.

- [Goods and densities](#goods-and-densities)
- [Steel and timber profiles](#steel-and-timber-profiles)
- [Locations](#locations)
- [Dangerous goods regulations](#dangerous-goods-regulations)
- [Official form templates](#official-form-templates)
- [Which edition is running](#which-edition-is-running)
- [UN cards](#un-cards)

## Goods and densities

**1,093 goods** with densities, min/max ranges, search aliases and names in Dutch, English,
German and French, in `backend/seed/materials.json`. Each entry carries a **category** —
`liquid`, `agri`, `bulk_material`, `ore_mineral`, `metal`, `wood`, `general_cargo` and nine
others — which drives which units the goods step offers first.

| Category | Goods | Category | Goods |
|---|--:|---|--:|
| `agri` | 241 | `general_cargo` | 55 |
| `liquid` | 137 | `plastic` | 39 |
| `wood` | 111 | `waste` | 32 |
| `construction` | 103 | `bulk_material` | 28 |
| `metal` | 88 | `paper` | 21 |
| `chemical` | 67 | `insulation` | 20 |
| `ore_mineral` | 62 | `textile` | 20 |
| `food` | 61 | `concrete` | 8 |

The invariants are held by `backend/tests/test_materials_catalog.py`: no good appears
twice, no alias belongs to two goods, every good carries every supported language, every
category is one `units.py` knows, and every density lies inside its own min/max band.

**How a new good reaches an installation that already runs.** `seed_catalogs` fills the
materials table only when it is empty, so on its own it would never deliver anything to an
existing database. The startup catalogue sync does: it reads the same seed file and
*upserts*, so new goods are added and changed ones updated. Measured on a database seeded
with the old set, adding one good to the seed and restarting: `seed_catalogs` added
nothing, the sync added it. This is why `CATALOG_AUTO_SYNC=false` also freezes the goods
database at whatever it held on first start.

One thing the sync deliberately does *not* do: remove an alias. `merge_seed_material_aliases`
folds the aliases already in the database back into the record so that anything added
locally survives an update — which also means a **deletion in the seed never propagates**.
The stray `broccoli` alias on cauliflower, corrected in v1.42.0, therefore disappears on a
fresh install but stays on an existing one. It no longer does harm there: an exact match on
a good's own name now outranks another good's alias.

> **A correction.** This page used to claim that each entry states whether its figure is a
> bulk, solid, liquid or effective pallet density. It does not: there is no such field, only
> the category. That distinction matters — 20 m³ of gravel times a bulk density is right,
> 20 m³ of steel times a solid density is right, and 20 m³ of *stacked* timber is neither.
> Since v1.34.0 the application derives a density basis from the category and reports it as
> derived (`backend/app/services/units.py`), rather than treating it as something the data
> states.

**The form a good travels in is a choice, not an assumption.** Oak is 720 kg/m³ and steel
7850 — those are the densities of the *material*. A cubic metre of stacked boards, of
loose-tipped firewood and of a solid beam are three different weights of the same wood, and
the difference is air. Rather than hiding one average in the code, the line carries a
**form** and the form carries the factor:

| Form | Share of a cubic metre that is material |
|---|---|
| Solid / single piece | 1.00 |
| Sheets, lying flat | 1.00 |
| Bundled / packaged | 0.75 |
| Stacked | 0.65 |
| Loose bulk | 0.45 |

So 20 m³ of oak is 14,400 kg solid, 10,800 bundled, 9,360 stacked or 6,480 loose — the
shipper says which. The same choice applies to steel (plate against scrap), plastic
(granulate against regrind), paper and textile.

**Where the form deliberately does not apply.** For gravel, grain and ore the stored figure
is *already* a bulk density: those goods travel no other way and the database describes them
in that state. Laying a loose factor over that would subtract the air twice. The same holds
for liquids and for the effective per-pallet averages. The form is therefore only offered
where the stored number describes the substance itself.

These factors are practical figures, not standards. They live in `units.py` rather than in
the goods database because `seed_catalogs` only fills that database when it is empty — new
seed values never reach an existing installation, and a calculation that is only right for
new users is worse than none. A line with explicit length, width and height is weighed
solid regardless, because those dimensions describe actual material.

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
| Proper shipping names, English and German | The same ADR Table A export — it carries `name_en` and `name_de` per UN number |
| The eleven Table A rows ADR 2025 added (UN 0514, 3551–3560) | **ADR 2025, official Dutch edition**, table A — copied by hand, each row read twice (table A and the alphabetical index) with the page recorded. The export the rest of the table comes from is an ADR 2023 one and does not have them |
| Proper shipping names, Dutch | **ADR 2025, official Dutch edition**, table A column (2), read by `scripts/extract_adr_names.py` and cross-checked against the alphabetical index of the same edition (2,345 UN numbers, 99.9% agreement). The book itself is not in this repository; only the derived names are |
| English proper shipping names, cross-check | 49 CFR 172.101 (eCFR / GovInfo, public domain) |
| UN packaging codes (107) | ADR 6.1.2 / 6.5.1.4 / 6.6.2 |
| EmS emergency schedules per UN number, and the schedule descriptions | IMO **MSC.1/Circ.1588/Rev.3** — EmS Guide (IMO circular, freely distributable) |
| Class segregation table and class 1 compatibility matrix | IMDG Code chapter 7.2, Amendment 40-20 — unchanged in 42-24 |
| Segregation exemption tables 7.2.6.3.1 – 7.2.6.3.4 | IMDG Code chapter 7.2, Amendment 40-20 — unchanged in 42-24 |
| Segregation groups per substance (SGG1–SGG18, 629 entries) | IMDG Code chapter 3.1, section 3.1.4.4 — unchanged in 42-24; the separate SGG1a marking for strong acids was dropped in 41-22 |
| Lithium and sodium-ion batteries in aviation | [IATA Guidance Document for Lithium Batteries and Sodium ion Batteries](https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-guidance-document.pdf), 2026 edition |
| ADR 1.1.3.6 points, loading together 7.5.2, IATA Table 9.3.A, Q value | ADR 2025 (UNECE) and the IATA DGR |
| ADR 3.4.2/3.4.3 gross mass, table 3.5.1.2 E-code limits, 3.5.5 package cap, note (a) to 1.1.3.6.3 | Read from **ADR 2025 Volume I** (UNECE, ECE/TRANS/352) by `scripts/read_land_regulations.py` |
| RID 1.1.3.6.3 categories and 1.1.3.6.4 multipliers, RID 5.4.1.1.1 particulars | Read from **RID 2025** (OTIF, Appendix C to COTIF) by the same script |
| ADN 1.1.3.6.1 per-class exempted quantities and the 3,000 kg ceiling, 1.1.3.6.2 conditions | Read from **ADN 2025** (UNECE) by the same script |
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
| `backend/seed/dg/un_numbers.json` | 2,928 Table A rows over 2,336 UN numbers |
| `backend/seed/dg/adr_names_nl.json` | The Dutch proper shipping names, 2,345 UN numbers |
| `backend/seed/dg/adr_2025_additions.json` | The eleven rows ADR 2025 added, and the two it dropped |
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

> **A correction, and a number worth knowing.** This page said the folder is empty in a
> fresh checkout and is filled once by the **Fetch UN cards** workflow. That was the design;
> it is not what the repository contains. **2,849 PDFs totalling 575 MB are committed**, and
> the `Dockerfile` copies them into the image. That is roughly nine tenths of what a `docker
> pull` transfers, and it is paid by every installation on every update — including the ones
> that never open a UN card.
>
> They are not dead weight: the UN card export serves exactly these files. But whether the
> feature is worth 575 MB per pull is a decision, not a default, and it should be made
> deliberately rather than inherited from whoever committed them. Two ways out if it is not
> worth it: exclude `un_cards/` from the image and let the workflow fill a mounted volume,
> or keep only the cards for the UN numbers actually held in `card_data.json`. Neither is
> done here — this note exists so the cost is visible.

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
