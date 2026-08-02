# Changelog

All notable changes are documented here, following [Semantic Versioning](https://semver.org/).

## [1.16.0] — 2026-08-02

Columns 16a and 16b, per substance.

### Added

- **Stowage and segregation codes for 2,336 UN numbers**, read out of the UN cards by
  `scripts/extract_un_card_data.py` into `backend/seed/dg/card_data.json`. 1,242
  substances carry stowage codes (SW, column 16a) and 840 carry segregation codes
  (SG, column 16b). Nitric acid, for instance, now yields
  `SG6, SG16, SG17, SG19, SG36, SG49`.
- **Each code comes with the wording that explains it.** `SG6` on its own tells a user
  nothing; the dangerous goods step shows "Segregation as for class 5.1 (SG6). Stow
  'separated from' class 7 (SG19)." This was the last place the app had to send someone
  to the Dangerous Goods List itself.
- **Marine pollutant per substance** (column 4): 202 confirmed, 38 explicitly not, and
  the rest marked as depending on the actual substance — which is what the source says
  for n.o.s. entries, and is reported as such rather than guessed either way. A confirmed
  marine pollutant now fills the field on the IMO and IMDG documents by itself.
- **Bulk carriage**: the 28 substances that may travel in bulk, with their BK instruction.

### Verification

The extraction read its own EmS code from every card and compared it with `ems.json`,
which comes from the official EmS Guide: **2,282 agreed and none disagreed**. Two
independent sources for the same field arriving at the same answer is a good sign for
both of them. The EmS Guide remains the authority; the card reading is only a check.

### Removed

- The **Fetch UN cards** workflow. It was a one-off and its work is done. Both scripts
  stay, so a future edition of the IMDG Code is a matter of running them again — see
  [docs/development.md](docs/development.md#the-un-cards).

## [1.15.0] — 2026-08-02

The UN card library is in.

### Added

- **2,849 UN cards covering 2,336 UN numbers** in `un_cards/`, fetched from Cantell's
  IMDG UN cards (2023 edition, IMDG 41-22). Every one of the 2,900 source files was
  opened and the UN number read out of the card itself, because the source numbers its
  files sequentially with no relation to their contents. 2,703 were confirmed by both the
  number and the shipping name, 146 by the number alone, and **none** contradicted itself
  or fell out of sequence. A sample of twelve was checked by hand against the filename:
  twelve correct.
- The 2,336 unique UN numbers match `backend/seed/dg/un_numbers.json` exactly. The extra
  513 cards are second and third entries for the same UN number, which the regulations
  give a separate card per packing group; all of them are handed to the user.
- **The download option in the export now works.** A shipment with dangerous goods gets a
  zip with the cards for the substances it declared. It was built in 1.14.0 but stayed
  hidden while the library was empty.

### Changed

- Parts 2850 to 2900 of the source are the card layout with every field empty. They carry
  no substance and are not included; `manifest.json` records that they were seen.
- The fetch workflow no longer fails when it cannot open a pull request — that needs a
  repository setting, and the pushed branch is the deliverable either way. It prints the
  compare link instead.

### Note on size

`un_cards/` is 581 MB on disk but **49 MB packed**: every card embeds the same seven
fonts, so git's delta compression collapses them, and the Docker layer compresses the
same way. A clone and an image pull stay small; the unpacked container grows by ~580 MB.

## [1.14.1] — 2026-08-02

### Changed

- **The UN card fetcher now reads the card's own `UN number` field.** The real cards
  (Cantell's IMDG UN cards, 2023 edition) are laid out as label/value pairs and repeat
  the number in the footer, which is far more reliable than judging by font size. Both
  are read and must agree; a card that contradicts itself is parked for a human instead
  of being filed on a coin flip. The previous heuristic — prominence plus shipping-name
  match — remains as the fallback.
- The source URL is filled in as the workflow's default, and the parts are checked for
  ascending UN order so a card that steps backwards is flagged even when it read cleanly.

## [1.14.0] — 2026-08-02

UN cards for your own records.

### Added

- **Download the UN cards for your substances** at the end of the wizard. A shipment
  with dangerous goods gets a zip with one reference card per UN number it declared —
  only those, not the whole library — plus a README stating what is in it and which
  declared substances no card is held for. The cards are reference material for the
  user's own file; they are not transport documents and are attached to nothing.
  New endpoints: `POST /api/documents/un-cards` and
  `POST /api/documents/un-cards/availability`.
- **A workflow to fetch the card library** (`.github/workflows/fetch-un-cards.yml`).
  The source numbers its files sequentially — `part1`, `part2`, … — with no relation to
  the UN number on the card, so the workflow opens every document, reads the UN number
  out of the contents and saves it as `un_1033.pdf`.
- The identification is deliberately cautious. A four-digit number only counts if it is
  a real entry in the UN database, prominence on the page is weighed so a page number or
  a cross-reference cannot outrank the card's own heading, and a card is marked
  `confirmed` only when the shipping name printed on it matches the name we hold for
  that number. Anything weaker goes to `un_cards/_unidentified/` for a human to look at,
  and `un_cards/manifest.json` records what happened to every part. A card filed under
  the wrong UN number would hand someone the emergency information for a different
  substance, so the script skips rather than guesses.
- If the card library is absent — any fork that has not run the workflow — the download
  option simply does not appear.

## [1.13.2] — 2026-08-02

Documentation rewritten, in English, and split up.

### Changed

- **The README is now about the app, not about everything.** It says what CargoPilot is,
  what it does for you and how to start it, and links onward. Installation instructions,
  environment variables, data provenance and developer setup have moved into `docs/`.
- **All documentation is in English**, including the changelog and the roadmap.
- **New guides in `docs/`**: [getting started](docs/getting-started.md),
  [user guide](docs/user-guide.md), [documents](docs/documents.md),
  [dangerous goods](docs/dangerous-goods.md), [configuration](docs/configuration.md),
  [data sources](docs/data-sources.md), [privacy](docs/privacy.md) and
  [development](docs/development.md).
- Badges on the README for Docker pulls, the latest release, build status, development
  status, licence, image size and stack.
- The disclaimer is now available in English as `DISCLAIMER.md`. The Dutch text remains
  the legally binding version and has moved to `DISCLAIMER.nl.md`; the two link to each
  other.

### Fixed

- **`GET /api/health` reported the wrong version.** `backend/VERSION` takes priority over
  the repository root `VERSION`, and it had been left at 1.13.0. Both are now bumped
  together, and a test fails if the root `VERSION`, `backend/VERSION` and
  `frontend/package.json` ever drift apart again.
- The transport mode tiles still advertised "internal forms" — a leftover from the
  military form removed in v1.4.0 — and a separate ADR document that no longer exists
  since v1.13.0. Road now reads "CMR and AVC waybill, packing list and delivery note",
  inland waterway "ADN document, VGM and packing list".

## [1.13.1] — 2026-08-02

The AVC waybill now fills in the official form.

### Changed

- **The AVC waybill is no longer redrawn — it is filled in.** The official waybill form
  from sVa / Stichting Vervoeradres now ships as `templates/forms/avc.pdf` and is filled
  in by the backend, just like the CMR, the CIM and the IATA declaration. The previous
  version redrew the form with reportlab; the result looked like the original but was
  not one.
- Unlike the CMR, the AVC form has no PDF form fields (AcroForm), so the values are
  placed as a text layer over the template. The positions are derived from the form's
  own ruling and field labels: sender, delivery address, franking instruction with the
  Franco / Not franco checkboxes, carrier, the goods table with its number, packaging,
  contents and weight columns, the totals, and the place and date of dispatch — in both
  the waybill and the receipt panel.
- The ADR description (5.4.1.1.1) stays in the "contents" column, and the total per
  transport category (5.4.1.1.1.1) now appears under the last goods line instead of in
  the footer. Text too long for a column is wrapped on actual text width, so the
  "contents" column no longer runs into "weight in kg".
- The AVC waybill therefore also gets the **Official form** label in the form overview.

## [1.13.0] — 2026-08-02

An AVC waybill in place of a separate ADR road document.

### Added

- **AVC waybill** for domestic road carriage, generated as a PDF following the standard
  sVa / Stichting Vervoeradres model: the waybill on the left, the receipt on the right,
  with the same box layout (sender, delivery address, franking instruction with Franco /
  Not franco, carrier, goods table with number, packaging, contents and weight, totals,
  place and date of dispatch). The reference clause makes the **Algemene
  Vervoercondities 2002** applicable. The carrier's signature and the consignee's receipt
  stay blank; the sender can have their own signature placed.

### Changed

- **The CMR now carries the dangerous goods data itself.** For a package containing
  dangerous goods, the official description under ADR 5.4.1.1.1 goes into boxes 6–12
  (`UN 1203, GASOLINE, 3, II, (D/E), 10 jerrycan, 200 L`) instead of the free
  description, and box 13 gets the total quantity per transport category (5.4.1.1.1.1).
  Packages without dangerous goods keep their normal description, and the mass is not
  counted twice.
- The same applies to the AVC waybill: the ADR description appears in the "contents"
  column.

### Removed

- **The separate ADR transport document for road has been dropped.** ADR 5.4.1
  prescribes no form for the transport document: a waybill carrying the data of
  5.4.1.1.1 is sufficient. Now that the CMR and the AVC waybill contain that description
  themselves, a separate document is redundant. The ADN transport document for inland
  waterways remains, because there is no waybill for that mode in the app.

## [1.12.0] — 2026-08-01

Segregation groups per substance, from the official IMDG Code.

### Added

- **All eighteen segregation groups with their substances** (IMDG 3.1.4.4): 632 entries
  across 539 UN numbers, from acids and alkalis to cyanides, azides, permanganates,
  metal powders and mercury compounds. The 21 **strong acids** get the separate SGG1a
  marking. A substance can fall into several groups — lead azide (UN 0129) belongs to
  heavy metals, lead *and* azides at once.
- **Segregation group straight from the UN number**: as soon as a UN number is entered,
  the app shows the applicable groups, for example "SGG1 (Acids), SGG1a (strong acids)"
  for hydrochloric acid.
- **Incompatible segregation group checks** in the compliance panel for sea freight.
  Reported combinations include acids with alkalis, acids with cyanides (hydrogen
  cyanide), acids with chlorites or hypochlorites (chlorine dioxide and chlorine gas
  respectively), acids with nitrites, acids with azides (explosive hydrazoic acid), acids
  with metal powders (hydrogen evolution) and peroxides with acids. Manually entered
  group codes are taken into account.

## [1.11.0] — 2026-08-01

EmS emergency schedules, complete, from the official EmS Guide.

### Added

- **All 2,338 UN numbers from the EmS Guide.** The index of IMO MSC.1/Circ.1588/Rev.3
  (*Revised Emergency Response Procedures for Ships Carrying Dangerous Goods*) has been
  taken over in full. Coverage goes from 12.9% to **99.5% exact codes**; only a handful
  of entries not present in the guide still fall back on an indicative class default.
- **A description with every code**: all ten fire schedules (F-A Alfa "general fire
  schedule" through F-J Juliet) and all 26 spillage schedules (S-A Alfa "toxic
  substances" through S-Z Zulu "toxic explosives") are included in Dutch and English.
  The app now shows "F-E (Flammable liquids that do not react with water) · S-E
  (Flammable liquids that float on water)" instead of just the code.
- **A schedule per packing group**: 43 UN numbers have a different emergency schedule per
  packing group — UN 1826 (nitrating acid mixture), for instance, is treated as oxidising
  (S-Q) in packing group I and corrosive (S-B) in group II. Without a known packing
  group, the app shows both options rather than guessing one.
- **Variants with their own schedule**: UN 3166 (vehicles) gets a different schedule for
  gas than for liquid propulsion; both are shown.
- **Air freight rules updated** to the IATA Guidance Document for Lithium Batteries and
  Sodium ion Batteries, 2026 edition: the 30% state-of-charge limit under PI 965 with the
  approval route of special provision A331, the CAO label for UN 3090/3480, approval
  route A201, and newly the **sodium-ion batteries** UN 3551 (PI 976) and UN 3552 (PI
  977/978) — with the caveat that sodium-ion batteries with an aqueous alkaline
  electrolyte fall under UN 2795. The battery-powered vehicles UN 3556, 3557 and 3558 are
  included as well.

### Changed

- The EmS data no longer comes from a curated selection but straight from the official
  guide. During the transfer, 13.5% of the earlier curated entries turned out to deviate
  (39 out of 288), mostly oxidisers that are F-H rather than F-A and temperature-controlled
  peroxides that fall under F-F. All of those are now correct.

## [1.10.0] — 2026-08-01

Segregation verified against the official IMDG Code and extended with segregation groups
and class 1.

### Changed

- **Segregation table verified and updated to Amendment 40-20.** The table was compared
  line by line with chapter 7.2 of the official IMDG Code. 287 of 289 cells were already
  correct; four cells were updated because Amendment 40-20 is stricter than the older
  edition the previous version relied on:
  - class 2.1 × 4.3: from "no general segregation" to **2 (separated from)**
  - class 3 × 4.3: from 1 (away from) to **2 (separated from)**
  - class 2.2 × 5.2: from 2 to **1 (away from)**

  The table is now pinned verbatim in a test, so a future change cannot slip through
  unnoticed.

### Added

- **Segregation groups (IMDG 7.2.5)**: all nineteen groups SGG1 through SGG18 (acids,
  strong acids, ammonium compounds, bromates, chlorates, chlorites, cyanides, heavy
  metals, hypochlorites, lead, halogenated hydrocarbons, mercury, nitrites, perchlorates,
  permanganates, metal powders, peroxides, azides and alkalis) are included as reference
  in the compliance panel, with the explanation that column 16b of the Dangerous Goods
  List determines whether a substance belongs to one, and that for n.o.s. entries the
  shipper assesses this themselves (5.4.1.5.11).
- **Exception for class 8 (IMDG 7.2.6.5)**: acids and alkalis of packing group II or III
  may nonetheless travel together in one cargo transport unit in packages up to 30 L or
  30 kg, provided the substances do not react dangerously and the transport document
  carries the statement of 5.4.1.5.11.3.
- **Loading compatibility check for explosives (IMDG 7.2.7.1.4)**: the full compatibility
  group matrix A through S now determines whether class 1 packages may share a space or
  cargo transport unit. Group S is compatible with everything except L; group L only with
  its own type; the special provisions for groups G (fireworks), L and N are shown as
  warnings. The exception of 7.2.7.2.1 (ammonium nitrate and nitrates together with
  explosives, except UN 0083) is included.
- **A subsidiary class 1 risk counts as division 1.3** when determining segregation (IMDG
  7.2.3.3), which is stricter than the primary hazard alone.

## [1.9.0] — 2026-08-01

EmS database extended and carriage prohibitions flagged.

### Added

- **EmS emergency schedules extended from roughly 90 to 305 UN numbers** in a dedicated
  data file (`backend/seed/dg/ems.json`), grouped by hazard profile: flammable, toxic,
  oxidising and inert gases, flammable liquids (distinguishing those that float on water
  from the rest), flammable and pyrophoric solids, water-reactive substances, oxidising
  substances and ammonium nitrate, organic peroxides, toxic and infectious substances,
  radioactive material, corrosives (including the corrosive-and-oxidising combinations),
  environmentally hazardous substances and lithium batteries. Each entry shows the
  profile ("Flammable liquid that floats on water"), so it is visible *why* that schedule
  applies.
- **Carriage prohibition flagging**: fourteen substances that ADR Table A does not permit
  for carriage (including UN 1798 aqua regia, UN 2249 symmetrical dichlorodimethyl ether,
  UN 2186 refrigerated hydrogen chloride and several n.o.s. entries with incompatible
  hazards) are recognised. The dangerous goods step shows a red block and export of
  transport documents is refused; carriage is only possible with an exemption from the
  competent authority.
- Explanation for articles containing dangerous goods (UN 3537 through 3548) about
  labelling under 5.2.2.1.12.

### Fixed

- **German source data leaked into forms.** For prohibited substances, ADR Table A fills
  *every* column with the text "BEFÖRDERUNG VERBOTEN". That ended up in the packing group,
  the limited quantity, and even the description line of the transport document
  (`UN 1798, NITROHYDROCHLORIC ACID, 8, BEFÖRDERUNG VERBOTEN`). All columns are now
  filtered; the prohibition is shown only as a warning.
- The EmS fallback did not account for the division: gases got no indication on the basis
  of class "2". The division from the labels column is now used first (2.1 → F-D/S-U,
  2.2 → F-C/S-V, 2.3 → F-C/S-U), so nearly every UN number gets a usable emergency
  schedule.

### Known limitation

The EmS data is a curated compilation: nine entries were checked against public sources
while compiling and marked as such; the rest follow the substance's hazard profile. For
UN numbers without an exact entry, the app shows an indicative class default, presented
recognisably as a suggestion and not filled in automatically. The current IMDG edition
remains the authority.

## [1.8.0] — 2026-08-01

Dangerous goods: automatic completion per transport mode, and sea segregation.

### Added

- **Automatic completion of dangerous goods data** (`POST /api/dg/prepare`): you enter
  only the UN number per package (or search by substance name) and CargoPilot derives the
  proper shipping name, class, subsidiary risks, packing group, packing instruction,
  transport category, tunnel code, Kemler number and LQ/EQ limits. Number of packages,
  packaging type and masses are taken from the packages already entered. Only empty fields
  are filled, so manual corrections always survive.
- **EmS emergency schedules for sea transport**: the EmS code (fire and spillage schedule)
  is filled in per UN number for a curated selection of commonly carried substances from
  the IMDG Dangerous Goods List; for other substances an indicative class default is shown
  and marked as such.
- **Air freight rules**: lithium batteries UN 3090/3480 are automatically marked **Cargo
  Aircraft Only** with the correct IATA packing instruction (PI 965/968), UN 3091/3481 get
  PI 966/967 and 969/970 respectively, and class 2.3 (toxic gases) is reported as
  forbidden in aviation.
- **Official description lines per form** are assembled automatically and shown before
  export: ADR/RID/ADN under 5.4.1.1.1 including tunnel code, number of packages and total
  quantity; IMDG with EmS code and marine pollutant; IATA with packing instruction and
  Cargo Aircraft Only.
- **Total quantity per transport category** (ADR 5.4.1.1.1.1) is calculated and placed on
  the generated ADR/RID/ADN documents — mandatory when using the 1.1.3.6 exemption, and
  until now manual work.
- **IMDG segregation check (7.2.4)**: the full class segregation table is included, with
  codes 1 through 4 ("away from", "separated from", "separated by a complete compartment
  or hold", "separated longitudinally") and their distances. Subsidiary risks count; for
  sea freight, conflicts appear in the compliance panel.
- **Excepted and limited quantities** are explained in plain language (E1 through E5 with
  the maxima per inner and outer packaging under 3.5.1.2, and the LQ limit per inner
  packaging under 3.4).
- **Class-specific document requirements** are named: net explosive mass and compatibility
  groups for class 1, temperature control for self-reactive substances and organic
  peroxides, the responsible person for class 6.2, and radionuclides, package category,
  transport index and criticality safety index for class 7. Sea freight gets the container
  packing certificate, air freight the signature in duplicate.
- **Versioning policy** written down explicitly: patch releases for corrections, minor for
  new functionality, major only for major overhauls.

### Fixed

- **The ADR classification code was wrongly entered as a subsidiary risk.** When choosing
  a UN number, the classification code (for example `F1` for gasoline, `M4` for lithium
  batteries or `C1` for sulphuric acid) ended up in the "subsidiary risk" field, so the
  description on the transport document read `UN 1203, GASOLINE, 3 (F1), II` instead of
  `UN 1203, GASOLINE, 3, II`. Subsidiary risks are now read correctly from the labels
  column of ADR Table A: UN 2031 (nitric acid) now correctly yields `8 (5.1)`, and
  gasoline no longer yields a subsidiary risk. The classification code is stored
  separately.
- **The division of gases and explosives** is now determined correctly: ADR Table A lists
  only class "2" for gases and "1" for explosives, while the actual division sits in the
  labels column (2.1/2.2/2.3) or the classification code (1.4S). This drives loading
  compatibility and segregation, which could previously be incomplete.
- The IATA description showed the ADR packing instruction (P001, IBC02), which is not
  valid for air freight; an IATA packing instruction is now shown only where one is known.
- The button to download a document was still labelled **"Download Excel"** while all
  documents are exported as PDF; it now reads "Download document".
- Two missing translation keys showed raw text in the interface: the paste field in the
  import dialog had no placeholder, and inactive equipment showed `questions.no` (a
  leftover from the removed internal form) instead of "Inactive".
- The explanation on the dangerous goods step still described the old approach (fill in
  everything by hand, UN data online only) and has been brought in line with automatic
  completion from the offline database.

## [1.7.0] — 2026-07-31

Goods database extended to 400 transport goods.

### Added

- **Goods database extended from 159 to 400 goods** with bulk and solid densities,
  min/max ranges and Dutch/English aliases, across the whole transport spectrum:
  - **Construction and natural stone**: basalt, bluestone, travertine, quartzite,
    porphyry, track ballast, screed mortar, tile adhesive, concrete blocks, kerbstones,
    paving bricks, gypsum plaster, silver sand, dolomite, chalk, loam, roofing rolls,
    bagged cement, wet ready-mix concrete, rubble stone
  - **Insulation**: perlite, vermiculite, foam glass, wood fibre board, cellulose blow-in
  - **Metals**: pure iron, chromium, manganese, tungsten, molybdenum, cobalt, silver,
    gold, platinum, antimony, cadmium, bismuth, silicon, zamak, cemented carbide
    (tungsten carbide), mercury, ferrosilicon
  - **Timber and sheet material**: pine, poplar, alder, maple, walnut, cherry, hornbeam,
    elm, chestnut, lime, iroko, sapele, bangkirai, padauk, wengé, accoya, western red
    cedar, robinia, thermally modified wood, OSB, MDF, HDF, hardboard, softboard, glulam,
    cross-laminated timber (CLT), cork, round timber
  - **Fuels, chemicals and gases**: crude oil, naphtha, heating oil, biodiesel (FAME),
    HVO, solvents (toluene, xylene, benzene, styrene, MEK, IPA, ethyl acetate, white
    spirit/turpentine), acids (acetic, nitric, phosphoric), hydrogen peroxide, ammonia
    solution, glycerine, vegetable oils by type (olive, palm, sunflower, rapeseed,
    linseed), bitumen emulsion, spirits, and liquefied gases (LNG, propane, butane, CO₂,
    nitrogen, oxygen, argon, hydrogen, anhydrous ammonia)
  - **Fertilisers and solid chemicals**: ammonium nitrate, ammonium sulphate, DAP/MAP/TSP,
    kieserite, UAN, calcium chloride, citric acid, washing powder, activated carbon,
    carbon black, titanium dioxide, zinc oxide, starch, vacuum salt, sodium bicarbonate,
    paraffin, bleach lye, iron chloride, epoxy resin
  - **Agricultural**: spelt, buckwheat, millet, sorghum, quinoa, linseed, pulses (peas,
    beans, lentils, chickpeas), feed materials (soybean meal, rapeseed meal, sunflower
    meal, palm kernel expeller, beet pulp pellets, DDGS, alfalfa pellets, fish meal),
    silage, slurry and solid manure, compost, tree bark, wood shavings, potting soil,
    grass seed, mustard and sesame seed, peanuts, hop pellets, tobacco and tea
  - **Fruit and vegetables** (effective density in crates and boxes): bananas, oranges,
    lemons, pears, grapes, melons, strawberries, tomatoes, cucumbers, peppers, leeks,
    cauliflower, cabbage, carrots, mushrooms
  - **Foodstuffs**: table salt, pasta, oats, milk and whey powder, butter, cheese, honey,
    chocolate, cocoa butter, roasted coffee, bottled water, sugar syrup, vinegar
  - **Ores and energy**: copper and zinc concentrate, chrome ore, manganese ore, nickel
    ore, phosphate rock, ilmenite, barite, bentonite, kaolin, feldspar, olivine, rock
    salt, petroleum coke, lignite, anthracite, alumina, slaked lime
  - **Plastics, paper and textiles**: solid polystyrene, ABS, polycarbonate, PET, PTFE,
    PUR foam, rubber granulate, copy paper, newsprint, tissue, books, wool, flax and
    carpet goods, clothing
  - **Waste and recycling**: RDF bales, e-waste, incinerator bottom ash, green waste,
    sewage sludge, used cooking oil, mixed plastic waste
  - **General cargo practical averages**: empty pallets and crates, machinery on skids,
    white goods, lead-acid batteries, cable drums, sanitary ware, fasteners, mattresses,
    bicycles
- Every entry states whether the figure is a bulk density, solid density, liquid density
  or an effective pallet density

### Changed

- Overly broad aliases have been moved to more specific goods (for example "olive oil"
  from generic vegetable oil to olive oil, "potting soil" from peat to potting soil,
  "slaked lime" from quicklime to lime hydrate), so recognition and density are more
  accurate
- All aliases are guaranteed unique across the whole database, so a description always
  resolves to exactly one entry
- Existing installations pick up the new goods automatically at the next catalogue sync,
  which by default runs at startup

## [1.6.0] — 2026-07-25

Signatures on documents, and a complete offline UN and packaging database.

### Added

- **Draw, upload or skip a signature**: on the shipment details step the sender can draw
  a signature (mouse, finger or stylus, with smooth lines, undo and clear) or upload an
  image (PNG/JPEG/WebP; a white background is made transparent automatically and the
  signature is trimmed tightly). The signature is placed in the sender's box of the
  documents: CMR box 22 (all four copies), the signature field of the IATA Shipper's
  Declaration, and a proper signature section on all generated PDFs. Skipping remains
  possible at all times, to sign physically with a pen. Carrier and consignee signatures
  (CMR boxes 23/24, CIM box 61, delivery note receipt) always stay blank.
- **UN number autocomplete**: when entering a UN number or substance name, suggestions
  appear straight away from an **offline database of 2,928 ADR entries** (class,
  classification code, packing group, labels, limited and excepted quantities, packing
  instructions, transport category, tunnel code and Kemler number from ADR Table A;
  English substance names from the official US 49 CFR 172.101 table). One click fills the
  proper shipping name, class, packing group, packing instruction, transport category and
  tunnel code; where internet is available, the existing ADR 2025 lookup enriches the data
  live. New endpoint: `GET /api/dg/search`.
- **Packaging database**: all 107 UN packaging codes under ADR 6.1.2/6.5.1.4/6.6.2 (drums,
  jerricans, boxes, bags, composite packagings with plastic or glass inner receptacles,
  metal, flexible, plastic and composite IBCs such as big bags and 1000-litre totes, large
  packagings and pressure receptacles) with Dutch/English descriptions and a liquid/solid
  indication. The packaging field on the dangerous goods step is now a searchable list;
  free text remains possible. New endpoint: `GET /api/dg/packagings`.
- The UN lookup (`GET /api/dg/lookup`) falls back to the offline database automatically
  when the external ADR source is unreachable — the dangerous goods step now works fully
  offline.

### Changed

- Form texts clarified: carrier and consignee signatures are never pre-filled; the
  sender's signature is only placed when the user draws or uploads one.

## [1.5.0] — 2026-07-25

One wizard for all forms, location and address autocomplete, and a transport-wide goods
database.

### Added

- **Forms sub-wizard**: after entering packages there is one continuous wizard — first the
  **shipment details** (parties, route, references) which are entered once and reused in
  *all* selected forms, then a step per form ("Form x of y") with only the fields that
  form still needs. Steps are directly clickable and show a green or orange dot for
  whether all required fields are filled; forms without their own fields are listed as
  "covered by the shipment details".
- **Address autocomplete**: address fields (sender, consignee) can search and fill an
  address automatically via a Photon geocoder on OpenStreetMap data (configurable with
  `GEO_ADDRESS_API_URL`; goes quiet without internet access, manual entry always remains
  possible). New endpoint: `GET /api/geo/address`.
- **Location autocomplete for airports, ports and railway stations**: route fields (place
  of loading, place of discharge, receipt/delivery, final destination) search live in
  bundled open datasets — 4,500+ airports with IATA/ICAO code (OurAirports), 17,500+ ports
  with UN/LOCODE (UNECE) and 750+ European main stations (Trainline EU). The right kind is
  suggested per mode (air → airports, sea and inland waterway → ports, rail → stations,
  road and multimodal → everything plus addresses). New endpoint: `GET /api/geo/locations`.
  Free text remains allowed at all times.
- **Goods database greatly extended**: from 18 to **159 goods** with bulk and solid
  densities and Dutch/English aliases — construction materials (cement, sand-lime brick,
  brick, roof tiles, natural stone, asphalt, aggregates, insulation), metals and scrap,
  timber species and timber products, fuels and liquids (diesel, kerosene, lubricating
  oil, acids, AdBlue), chemicals and fertilisers, agricultural bulk (grain, seed,
  potatoes, animal feed, hay and straw, coffee, cocoa), foodstuffs and drinks, paper and
  packaging, ores and energy (iron ore, coal, coke), recycling and waste streams, textiles
  and general cargo practical averages (pallets, parcels, furniture).
- Catalogue search now also shows goods directly as a **material suggestion with density**
  (for example "Wheat — 780 kg/m³"), alongside the existing profile and equipment results.
- **Weight calculation for block-shaped goods**: a recognised material with three
  dimensions is now calculated as a solid block on density (for example "brick
  100x100x100cm" → 1,900 kg), even without an explicit product type such as sheet or beam.

### Changed

- The "Shipment details" step keeps its name in the progress bar but now contains the
  sub-wizard with its own navigation; duplicate entry of the same data across forms is
  gone entirely.
- New environment variables: `GEO_ADDRESS_API_URL` and `GEO_ADDRESS_TIMEOUT_SECONDS`.

## [1.4.0] — 2026-07-13

CargoPilot is fully civilian: military forms removed.

### Removed

- The internal military form has been removed completely: the wizard step with its
  questions, the Excel template, the export endpoints, the PDF rendering and all
  references in the interface. Military use gets a separate private fork (CargoPilot MIL)
  with its own forms.
- Military flags and help texts (weapons, ammunition, ITAR, TBB) and external references
  to defence portals
- Older Docker images still contain the form; these are removed through the Docker Hub tag
  cleanup

### Changed

- **Package entry**: the "Review" step is now called **Packages**; each package can be
  ticked as containing dangerous goods. A tick (or a recognised UN number) automatically
  brings up the dangerous goods step.
- The dangerous goods step, UN detection, ADR/IATA compliance checks and all transport
  documents are fully retained
- Per mode, the primary transport document is pre-selected (road: CMR, rail: CIM, air: AWB
  instructions, sea: B/L instructions)

## [1.3.0] — 2026-07-13

Dangerous goods compliance guidance (ADR and IATA).

### Added

- **ADR 1.1.3.6 points calculator (the 1,000-point rule)**: transport category (0–4) and
  total quantity per DG product; automatic calculation with factors ×50/×3/×1/×0, verdicts
  "exemption possible", "over 1,000 points", "category 0 — no exemption" and "incomplete",
  including an explanation of what the exemption releases you from and what remains
  mandatory
- **Loading compatibility check ADR 7.5.2**: warning for class 1 (other than 1.4S)
  together with other classes, different compatibility groups within class 1 (7.5.2.2) and
  the CV28/7.5.4 separation of foodstuffs (labels 6.1/6.2 and class 9 UN
  2212/2315/2590/3151/3152/3245)
- **IATA segregation (Table 9.3.A)**: check on incompatible packages (class 1 excluding
  1.4S × 2.1/3/4.1/5.1; class 8 × 4.3) including subsidiary risks, plus the lithium
  battery rule (UN 3090/3480 separated from 1/2.1/3/4.1/5.1)
- **IATA Q value (5.0.2.11)**: automatic calculation of Q = Σ n/M, rounded up to one
  decimal, with a warning above 1.0
- **Compliance panel** on the dangerous goods step and in the export summary, with source
  references (ADR 2025, IATA DGR 67th edition) and a recalculate button
- New DG fields with help text: ADR transport category, total quantity (1.1.3.6.3 units),
  net per packaging and max. net per packaging (Q); the UN lookup fills the transport
  category where the ADR database provides it
- Cargo Aircraft Only flagging towards the Shipper's Declaration and AWB handling
  information
- New endpoint: `POST /api/dg/compliance`; rule configuration in
  `backend/app/config/dg_compliance.json`

## [1.2.0] — 2026-07-12

Multimodal transport selection.

### Added

- **Transport mode selection at the start**: a tile screen with road, rail, sea, inland
  waterway, air and multimodal (separate illustrations for light and dark theme)
- **Form selection as the first wizard step**: only relevant forms per mode; with
  multimodal, all forms selectable
- **Document registry** (`backend/app/config/document_registry.json`) with field
  definitions and field statuses (`USER_REQUIRED`, `CONDITIONAL`, `CARRIER_PROVIDED`,
  `OPERATIONAL`, `SIGNATURE_REQUIRED`, …)
- **All documents are now downloaded as PDF.**
- **Official fillable PDF forms filled in**: the **CMR consignment note** (IRU model 2007,
  4 copies), the **IATA Shipper's Declaration** (open format) and the **CIM consignment
  note** (CIT CIM/CUV, 2019 edition) are filled in as the original, fillable PDF templates
  — including correct box numbering, IATA column order and "delete non-applicable"
  strikethrough. Signature fields stay blank.
- **Self-designed documents as clean PDFs** (reportlab): packing list, delivery note, IMO
  Multimodal Dangerous Goods Form, VGM declaration, AWB/B-L Shipping Instructions and the
  ADR/ADN transport document — with parties, goods table, DG table per profile, fixed legal
  texts and a disclaimer.
- **New documents**: CMR (PDF), IATA (PDF), CIM (PDF), IMO Multimodal DG Form, VGM
  declaration (method 1/2 with a total cross-check), AWB Shipping Instructions, B/L or Sea
  Waybill Shipping Instructions, ADR/ADN transport document, packing list and delivery note
- **Legal disclaimer**: a separate disclaimer page in the app (NL/EN), `DISCLAIMER.md`, a
  draft warning on export and a disclaimer in the metadata and footer of generated
  documents. Liability fully excluded; Apache License 2.0 with Commons Clause named
  explicitly.
- Official regulations and fixed legal texts (CMR paramount clause, IATA
  certification/WARNING, IMO declaration, VGM SOLAS reference, ADR 5.4.1 description line)
  plus links to the official source templates per document
- **Shipment details step**: shared blocks (parties, route, references) are entered once
  and reused in all selected documents
- **Document statuses in the summary**: ready for export, draft, waiting for carrier data,
  blocked by safety validation, not applicable
- **Dangerous goods validation per mode** (ADR/RID/ADN/IMDG/IATA DGR): export of DG
  declarations is blocked on incomplete classification (UN number, proper shipping name,
  class; for IATA also packing instruction, packages and quantity)
- Extra DG fields on IMO/IATA forms: technical name, marine pollutant, Cargo Aircraft Only,
  overpack, emergency contact, EmS code
- New API endpoints: `GET /api/documents/registry`, `POST /api/documents/validate`,
  `POST /api/documents/export`

### Changed

- The wizard starts with the form selection
- Signature, carrier and operational fields are never pre-filled; they are marked as such
  in the export
- Navigation: the starting point is called "New shipment" and begins at the mode selection
- The wizard progress bar shows icons instead of text on mobile (more steps fit on screen)

## [1.0.0] — 2026-07-11

First stable release.

### Added

- Wizard: review-first flow with a material catalogue and synonyms
- Dangerous goods with ADR UN lookup
- Equipment overview: management, import via template (.xlsx/.csv/.txt)
- Wizard import: paste and file upload with a template
- Weight per line editable; total weight proportionally scalable in the summary
- Automatic catalogue sync (materials, profiles) from public sources
- Dark mode, NL/EN interface, Docker and Unraid deployment

### Changed

- Semantic versions from v1.0.0 onwards (`VERSION`, Docker tags `v*`, health endpoint)
- The equipment library starts **empty**; no pre-filled operational data in the repository
  or the image

### Removed / privacy

- Pre-filled equipment list (`equipment_overview.json`) removed from the codebase and the
  Docker build
- On startup, legacy items with the source `overzicht_materieel` are removed from existing
  databases
- Stale built frontend assets in `backend/static/` (the build happens in Docker)
