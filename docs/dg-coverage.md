# Dangerous goods: what CargoPilot covers, per mode

An assessment of the dangerous goods functionality against what the five transport
regimes ask of a consignor, written to answer one question honestly: **where would someone
relying on this application be caught out?**

- [How to read this, and what it is not](#how-to-read-this-and-what-it-is-not)
- [The three questions a consignor has to answer](#the-three-questions-a-consignor-has-to-answer)
- [What is held, per substance](#what-is-held-per-substance)
- [Road — ADR](#road--adr)
- [Rail — RID](#rail--rid)
- [Inland waterway — ADN](#inland-waterway--adn)
- [Sea — IMDG](#sea--imdg)
- [Air — IATA DGR](#air--iata-dgr)
- [Gaps ranked by what they cost](#gaps-ranked-by-what-they-cost)
- [What should and should not be built](#what-should-and-should-not-be-built)

## How to read this, and what it is not

Two columns run through this document. They do not have the same standing and it would be
dishonest to present them as if they did.

**What CargoPilot does** is established from the code and the data in this repository.
Every claim in that column was read out of `backend/app/services/dg/`,
`backend/app/config/` or `backend/seed/dg/` while writing this, not remembered.

**What the regime requires** now splits in two, and the split matters more than anything
else in this document.

**For road, rail and inland waterway it has been read.** Earlier versions of this
assessment said the regulatory texts were out of reach. That was wrong, and the error was
costly enough to be worth naming: **ADR and ADN are published free of charge by UNECE and
RID by OTIF.** All four PDFs are the official legal texts and cost nothing. What was
actually missing was a network route from the development container — not the documents.
`scripts/read_land_regulations.py` fetches them on a runner and quotes the provisions the
application implements, so a claim about ADR, RID or ADN can be checked against the text
rather than against someone's memory of it. Where this document now names a figure for
those three regimes, it was read from:

| Text | Publisher | Edition |
|---|---|---|
| ADR 2025, Volumes I and II (ECE/TRANS/352) | UNECE | in force 1 January 2025 |
| RID 2025 (Appendix C to COTIF, Annex) | OTIF | in force 1 January 2025 |
| ADN 2025 | UNECE | in force 1 January 2025 |

**For sea and air it has not.** The IMDG Code is sold by the IMO and the DGR by IATA;
there is no free official text to read. Those two sections are still written from knowledge
of how the regimes are structured, and are reliable at the level of *which chapter governs
what*, not at the level of an exact limit or table value. The standing policy in
[Data sources](data-sources.md) is unchanged either way: no regulatory text is
redistributed here, only the factual values read out of one.

The practical consequence:

> **A rule implemented from memory is worse than no rule, because it looks like an answer.**
> For IMDG and the DGR that constraint still binds, and every statement about them below is
> marked **[verify]**. For ADR, RID and ADN it no longer does — and reading them turned up
> two things the application had been getting wrong, both described in their own sections.

Where a statement about sea or air is one I would want checked before anyone leans on it,
it is marked **[verify]**. Statements about the three land regimes carry their provision
number instead.

## The three questions a consignor has to answer

Before any software helps, the work divides into three:

1. **Is it classified correctly?** UN number, proper shipping name, class and division,
   subsidiary hazards, packing group. This is where a mistake is most expensive and where
   it is least visible, because everything downstream inherits it.
2. **May it travel like this?** In this packaging, in this quantity, next to these other
   goods, on this vehicle or vessel or aircraft, along this route.
3. **Does the paperwork say what it must say?** In the right order, in a permitted
   language, with the declarations signed by someone entitled to sign them.

CargoPilot is built for the third question, does a great deal of the first, and answers
part of the second. It does not attempt the parts of the second that depend on the
vehicle, the vessel, the aircraft or the route — and those are not marginal.

## What is held, per substance

| Source | Contents | Covers |
|---|---|---|
| `seed/dg/un_numbers.json` | ADR Table A: class, classification code, packing group, labels, special provisions, LQ, EQ, packing instructions, transport category, tunnel code, hazard number, English and German names | 2,928 rows over 2,336 UN numbers |
| `seed/dg/imdg_dgl.json` | IMDG Dangerous Goods List (Amdt. 42-24): class, subsidiary hazards, PG, special provisions, LQ, EQ, packing/IBC/tank instructions, EmS, stowage and handling (16a), segregation (16b), properties | 2,860 rows over 2,347 UN numbers |
| `seed/dg/card_data.json` | Per-substance marine pollutant status and bulk carriage | 2,336 UN numbers |
| `seed/dg/ems.json` | Fire and spillage schedules | 2,338 UN numbers |
| `seed/dg/segregation_groups.json` | SGG1–SGG18 assignments | 629 entries over 539 UN numbers |
| `seed/dg/imdg_codes.json` | SW1–SW31, H1–H5, SG1–SG78 with their wording | 110 codes |

What is **not** held for any substance: IATA quantity limits per packing instruction,
ADN Table C, and any state or operator variation.

**Tank carriage is modelled since v1.66.0.** Every check in this application was
written for packages and said so nowhere, so a tank load got the packages answer with
nothing to mark it as the wrong one. A per-substance **mode of carriage** — packages, ADR
tank, portable tank or bulk — now says how the goods travel, and the first check to use it
answers whether they may travel that way at all (ADR 3.2.1). Absent means packages, which
is what every consignment drawn up before this release was.

**Two more answers branch on it since v1.67.0.** The **tunnel** code of 8.6.4 gives five of
its twelve codes two answers — B/D, B/E, C/D, C/E and D/E bar more categories for tanks and
bulk than for packages — and both lists had been in this repository since v1.50.0 with only
the packages one ever read. And the **orange plates**: 5.3.2.1.6 *permits* the hazard and UN
numbers for packages, while 5.3.2.1.2 *requires* them on both sides of every tank and
compartment. Permitted and required are not the same finding.

**The ADR tank columns are held since v1.65.0** — the portable tank instruction (10) and its
provisions (11), the ADR tank code (12), its provisions (13) and the vehicle the substance
then requires (14). They were read and cross-checked from the first day of the extractor and
kept out of the seed on purpose, because nothing computed with them. That release carried
them as data and deliberately refused to read an empty column (12) as "not accepted in a
tank", however plainly the pattern suggested it — a statement about what the ADR *permits*
is not an observation about a table. v1.66.0 read the text (3.2.1, printed pages 546-547)
and the admission check acts on it now.

## Road — ADR

**Checked:** the 1.1.3.6 points calculation (categories, factors, the 1,000-point
threshold, category 0 as a hard stop); the 7.5.2 mixed-loading prohibitions including
CV28 for foodstuffs and, since v1.38.0, footnotes (b), (c) and (d) of table 7.5.2.1 read
from the official text and applied per pair of packages rather than per consignment; and
the quantity limits of chapters 3.4 and 3.5 — the entered net
per inner packaging against column 7a and the E code of column 7b, the 30 kg gross
limit of 3.4.2 (naming the 20 kg tray limit of 3.4.3), and the 1,000-package cap of
3.5.5. When packages that fall within the LQ limits total more than 8 tonnes gross on the
transport unit, ADR 3.4.13/3.4.14 is raised so the large LQ mark of 3.4.15 is not missed.
For class 1 the 1.1.3.6 points use the entered net explosive mass, not the product mass.
Classification comes from Table A; the row is narrowed by whatever the user has filled in —
the classification code first, then the packing group — and where more than one row is still
in the running, the panel says how many, what they differ in and which field settles it.
Until v1.51.0 only a varying *packing group* was flagged, which left fifteen UN numbers to
be resolved in silence, UN 1950 aerosols and UN 2037 gas cartridges among them. Carriage-prohibited
substances are kept out of the points table. The description line follows 5.4.1.1.1 and
the tunnel code is printed, correctly, only here — and since v1.50.0 the code for the whole
load is derived from it under 8.6.3.

Since v1.33.0 the figures behind those checks have been read out of ADR 2025 Volume I
rather than recalled. Confirmed verbatim: the 30 kg gross mass of **3.4.2**, the 20 kg for
shrink- or stretch-wrapped trays of **3.4.3**, the 1,000-package cap of **3.5.5**, and the
whole of table **3.5.1.2** — E1 30/1000, E2 30/500, E3 30/300, E4 1/500, E5 1/300, in grams
for solids and millilitres for liquids and gases, with E0 not permitted. Every value the
application had was correct. Saying so on the strength of the text is worth more than
saying so on the strength of a recollection that happened to be right.

**One thing was wrong, and it cost users money.** Note (a) to the table in 1.1.3.6.3 reads:
*"For UN Nos. 0081, 0082, 0084, 0241, 0331, 0332, 0482, 1005 and 1017, the total maximum
quantity per transport unit shall be 50 kg"* — and the matching multiplier, spelled out in
RID 1.1.3.6.4, is **× 20** rather than the × 50 of ordinary transport category 1.
CargoPilot applied × 50 to all nine. 50 kg of chlorine (UN 1017) or anhydrous ammonia
(UN 1005) therefore scored 2,500 points and lost the 1.1.3.6 exemption, when 50 × 20 is
exactly the 1,000 the text allows. The application was insisting on orange plates, a driver
certificate, written instructions and an ADR vehicle for consignments entitled to the
exemption. Fixed in v1.33.0.

**Since v1.56.0 the table is ADR 2025 itself.** Until then it was an export of ADR **2023**,
patched: the eleven rows 2025 added were carried in by hand and the two it withdrew were
flagged in place. A patch covers what an edition added and nothing of what it changed, and
2025 changes a field on 316 of the 2,334 UN numbers the two share. All twenty-three columns
are now read out of the official Dutch edition — 3,158 rows, 2,345 UN numbers, no unreadable
page — and checked against the alphabetical index of that edition, which is the same table
set a second time. Eleven of the thirteen compared fields agree on every UN number.

Three of those changes are worth naming, because each was an answer the application was
giving with confidence:

- **UN 3423 tetramethylammonium hydroxide, solid** moved from class 8 to **class 6.1**.
  Different labels, transport category 1 instead of 2, hazard identification number 668
  instead of 80 — the number that goes on the orange plate.
- **The three UN 0015 rows** carry their own subsidiary hazard again: 1, 1 + 8 and
  1 + 6.1. The export gave all three the same labels column, so the corrosive and the toxic
  variant lost their second label on the way to the document.
- **UN 1950 aerosols** are in the ADR's own order, which opens at 5F — the flammable spray
  can. The export was sorted alphabetically, so an unspecified aerosol was filled in as 5A,
  the *non-flammable* row: the exact reading v1.51.0 showed costs a factor of three in
  points.

Two things the Dutch edition cannot supply, and where they come from instead: the **English
and German** proper shipping names, which have no column in it, and **which UN numbers are
not admitted for carriage** — the Dutch table writes a prohibition by leaving the row empty,
and writes "not subject to ADR" the same way, so the fourteen prohibited entries come from
the 2023 export, which names them in words. Both are in the manifest errata.

This is the mode CargoPilot serves best, and the reason is simple: ADR Table A is the
dataset it was built on.

**Not checked, and worth knowing:**

- **The route is still not known, and that is the part that remains.** Since v1.50.0 the
  load's own tunnel restriction code *is* derived, from ADR 8.6.3 read out of the book:
  8.6.3.2 assigns the most restrictive code of the load to the whole load; 8.6.3.3 leaves
  goods carried under 1.1.3 out of that determination entirely, except where the 3.4.13
  marking applies; and the table of 8.6.4 turns the code into the tunnel categories that
  are barred, with B1000C and C5000D splitting on the total net explosive mass per
  transport unit. The result reaches the export as well as the panel. What CargoPilot still
  does not know is which tunnels lie on the route and which category they carry — that is
  the carrier's, under 1.9.5 — and whether the goods travel in tanks or in bulk, which is
  stricter for five of the twelve codes. Both are said next to the answer.
- **LQ and EQ are compared, not granted.** The quantity check of 3.4 and 3.5 says
  whether a line falls within or outside the limits, or that the input is incomplete.
  What it deliberately does not do is treat qualifying as being exempt: the LQ/EQ mark,
  the packaging requirements of 3.4.1/3.5.2 and the tests of 3.5.3 are conditions the
  application cannot see, so a qualifying line is reported next to the points table and
  never removed from it. The limits have since been checked against the published 3.4.2,
  3.4.3, 3.5.1.2 and 3.5.5 and are correct.
- **The compatibility groups of 7.5.2.2 are evaluated since v1.41.0**, against ADR's own
  table read from printed page 593 — twelve groups, A to S, with no group K. An empty cell
  is an error, an X passes silently, and the four footnotes come back as the condition they
  state. Two releases were needed to get here and the order is worth recording: until
  v1.40.1 the check crashed when it fired, and it only ever fired if the group happened to
  sit in the class column, which for explosives it does not. Group S is now included, so
  1.4S beside a group L package is refused — the old code carried the 7.5.2.1 exception for
  1.4S into a table where it does not belong.
- **The two EQ provisions that only show up across lines are applied since v1.50.0.**
  3.5.1.3: where goods with different E codes are packed together, the total per outer
  packaging is capped by the most restrictive of those codes — 400 g of an E1 substance
  beside 200 g of an E3 one is over the 300 g cap while each line on its own is within its
  own code, which is exactly what assessing line by line cannot see. And 3.5.1.4 relieves
  the smallest quantities (E1/E2/E4/E5, ≤ 1 g or 1 ml inner and ≤ 100 g or 100 ml outer) of
  everything but 3.5.2 and 3.5.3 — including the 3.5.5 cap, so those packages no longer
  count towards the 1,000. The two fail in opposite directions: the first let a package
  through that the text caps, the second refused a load the text permits.
- **The vehicle, except its equipment.** Placarding and marking (5.3), driver training
  (8.2), the ADR certificate of approval, tank codes: all outside the application. The
  equipment of **8.1.4 and 8.1.5 is derived** since v1.53.0, because 8.1.5.1 chooses it by
  the hazard label numbers of the goods loaded and points at the transport document to
  identify them — which is what CargoPilot holds. It is a checklist and not a finding; the
  application cannot see what is in the cab.
- **Placarding and marking are derived since v1.57.0, for carriage in packages.** The
  useful half of 5.3 turned out to be the refusals. 5.3.1.5 gives a vehicle carrying
  packages two reasons to placard — class 1 other than division 1.4 compatibility group S,
  and class 7 other than excepted packages — so a load of packaged petrol, nitric acid or
  toxic liquid needs none, and the orange plates of 5.3.2.1.1 are the whole of it. Where the
  consignment is a single substance, 5.3.2.1.6 lets those plates carry the hazard
  identification number over the UN number, and both come out of table A, so they are
  printed. And 5.3.6.1 opens "when a placard is required": the environmentally hazardous
  mark on the *vehicle* therefore hangs on the placard, not on the substance, so packaged
  class 9 marine pollutant marks the package and not the truck. Tanks and bulk have their
  own subsections and are not answered; the elevated temperature mark of 5.3.3 turns on a
  carriage temperature nobody tells the application.
- **High consequence dangerous goods are derived since v1.58.0.** Table 1.10.3.1.2 turns
  out to be easier than it looks once it has been read: for carriage in packages its column
  holds two values and no others — **0**, meaning any quantity at all, and footnote **b)**,
  meaning 1.10.3 does not apply whatever the quantity. There is no threshold to compare
  against. What the table catches is class 1 (divisions 1.1, 1.2, 1.5, 1.6, 1.3 group C and
  fifteen named 1.4 entries), the toxic gases, the desensitised explosives, packing group I
  toxics and category A infectious substances. What it does *not* catch is the half a user
  would guess: flammable liquids, corrosives and packing group I oxidisers are all footnote
  b) in packages. Class 7 is not answered — 1.10.3.1.3 measures it in activity against
  3,000 A2 — and neither are the tank and bulk columns, whose 3,000 litre and 3,000 kg
  thresholds are relevant only where table A permits that form of carriage.

## Rail — RID

**Checked:** the 1.1.3.6 quantity calculation — and since v1.33.0 that is a statement about
RID, not a borrowed ADR figure.

RID 1.1.3.6 has been read. It settles a question this document previously listed as an
assumption:

- **RID 1.1.3.6.3** sets out the same five transport categories with the same maximum
  quantities — 0, 20, 333, 1000 and unlimited — as ADR.
- **RID 1.1.3.6.4** prescribes the same multipliers: category 1 × 50, category 2 × 3,
  category 3 × 1, against the same calculated value of **1000**.
- What differs is the **unit of account**. RID counts per *wagon or large container*; ADR
  per *transport unit*. RID 1.1.3.6.1 and 1.1.3.6.2 are `(Reserved)` where ADR has text.

So the arithmetic was right all along, and the old warning that "RID has its own 1.1.3.6
which CargoPilot does not hold" was true but unhelpfully vague — it invited the user to
distrust a number that is in fact the number RID prescribes. The panel now cites
1.1.3.6.3/1.1.3.6.4 and names the difference in unit instead of hedging.

**And reading it found a bug that affects road as much as rail.** Note (a) to the table in
1.1.3.6.3 reads, in both ADR and RID: *"For UN Nos. 0081, 0082, 0084, 0241, 0331, 0332,
0482, 1005 and 1017, the total maximum quantity per transport unit shall be 50 kg."* RID
1.1.3.6.4 gives the matching multiplier in words — those goods count **× 20**, not × 50.
CargoPilot applied × 50 to all of transport category 1, so 50 kg of chlorine scored 2500
and lost an exemption the text grants at exactly 1000. The application was demanding orange
plates, a driver certificate and an ADR vehicle for loads that do not need them. Fixed in
v1.33.0 for both ADR and RID.

The tunnel code remains correctly absent from the CIM: RID 5.4.1.1.1 has been read and its
list of particulars — (a) UN number, (b) proper shipping name, (c) labels or class,
(d) packing group, (e) number and description of packages, (f) total quantity, (g) consignor,
(h) consignee, (i) any special agreement declaration, (j) the hazard identification number
where 5.3.2.1 marking is prescribed — contains no tunnel restriction code.

**What a rail specialist would additionally expect,** none of which is present:

- **The hazard identification number before the UN number.** RID 5.4.1.1.1 (j) requires it
  on the document when 5.3.2.1 marking is prescribed, in the order (j), (a), (b), (c), (d) —
  e.g. `663, UN 1098 ALLYL ALCOHOL, 6.1(3), I`. CargoPilot holds the Kemler number per
  substance but never places it in the description line for rail.
- **Shunting and marshalling.** Provisions with no road equivalent, including the shunting
  label of model 13 which RID 5.4.1.1.1 (c) explicitly excludes from the description.
- **Shunting and marshalling** beyond 7.5.3, including the shunting label of model 13 which
  RID 5.4.1.1.1 (c) explicitly excludes from the description.
- **7.5.2.4**, read in passing on page 1103 and not implemented: mixed loading of dangerous
  goods packed in limited quantities with any explosive substance or article is prohibited
  for rail, except division 1.4 and UN 0161 and 0499. CargoPilot already knows which lines
  fall within the LQ limits and which packages are class 1, so this is a small rule sitting
  on data the application holds. There is no ADR equivalent.
- **The CIM's own dangerous goods fields.** Box 24 (NHM) is a free-text field with a format
  check; the entries in boxes 21/23 come from the shared DG data without rail-specific
  validation.

**What rail did get, from its own text.** Two provisions moved out of this list in v1.41.0
and both came from OTIF's own pages rather than from ADR on loan:

- **7.5.2.2, the compatibility groups** (page 1102). RID's table is ADR's table *minus
  compatibility group A* — road runs A to S, rail B to S, and neither lists group K. So the
  rail leg is evaluated against the rail table, and a group A package on rail is told that
  the table does not cover it rather than being given ADR's row. The four footnotes are
  word for word the same in both texts.
- **7.5.3, the protective distance** (page 1103). 18 m, or two 2-axle wagons or one wagon
  with four or more axles, between a unit placarded 1, 1.5 or 1.6 and one placarded 2.1, 3,
  4.1, 4.2, 4.3, 5.1 or 5.2. Note what the text does *not* say: model 1.4 is not among the
  triggers, and classes 6.1, 8 and 9 are not among the counterparts. This is the one place
  where the ADR chapter could never have stood in — 7.5.3 is about how a train is made up,
  and a road transport unit travels alone, so borrowing would have produced no answer rather
  than a rough one. Since CargoPilot cannot see the rest of the train, a consignment with a
  class 1 wagon and no counterpart of its own still gets the provision, addressed to the
  carrier.
- **CW 28 instead of CV28.** RID column (18) names the foodstuffs provision CW 28; the
  application cited ADR's CV28 on rail as well. The text of 7.5.4 is identical in both, so
  nothing changes about the requirement — but a CIM that quotes a code the RID does not have
  is the same category of defect as the tunnel code that used to be printed on it.

**Assessment:** rail is no longer the weakest of the five, and since v1.41.0 it is no longer
mostly road on loan either. The quantity calculation, the mixed-loading table, the
compatibility groups and the protective distance are all cited to RID. What is left is
genuinely rail-specific: the hazard identification number on the document, 7.5.2.4, and
shunting.

## Inland waterway — ADN

**Checked:** ADN 1.1.3.6.1 — its own exemption, with its own table. Since v1.33.0 this is
the only mode whose exemption answer is not the ADR points total.

Reading ADN 1.1.3.6 produced the single most consequential finding in this assessment.
**ADN has no points calculation at all.** It does not use transport categories, it has no
multipliers, and there is no threshold of 1000. ADN 1.1.3.6.1 exempts a consignment carried
in packages when

- the **gross mass of all dangerous goods together does not exceed 3,000 kg**, and
- **no class exceeds its own figure** in the table: 0 kg, 300 kg or 3,000 kg depending on
  packing group, class 2 group, or whether a model No. 1 label is required.

Carriage in tanks is never exempt, for any class. Class 1 is 0 kg. Class 2 toxic groups
(T, TF, TC, TO, TFC, TOC) are 0 kg; group F is 300 kg; anything else in class 2 is 3,000 kg.
Class 7 is 0 kg except UN 2908–2911, which are 3,000 kg.

Until v1.33.0 an ADN shipment was shown the ADR points table. That is not an approximation
of the ADN answer — it answers a different question, and the two can point in opposite
directions. The concrete case, now pinned by a test:

> 1,200 litres of a packing group III liquid scores 1,200 ADR points and **loses** the
> exemption above the 1,000 threshold. Under ADN the class 3 "any other substances" figure
> is 3,000 kg and the total is under 3,000 kg, so the same consignment **is** exempt.

A user preparing an inland waterway shipment was being told to comply with requirements
that ADN does not impose on them — or, in the mirror case, reassured by a road threshold
that ADN does not use. The panel now shows an ADN card with its own status, the per-class
figures, and the conditions of 1.1.3.6.2 that survive the exemption (the 1.8.5 reporting
obligation, packagings to Parts 4 and 6, the 5.2 marking and labelling, the transport
document and stowage plan on board, stowage in the holds, and 3 m horizontal separation
between classes).

**Also checked, since v1.59.0:** ADN **7.1.4.3**, separation of packages in the holds. This
is not the road rule renamed. ADR 7.5.2 asks whether two packages may share a vehicle and
answers yes or no; 7.1.4.3 asks how many metres must lie between them, which is an answer
the application could not previously express at all. Different classes go 3.00 m apart and
are never stacked; class 1 goes 12 m from everything else.

**And since v1.61.0:** the ADN's **own table A**, read out of the Dutch edition by
`scripts/extract_adn_table_a.py`. Its first columns identify the goods as the ADR's do —
checked substance by substance against the ADR table already in the repository, and the
class and the name agree on all 2,343 they share — and then it answers a vessel's
questions. **Column (12), the number of blue cones or blue lights**, closes two things:

- the cone half of 7.1.4.3 — 7.1.4.3.2, which forbids two-cone goods a hold with one-cone
  flammable goods, and the three-cone extension of 7.1.4.3.3 to classes 4.1 and 5.2;
- **ADN 7.1.5.0.1**, the signals the vessel must show, which had no answer at all. With
  7.1.5.0.4: where the load disagrees with itself, the heaviest signal wins, so one package
  can set the signals for the whole vessel.

**What is missing beyond that:**

- **The tank vessel regime entirely.** ADN splits into dry cargo and tank vessels, and the
  tank vessel side with its own substance table (Table C) is a different discipline.
  CargoPilot has nothing to say about it and should not be read as though it has.
- **The rows the ADN table A holds only once.** The table is available one row per UN
  number and the book prints several for 452 of the 2,352 substances. Where those rows
  differ in the vessel's columns — UN 1203 petrol is the clear case — no cone count is
  offered and the substance is named. 1,913 substances are settled; 439 are not.
- **ADN 7.1.5.0.2**, the reduction for goods carried exclusively in containers. Its
  thresholds are **read** since v1.64.0 — above 130,000 kg keeps one cone, at or below shows
  none; above 30,000 kg keeps two, at or below none; three cones stay three — but the
  reduction is not applied. Doing so needs the consignor to state that the load travels only
  in containers, and there is nowhere to say that yet; inferring it from a packaging type
  would be guessing at the fact the provision turns on. Its absence can only overstate the
  signals, and the panel says so.
- ~~**7.1.4.3.4**, the class 1 compatibility table~~ — applied since v1.64.0. Twelve groups,
  four numbered conditions, and the two readings the rule demands were not a formality: the
  Dutch HTML edition is damaged there (row N has thirteen cells where twelve belong, and the
  D/B cell lost its footnote marker). The English edition mirrors across its diagonal in all
  144 cells, which is a property of a compatibility table and not of a typesetting, and that
  check is kept as a test.
- **Anything else vessel-specific** for dry cargo: requirements following from the vessel
  type, degassing and venting.
- **ADN 5.4.1.1.1 (j)**: where column (11) of Table A carries `ST01`, the document needs a
  confirmation of stabilisation. Read from the text; not implemented.
- **No ADN certificate and no expert on board.**

**Assessment:** for packaged goods on a dry cargo vessel the exemption, the separation and
the signals are all answered from the ADN's own text, and since v1.63.0 all three are
visible — in the compliance panel and on the document, where until then they were computed
for every consignment and shown to nobody.

**The mode came off the lock in v1.63.0.** It went on in v1.60.0 because inland waterway
answered its separation question with the *road* table and held no cone data at all. What
still does not exist is the tank vessel regime — and a tank vessel consignment cannot be
entered here in the first place, because this wizard models packages. So what a user can
draw up is exactly the part that is covered, which is the condition the lock existed to
enforce.

## Sea — IMDG

This is the most thoroughly developed part of the application, and the only mode where the
segregation question is genuinely answered.

**Checked:** the 7.2.4 class table; the 7.2.5 segregation groups; the per-substance
segregation provisions of column 16b with the 7.2.3.1 precedence rule applied and both
findings kept visible; the 7.2.6.3 exemption tables, reported but never used to remove a
warning; the 7.2.6.5 class 8 exception; the 7.2.7.1.4 class 1 compatibility matrix with
the ammonium nitrate exception; the LQ and EQ quantity limits of chapters 3.4 and 3.5,
read from the 42-24 Dangerous Goods List and flagged where the ADR value on the line
differs; and the Amendment 42-24 difference layer with its reclassifications flagged
rather than silently applied.

Subsidiary risks count throughout, and a subsidiary class 1 risk is treated as division
1.3, which is stricter than the primary hazard alone.

**Not checked:**

- **Stowage category is shown, not enforced.** Whether a substance may go on deck or under
  deck, and what that means for the rest of the load, is displayed as a category letter and
  left there. **[verify: IMDG 7.1]**
- **CTU packing.** The container/vehicle packing certificate is a set of declarations the
  user ticks. Nothing checks the load against them. The VGM has a real arithmetic
  cross-check, which is more than the certificate gets.
- **Segregation from foodstuffs** is raised as a requirement to verify for the seven codes
  whose target is ordinary cargo, because the application does not know what else is in the
  container. That is the right call and it is worth stating: it is a deliberate
  non-answer, not an oversight.
- **Nothing about the ship.** Stowage plans, the special list or manifest, and every
  provision that depends on the vessel.

**Assessment:** for the segregation of packaged dangerous goods this is solid, tested and
pinned against edits. Everything downstream of "may these two travel together" is out of
scope.

## Air — IATA DGR

**Checked:** Table 9.3.A segregation including the lithium battery rule, the Q value of
5.0.2.11 (only when M is entered — auto-filled n alone does not start the check), the
Cargo Aircraft Only flag, division 2.3 as forbidden for air carriage, and the requirement
that the IATA packing instruction rather than the ADR one reaches the declaration. The
required-field set for the Shipper's Declaration is the strictest of the five.

**The significant limitation:**

- **The Q value still depends on user-supplied n and M.** CargoPilot does not hold IATA's
  quantity tables, so the net quantity and maximum permitted net quantity for the
  applicable packing instruction must be entered manually. Since v1.30.0 the result makes
  this explicit: the API and compliance panel report `checked`, `incomplete`, `exceeded`
  or `not_checked`, and warn when an all-packed-in-one check may apply but the required
  values are absent. This prevents a skipped calculation from looking like approval, but
  it does not replace the missing IATA quantity tables. **[verify: IATA DGR 5.0.2.11 and
  table 4.2]**

**Also absent:**

- **Every automatic quantity limit.** Net per package, per aircraft type, passenger versus
  cargo aircraft. Without the tables CargoPilot cannot derive M or compare the shipment
  automatically.
- **State and operator variations.** Not held at all. In practice these decide a great deal
  of what actually flies, and an airline's variation can be stricter than the DGR.
- **Section I versus Section II** for lithium batteries, and the whole of the excepted
  quantity and limited quantity apparatus for air.
- **Overpack declarations, dry ice, radioactive material** beyond what the classification
  supplies.

**Assessment:** the segregation and the declaration are sound. Missing Q input is now
visible, but the quantity side remains incomplete because CargoPilot cannot derive the
per-package limits from IATA Table 4.2.

## Gaps ranked by what they cost

Ordered by how much harm someone could take before noticing, not by effort.

| # | Gap | Why it ranks here |
|---|---|---|
| 1 | **IATA quantity limits absent; Q depends on user-entered M** | CargoPilot warns when the Q check did not run — since v1.33.0 on the document as well as the screen — but it cannot derive the applicable passenger/cargo-aircraft limit or verify the entered M against Table 4.2. **[verify]** |
| 2 | **The ADN tank vessel regime is entirely absent** | Table C, vessel types, degassing. A tank vessel shipment gets nothing, and nothing says the mode is only half covered. |
| 3 | **Route data absent: which tunnels, and in which category** | Closed for the part that is CargoPilot's since v1.50.0 — 8.6.3.2, 8.6.3.3 and the table of 8.6.4 are applied and the load's code reaches the export. What is left is the route itself, which 1.9.5 puts with the carrier, and the tanks/bulk branch of five codes. |
| 4 | **Mixed loading for ADN answered with ADR's 7.5.2** | Closed. v1.38.0 read RID's 7.5.2.1 and found it identical to ADR's, footnotes included; v1.41.0 gave rail its own table and its own protective distance. v1.59.0 gave inland waterway ADN 7.1.4.3, which asks a different question again — how many metres, not whether — and v1.61.0 read column (12) of the ADN's own table A so the two cone provisions are answered as well. v1.64.0 closed the last of it: 7.1.4.3.4, the class 1 compatibility table, is applied — and getting it exposed that the Dutch HTML edition of that table is damaged, which the two-reading rule caught. |
| 5 | **LQ/EQ conditions not checked** | The arithmetic of 3.4/3.5 is verified correct and 3.5.1.3/3.5.1.4 are applied since v1.50.0, but the mark, the packagings and the 3.5.3 tests are declarations the application cannot see. A line "within the limits" is a candidate, not an exemption — and the panel says so. |
| 6 | **IMDG stowage category shown, not enforced** | Lower because on-deck/under-deck is usually the carrier's call, not the consignor's. **[verify]** |
| 7 | **No marking or placarding checks outside the road mode** | Closed for ADR in v1.57.0: 5.3.1.5, 5.3.2.1 and 5.3.6.1 are derived for carriage in packages, and the answer is mostly that no placard is required — the provision names only class 1 and class 7. The equipment half closed in v1.53.0. Rail, inland waterway, sea and air still have nothing. |

Two of the top gaps from earlier versions of this table are gone, and it is worth being
precise about why. "RID and ADN answered with ADR tables" ranked second for three releases;
it is closed for the exemption calculation, because the texts turned out to be free and
reading them showed that RID prescribes the same arithmetic while ADN prescribes something
else entirely. "The Q check silently not running" ranked first; it now reaches the export.

The pattern that remains is the original one: **the application knows or shows a value but
cannot always act on it.** A displayed value must never be mistaken for a completed
verification.

## What should and should not be built

**Shipped in v1.30.0:**

- **Say when the IATA Q check did not run.** The compliance response and panel expose
  `not_checked` and `incomplete` instead of silently omitting the result.

**Shipped in v1.31.0:**

- **Apply LQ and EQ.** The entered net per inner packaging against column 7a and the E code
  of column 7b, with the 30 kg gross limit of 3.4.2, the 20 kg tray note of 3.4.3, the inner
  and outer limits of table 3.5.1.2 and the 1,000-package cap of 3.5.5. Qualifying is
  reported, never granted.

**Shipped in v1.32.0:**

- **Close the specialist findings from the v1.31.0 review.** Division 2.3 air prohibition;
  Q participation only when M is entered; packing-group row selection with a multi-PG note;
  class 1 net explosive mass; the 8-tonne LQ mark of 3.4.13/14; IMDG 7.2.6.5 beside the
  acid × alkali pair; forbidden substances out of points and document lines; hints filtered
  to active modalities; the inner-packaging field hidden when LQ is 0 and EQ is E0.

**Shipped in v1.49.0 and v1.50.0 — the Dutch ADR read out:**

- **The Dutch proper shipping names.** Column (2) of Table A in the official Dutch edition,
  2,345 UN numbers, read twice from two independently typeset documents and cross-checked
  against each other. There is no open source for that column.
- **ADR 8.6.3, the tunnel restriction code for the whole load**, with 8.6.3.3 leaving
  goods carried under 1.1.3 out of the determination and the table of 8.6.4 turning the
  code into the categories that are barred.
- **ADR 3.5.1.3 and 3.5.1.4**, the two excepted-quantity provisions that can only be seen
  across lines.
- **The eleven rows ADR 2025 added.** UN 0514 and UN 3551–3560 reached the app through the
  IMDG 42-24 layer, and therefore with sea data only — no transport category, no tunnel
  code, no hazard identification number. Copied by hand from the Dutch edition, each row
  read twice.
- **The silent Table A row choice.** Fifteen UN numbers had several rows that the old
  packing-group check could not see, because their rows share one packing group or have
  none. UN 1950 aerosols is twelve rows apart on transport category, tunnel code and
  labels; UN 2037 gas cartridges is nine.
- **Entries with no usable English proper shipping name.** Fourteen empty and one
  truncated in the export; the German name was substituted without a word.
- **The edition the classification table actually is.** Reading the book showed it to be an
  ADR 2023 export while the manifest reported 2025; UN 0514 and UN 3551–3560 are missing
  from it and UN 1499 and 1999 are still in it. The manifest said so from v1.49.0, and
  v1.56.0 closed it: the table is now ADR 2025, read out of the book itself.

**Shipped in v1.33.0 — the land regulations read rather than recalled:**

- **`scripts/read_land_regulations.py`** fetches ADR, RID and ADN from UNECE and OTIF on a
  runner and quotes the provisions the application implements. The premise that these texts
  were unreachable was simply false.
- **Note (a) to 1.1.3.6.3**: the nine UN numbers that count × 20, not × 50.
- **ADN 1.1.3.6.1**: its own exemption, on gross mass with a per-class figure, reported
  separately from the ADR points.
- **RID 1.1.3.6.3/1.1.3.6.4 cited** instead of hedged.
- **The Q status moved into `check_compliance`**, so the export sees it; and a position
  holding two or more substances with no Q input is reported as not checked instead of
  being skipped.

**Worth building next, in this order:**

1. **The hazard identification number in the rail description line**, per RID 5.4.1.1.1 (j),
   and the `ST01` stabilisation confirmation for ADN per its 5.4.1.1.1 (j). Both read from
   the text; both small.
2. **RID 7.5.2.4** — limited quantities may not be loaded with explosives, except division
   1.4 and UN 0161/0499. Read from page 1103 in v1.41.0 but not implemented. It needs
   nothing the application does not already compute: the LQ assessment of 3.4 and the class
   of each package.
3. **ADN's own stowage regime**, the part of 7.5.2 still borrowed. Rail is done: 7.5.2.1,
   7.5.2.2 and 7.5.3 are now cited to RID.
4. **ADR 5.4.1.1.1 (c) for batteries.** ADR 2025 names UN 3551 and 3552 alongside 3090,
   3091, 3480 and 3481 as entries whose description carries class "9". The application does
   not hold those two as ADR entries at all yet — see the note on the edition below.

**Not worth building, or not buildable here:**

- **IATA quantity tables.** Table 4.2 is copyrighted and is not available as open data.
  CargoPilot can accept n and M, do the arithmetic and state clearly when input is missing;
  it cannot safely manufacture the source limits.
- **The IMDG Code's own text.** Sold by the IMO. The segregation data already in the
  repository came from IMO circulars and resolutions that are freely distributable; the
  Code itself is not.
- **State and operator variations.** These change per airline and per country and would be
  stale within months of shipping.
- **Anything about the vehicle, vessel or aircraft.** Outside what a document preparation
  tool can responsibly claim.

---

*This assessment covers CargoPilot v1.53.0. v1.42.0 to v1.48.0 touched the goods
catalogue, the interface language, the settings, the documentation and the error messages,
not a single regulatory check; v1.49.0 and v1.50.0 changed the ADR side, from the Dutch
edition of the book. It is guidance for development, not a compliance statement. Every document the application produces is a draft; see
[DISCLAIMER.md](../DISCLAIMER.md).*
