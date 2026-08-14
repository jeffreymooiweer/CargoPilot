# Changelog

All notable changes are documented here, following [Semantic Versioning](https://semver.org/).

## [1.70.0] — 2026-08-13

### Fixed

- **A tank needs placards, and this check used to say it needed none.** For
  carriage in packages 5.3.1.5 puts a placard on the vehicle only for class 1 and
  class 7. That reading is right, and it is the finding v1.57.0 was built around:
  a full load of packaged petrol needs no placard at all, and telling a driver to
  placard anyway teaches that the placard is decoration.

  A tank does not work that way. **5.3.1.4.1** requires a placard of *every label
  model of the load* on both long sides and on the rear of the vehicle;
  **5.3.1.2** requires the same on both long sides and at each end of a tank
  container or portable tank. Where a tank has several compartments carrying
  different goods, the placards go on the relevant compartments plus one of each
  model on each side at the rear.

  So the answer inverts with the mode: the same petrol that needs no placard in
  packages needs a class 3 placard on three faces in a tank. Answering the second
  with the first turns a requirement into an absence, which is the worst
  direction for a placard to be wrong in.

  Bulk is placarded like a tank here — 5.3.1.4 is headed carriage in bulk and in
  tanks alike, and this is the one rule in the tank work where the two share an
  answer. Where table A gives no label in column (5) the check says the provision
  turns on one, rather than reporting placards it cannot name.

  Read from ADR 2025, Dutch edition, 5.3.1.2 and 5.3.1.4.1, printed pages
  975-976.

## [1.69.0] — 2026-08-13

### Fixed

- **The 1.1.3.6 exemption is for carriage in packages, and a tank load can no
  longer claim it.** The operative sentence of 1.1.3.6.2 grants the exemption
  for goods carried *in packages* in one transport unit. A tank or a bulk load is
  not carriage in packages, so the exemption is not available to it however small
  the quantity — and the points arithmetic, which exists only to test that
  exemption, is answering a question that does not arise.

  The panel now says so in place of a total: neither green nor red, because the
  exemption is not failed, it is not on offer. One litre in a tank does not buy
  it back; the provision turns on the form of carriage and not on the amount.

  **This reaches the tunnel too.** 8.6.3.3 takes goods carried under 1.1.3 out of
  the tunnel determination altogether, and until now a tank load could be dropped
  out of it on the strength of a points total it was never entitled to. Its code
  now stands — and with v1.67.0 that code is read from the stricter column.

  Withholding an exemption is the safe direction to be wrong in; granting one is
  not. Read from ADR 2025, Dutch edition, 1.1.3.6.2, printed page 77.

## [1.68.0] — 2026-08-13

### Fixed

- **A road tanker of petrol is high consequence dangerous goods, and this check
  used to say it was not.** Table 1.10.3.1.2 has three quantity columns — tank,
  bulk and packages — and only the packages one was ever answered.

  For packages the answer is mostly footnote b): whatever the quantity, 1.10.3
  does not apply. That reading is right and it is why v1.58.0 could answer
  packages with a membership test and no arithmetic at all. **Seven rows are
  footnote b) in packages and 3,000 litres in a tank**, so they had no reason to
  exist in this configuration until the application knew about tanks: flammable
  non-toxic gases, flammable liquids of packing groups I and II, packing group I
  substances of classes 4.2, 4.3, 5.1 and 8, and the perchlorate and ammonium
  nitrate entries.

  Above 3,000 litres in a tank, those now qualify — and with them comes the
  security plan of 1.10.3.2 and the identity documents of 1.10.1. Not every tank
  row is a threshold: a toxic gas carries 0, meaning any quantity at all.

  **Footnotes c) and d) are applied with the figures.** A tank or bulk value
  counts only where table A admits that form of carriage, which the columns
  carried since v1.65.0 settle — so an explosive, which has no tank code, is not
  dragged into the tank column by a mode somebody set in error.

  A threshold needs a quantity. Where none is entered the row is reported as
  **unanswered** rather than read as under the figure: the difference between not
  knowing and knowing it is safe.

  Read from ADR 2025, Dutch edition, table 1.10.3.1.2 and its four footnotes,
  printed pages 184-185.

## [1.67.0] — 2026-08-13

### Fixed

- **The tunnel code applies the stricter side for tanks and bulk.** Five of the
  twelve codes of 8.6.4 carry two answers: B/D, B/E, C/D, C/E and D/E bar more
  tunnel categories for carriage in tanks and in bulk than for packages. **Both
  lists have been in this repository's configuration since v1.50.0** and only the
  packages one was ever read, because nothing knew how the goods travelled. The
  note under the tunnel card said as much — and a note is not a check.

  A tank of petrol under code D/E is now barred from categories D **and** E,
  where the same petrol in packages is barred from E alone. One tank position
  decides for the whole load, because 8.6.3.2 assigns one code to the load and
  not one per substance.

- **The orange plates tell a tank load what it must do, not what it may.** For
  packages 5.3.2.1.6 *permits* the hazard identification number above the UN
  number on the front and rear plates, and only where a single substance is on
  board. For a tank vehicle 5.3.2.1.2 *requires* an orange plate on both sides of
  every tank and every compartment, bearing the numbers of the substance that
  compartment holds. Permitted and required are not the same finding, and a tank
  load was being shown the permitted one.

  Where column (20) gives no hazard identification number the check says that
  5.3.2.1.2 turns on one, rather than printing a plate with a gap in it.

  Read from ADR 2025, Dutch edition, 5.3.2.1.2 and 5.3.2.1.6.

## [1.66.0] — 2026-08-13

### Added

- **The application knows how the goods travel.** Every check in the compliance
  layer was written for **packages**, and said so nowhere. A consignor filling in
  a tank load got the packages answer with nothing to mark it as the wrong one —
  the most expensive shape of wrong this application can produce, because it does
  not look like a gap, it looks like an answer.

  A per-substance **mode of carriage** now says which it is: in packages, in an
  ADR tank, in a portable tank, or in bulk. It is a list and not a text box —
  free text there would fall through every check that branches on it and the
  consignment would quietly be judged as packages again. An unknown value is
  refused at the API edge for the same reason. Absent means packages, which is
  what every consignment drawn up before this release was.

- **ADR 3.2.1: may these goods travel in a tank at all?** The first check to use
  the mode, and it only speaks once somebody has said the goods travel in one.
  UN 1203 petrol is admitted with tank code LGBF on an FL vehicle; UN 0004
  ammonium picrate is refused, because it has no tank code.

  **The two tank columns do not say the same thing, and the check keeps them
  apart.** Column (12) is absolute: where no code is given, carriage in ADR tanks
  is not permitted, and the provision carries no exception. Column (10) is not:
  where no portable tank instruction is given, carriage is not permitted *unless
  the competent authority allows it* under 6.7.1.3. Rounding those two to one
  answer would either invent a prohibition or hide one, so an item can be "not
  permitted" and still say that approval is open — and only column (12) blocks.

  v1.65.0 carried the tank columns and refused to read an empty column (12) as a
  prohibition until the text had been read. It has now been read: ADR 2025, Dutch
  edition, 3.2.1, printed pages 546-547.

## [1.65.0] — 2026-08-13

### Added

- **The ADR tank columns are in the substance database.** Columns (10) to (14) of
  table A — the portable tank instruction and its provisions, the ADR tank code,
  its provisions, and the vehicle the substance then requires (FL, AT, EX/III) —
  now reach the seed and the substance lookup. UN 1203 petrol reads LGBF and FL;
  UN 1017 chlorine reads P22DH(M) and AT; UN 0004 ammonium picrate leaves every
  tank column empty.

  Nothing new had to be read to get them. The extractor has read and
  cross-checked these five columns since v1.56.0 and dropped them on the way to
  the seed, with the reason written down: nothing in the application computed
  with them, and a field nobody reads is a field nobody notices going stale.
  Tank carriage changes that, so the reason expired.

  Both readings agree: the portable tank instruction, its provisions, the tank
  code and the tank provisions match on all 2,345 shared UN numbers between
  table A and the alphabetical index. Column (14) reaches 0.9966 — the eight
  disagreements are the same eight rows where the *index* also loses the
  transport category, because the digit lands one column over in that reading.
  Table A is the reading the application computes with, and a test pins the
  column to the three vehicle types so a boundary that moves is caught.

### Not yet

- **No check acts on the tank columns.** In particular nothing reads an empty
  column (12) as "not accepted in an ADR tank", however plainly the pattern
  suggests it — UN 0004 and every other class 1 entry leaves it blank. That is a
  statement about what the regulation permits, not an observation about a table,
  and it gets read out of the text before anything acts on it. This release
  carries the data; the checks come with the carriage mode.

## [1.64.0] — 2026-08-13

### Added

- **ADN 7.1.4.3.4, the class 1 compatibility table, is applied.** Twelve
  compatibility groups, four numbered conditions, and until now the one part of
  7.1.4.3 that was named as untranscribed. Two explosives may share a hold only
  where the table says so; where it says so *on a condition* the condition is
  named, because neither "permitted" nor "forbidden" would be the truth. The
  answer does not depend on the order the two were entered — the table mirrors,
  and a test holds it to that.

  **Getting it is why this repository insists on two readings.** The Dutch HTML
  edition is *damaged* at this table: row N carries thirteen cells where twelve
  belong, and the D/B cell lost its footnote marker so the table read "1)" one
  way and "(*)" the other. A compatibility table must mirror across its
  diagonal — that is a property of the thing itself, not of a typesetting — and
  checking it caught both defects. The English UNECE edition mirrors in all 144
  cells and is what the application computes with; the Dutch confirms ten of the
  twelve rows cell for cell. The symmetry check is kept as a test.

### Fixed

- **ADN 7.1.5.0.2: the thresholds are read rather than guessed.** The Dutch
  edition lost the comparison sign, so both rows of each pair read "> 130,000 kg"
  and "> 30,000 kg" — the same rule twice, which decides nothing. v1.61.0
  therefore left the reduction out and said so. The English edition has the
  signs: above 130,000 kg keeps one cone and at or below shows none; above
  30,000 kg keeps two and at or below none; other classes and packing groups II
  and III show none at any mass; three cones stay three.

  The figures were what one would have guessed, and that is exactly why guessing
  would not have done. They are recorded with their provision so nobody reads
  them a second time.

  The reduction is still **not applied**: doing so needs the consignor to state
  that the load travels exclusively in containers, and there is nowhere to say
  that yet. Inferring it from a packaging type would be guessing at the very
  fact the provision turns on. Its absence can only overstate the signals, and
  the panel now names both thresholds instead of gesturing at them.

- **The reading workflow uses the volumes that are already fetched.** The
  extraction workflow has kept them between runs since v1.61.0; this one did
  not, so quoting three lines of the ADN re-fetched 19 MB from the Internet
  Archive — which had already cost three runs to 503 and 498 answers. It now
  restores the same cache.

## [1.63.0] — 2026-08-13

### Added

- **The inland waterway outcomes reach the screen and the document.** v1.59.0 gave
  the ADN its own separation rule and v1.61.0 the blue cones out of its own table
  A. Both computed correctly for every consignment and appeared **nowhere**: the
  compliance panel showed only the 1.1.3.6.1 exemption, and no ADN warning had
  ever been written to a document. Two provisions were answered into the void.

  The panel now carries two more cards. **Separation in the holds (7.1.4.3)**
  lists each finding with the distance it prescribes — 3.00 m between classes,
  12 m around class 1 and the three-cone goods of 4.1 and 5.2 — and the
  shared-hold prohibition of 7.1.4.3.2 with the two substances it stands
  between. **Signals (7.1.5.0)** shows the number of blue cones or blue lights,
  which substance sets it under 7.1.5.0.4, and the container reduction of
  7.1.5.0.2 that CargoPilot deliberately does not apply.

  A cone count of **nought is displayed as prominently as two**. It is the
  commonest answer and means the vessel shows no signal; a card that appeared
  only when cones were needed would teach a consignor that an absent card means
  safe.

  The same outcomes now travel with the papers: the signals, the tie-break and
  every separation finding are warnings on the ADN transport document, through
  the channel opened in v1.62.0.

### Changed

- **Inland waterway is off the lock.** It went on in v1.60.0 because it answered
  its separation question with the *road* table and held no cone data at all.
  The exemption of 1.1.3.6.1, the separation of 7.1.4.3 and the signals of
  7.1.5.0 now all come out of the ADN itself, and all three are visible.

  What is still missing is the tank vessel regime — and a tank vessel
  consignment cannot be entered here in the first place, because this wizard
  models packages. So what a user can draw up is exactly the part that is
  covered, which is the condition the lock existed to enforce. Rail, sea, air
  and multimodal stay locked, with their gaps listed in `docs/dg-coverage.md`.

## [1.62.0] — 2026-08-13

### Fixed

- **The document warnings reach the person about to download.** `validate_document`
  has always returned two lists: blocking errors and warnings. The errors worked.
  The warnings were computed and went nowhere, along two routes at once — the
  export route discarded them (`errors, _warnings = ...`; a file response has no
  body to carry them), and the endpoint that does return them,
  `POST /documents/validate`, had **no caller anywhere in the frontend**.
  `api.validateDocument` sat in `client.ts` unused.

  Fourteen warning sites fed that dead channel: the missing-unit notice of
  v1.61.1 (ADR 5.4.1.1.1 (f)), the missing English proper shipping name, the
  name-language substitution, the lost 1.1.3.6 exemption and its "incomplete"
  counterpart, the mixed-loading findings, the LQ/EQ notes, the IATA Q-check
  notes, the 8.6.3 tunnel message for the whole load, and the VGM mass check —
  that last one has nothing to do with dangerous goods, which is why the fix is
  not gated on a consignment carrying any.

  The warnings now stand on each document's card on the export step, **before**
  the download button — a warning shown after the file is on disk is a warning
  shown too late. They never disable the button: that distinction from errors is
  the point of having two lists. One payload builder now serves validation and
  export both, so what is validated is what is exported by construction. The
  texts arrive from the backend already in the document's language; the frontend
  translates nothing.

### Known limitation, found while proving the fix in the browser

- **A total quantity typed at the wrong moment is silently reverted.** The
  dangerous-goods step re-derives its data 250 ms after every change to the
  fields its signature watches — and `adr_total_quantity` is not one of them, by
  design, because it is a computed value. A user who types a total while such a
  derivation round-trip is in flight gets it overwritten by the response's
  snapshot, which was taken before they typed. Reproduced live: the first "100"
  vanished, the retry stuck. This predates this release and sits in a delicate
  two-way sync; it is reported here rather than patched in passing, and wants a
  change of its own.

## [1.61.1] — 2026-08-13

### Fixed

- **The unit on the transport document followed an empty field.** A consignor who
  entered a total quantity of "100 L" got **"100 kg"** — on the signed consignment
  note, in the total per transport category of 5.4.1.1.1.1, and written back over
  what they had typed. 100 litres of acetone is about 79 kg, and 1.1.3.6.3 counts
  litres and kilograms differently, so this was a wrong quantity on a document
  somebody signs.

  `total_quantity` sniffed the unit out of the *per package* field only. While
  that field is filled the reading is right; the moment it is empty the number
  falls back to the total-quantity field and the unit stayed on its "kg" default.
  That is not a corner of the application: the wizard requires only UN number,
  proper shipping name and class for ADR, RID and ADN, so anyone who fills in
  nothing but the total the 1.1.3.6 points count needs took this path every time.

  The unit is now read from **the same field the number came from**, and a unit
  glued to its number ("100L") counts — a word boundary does not fire between a
  digit and a letter, which is exactly how the old rule would have missed it.

- **A missing unit is now named rather than invented.** Where the input carries no
  unit at all the document shows the bare number, and the export reports it
  against ADR 5.4.1.1.1 (f) in all four languages. Defaulting to kilograms was the
  original mistake in miniature: whether a substance travels by mass or by volume
  is not reliably derivable from table A, and this application does not guess at a
  regulatory fact. Class 1 is unaffected — its quantity is the net explosive mass,
  which 5.4.1.2.1 (a) states in kilograms by definition.

- **The ADR provenance label credited the wrong source.** The rule set was
  reported as "Table A via rkstgr/adr-substances". Table A has been read out of
  the official Dutch ADR 2025 edition since v1.56.0, with the 2023 export reduced
  to the one thing that edition cannot supply — the English and German proper
  shipping names. The regulatory manifest already said so; this label had lagged
  it for five releases. A claim about where a regulatory fact came from is exactly
  the claim that must not go stale.

## [1.61.0] — 2026-08-13

### Added

- **The ADN's own table A, and with it the blue cones.** The inland waterway regime has a
  substance table of its own and CargoPilot has never held it. Its first columns identify
  the goods exactly as the ADR's do, and then it asks a vessel's questions instead of a
  vehicle's: whether the goods may go in packages, in bulk or in a tank vessel, what
  equipment must be aboard, how the holds are ventilated — and **column (12), the number of
  blue cones by day or blue lights by night**.

  That column decides two things the application could not answer.

  **ADN 7.1.4.3 was half a check.** Since v1.59.0 it has applied its class rules and named
  its two cone rules as unassessed, which is honest and not much use. Both are answered now:
  7.1.4.3.2, which forbids two-cone goods a hold with one-cone flammable goods whatever the
  quantity; and the three-cone extension of 7.1.4.3.3, which sends organic peroxides and
  self-reactive substances 12 m from everything else — a provision that previously reached
  class 1 and nothing more.

  **ADN 7.1.5.0.1 had no answer at all.** Which signals a vessel must show is not a nuance
  or a warning; it is a plain fact about the voyage, and the question had nowhere to be
  asked. It is answered now, together with 7.1.5.0.4: where the load disagrees with itself
  the heaviest signal wins, so a single package of a two-cone substance sets the signals for
  everything else on board.

### Verified

- **The table was read twice and checked against a third.** The Dutch edition publishes it
  in two renderings and they do not agree in usefulness: the list pages print every row, the
  per-substance pages print one row per UN number. Where both exist, all 378 rows assembled
  from the per-substance pages appear verbatim in the list pages, all fourteen fields, with
  nothing contradicted. Then the identifying columns were checked against the **ADR** table
  A already in the repository — a different book, read from a PDF by different code in
  v1.56.0 — and the class and the name agree on every one of the 2,343 substances the two
  regimes share.

  Nine substances are in the ADN table and not the ADR's, and all nine are explained: 1499
  and 1999 are the two the 2025 edition withdrew, and 9000 to 9006 are ADN substance numbers
  that exist only for tank vessels.

  One cell disagrees. UN 2071 ammonium nitrate based fertiliser carries classification code
  M11 in the ADN and a dash in the Dutch ADR 2025, whose row for it is blank throughout. Both
  readings match their own book — checked character by character against the page — so the
  disagreement is recorded rather than resolved.

### Known limitation

- **439 of 2,352 substances get no cone count.** The table is available one row per UN
  number and the book prints several for 452 of them. Several rows is not by itself a reason
  to withhold an answer — UN 0015 smoke ammunition has three and all three carry three cones,
  because they differ only in the labels. UN 1203 petrol has three and they do not agree.
  Which kind a substance is was measured from the printed rows rather than assumed, and where
  it could not be settled the substance is **named** rather than silently guessed at. A
  consignor can act on "not settled for UN 1203"; nobody can act on "the cone rules were not
  assessed".

- **ADN 7.1.5.0.2 is not applied.** It lowers the signal count for goods carried exclusively
  in containers against a gross mass threshold, and the comparison operator on one row of
  that table is not legible in the text available here. A threshold read wrong is worse than
  one not read. Leaving it out can only overstate the signals, which is the safe direction,
  and the panel says so instead of leaving it to be discovered.

### Fixed

- **A download is asked for once, not once per run.** UNECE refuses a CI runner outright and
  the Internet Archive, which is the way round, rate-limits: the same ADN address served
  19 MB in the morning, 503 twice in the afternoon and then 498. Three runs were spent
  discovering that the internet was briefly crowded. A temporary status is now retried with
  a widening wait, and the volumes are kept between runs — including when the run fails,
  because the run that fetched one book and then tripped over the next is precisely the one
  whose first download must survive.

## [1.60.0] — 2026-08-13

### Changed

- **Only carriage by road may be used to draw up documents.** Rail, sea, inland waterway
  and air are locked: the tiles are greyed out and say why, and the wizard refuses the
  route.

  They were built, reachable, and **wrong in ways that do not announce themselves.** Inland
  waterway answered its separation question with the *road* table until v1.59.0, and it
  still has no table C — so a tank vessel consignment gets nothing at all, silently. Rail
  and sea carry known gaps of their own, listed in `docs/dg-coverage.md`.

  A half-right document is worse than no document. It gets signed and handed over, and the
  consignor has no way to see which half was right. That is the whole reason for this
  release: the application was perfectly willing to produce one.

  **The lock is checked in three places, because the tile is not the only way in.** A
  bookmark reaches `/wizard/rail` without touching a tile, and a `default_modality` set
  while a modality was open navigates there on its own, on load, before anything is
  clicked. Guarding the tiles alone would guard the honest route and leave the other two
  open — the shape of lock that is found out in production rather than in review.

  The tiles are locked rather than hidden. Hiding them raises the wrong question — *where
  did rail go?* — where the true answer is *not yet, and here is why*, in all four
  languages.

### Added

- **`frontend/src/pages/ModalitySelectPage.test.tsx`** — six tests, three of them on the
  ways in that are not the tile.

## [1.59.0] — 2026-08-12

### Fixed

- **Inland waterway consignments were being answered with a road table, and the two do not
  ask the same question.** `docs/dg-coverage.md` has ranked "mixed loading for ADN answered
  with ADR's 7.5.2" as a gap for several releases, and that wording undersold it. It was
  labelled as borrowed, which sounds like an approximation. It is not.

  **ADR 7.5.2 asks whether two packages may share a vehicle, and answers yes or no. ADN
  7.1.4.3 asks how many metres must lie between them, and whether they may share a hold.**
  A distance was not an answer this application could give at all, so a consignor reading
  "permitted" on an inland waterway shipment was reading a yes to a question nobody had
  asked.

  Two of the three rules have no counterpart in the road regime at all:

  - **7.1.4.3.1** — goods of different classes at least **3.00 m** apart horizontally, and
    never stacked on one another.
  - **7.1.4.3.3** — class 1, and the three-blue-cone goods of 4.1 and 5.2, at least
    **12 m** from goods of every other class.
  - **7.1.4.3.2** — two blue cones may not share a hold with one-blue-cone flammable goods,
    whatever the quantity.

  Read from the official Dutch edition of ADN 2025, which is a text and not a recollection.

### Changed

- **What the check did *not* assess is named in its own output.** The blue cone provisions
  come out of column (12) of the ADN's own table A, and the application holds the road
  table, which has no column (12). So the class rules are applied and the cone rules are
  reported as unassessed. A check that silently drops half a provision is worse than one
  that says which half it kept — the first reads as a clean bill of health.

  The compatibility group table of 7.1.4.3.4 is not transcribed either, and says so:
  twelve groups, four numbered conditions, and footnotes that differ from the road table's.
  A regulatory table gets two independent readings in this repository or none.

  Both wait on the same thing: the ADN's own table A and table C, which come from UNECE.

## [1.58.0] — 2026-08-12

### Added

- **High consequence dangerous goods, ADR 1.10.3.** The last heading in
  `docs/dg-coverage.md` with nothing behind it: chapter 1.10 was named in the 1.1.3.6
  exemption text and nowhere else.

  Table 1.10.3.1.2 turns out to be *easier* than it looks — but only once it has been read.
  For carriage in packages its column holds two values and no others: **0**, meaning any
  quantity at all, and footnote **b)**, "whatever the quantity, the provisions of 1.10.3 do
  not apply". There is no threshold to compare against and no arithmetic to get wrong. It
  is a membership test.

  It is worth having because **the intuition it corrects runs the other way.** Flammable
  liquids, corrosives and packing group I oxidisers all look like the dangerous end of a
  load, and in packages every one of them is footnote b): a full truck of packaged petrol
  is not high consequence dangerous goods and does not become so at a larger quantity. What
  the table catches instead is class 1 — divisions 1.1, 1.2, 1.5, 1.6, division 1.3
  compatibility group C and fifteen named 1.4 entries — the toxic gases with aerosols
  excepted in the table's own words, the desensitised explosives, packing group I toxics and
  category A infectious substances. A single kilogram of any of those qualifies.

  Where a line qualifies, the finding asks for the security plan of 1.10.3.2 and the
  photographic identification of 1.10.1.4, and names the line that caused it.

  Two things are not answered and say so rather than defaulting to "ok": **class 7**, which
  1.10.3.1.3 measures in activity against 3,000 A2 with its own limits per radionuclide, and
  the **tank and bulk columns**, whose 3,000 litre and 3,000 kg thresholds are made relevant
  by footnotes c) and d) only where table A column (10), (12) or (17) permits that form of
  carriage.

- **`backend/tests/test_adr_security.py`** — 23 tests, again weighted towards the
  refusals, because a check that answers "no" to petrol and "yes" to chlorine is only
  useful if the "no" is trustworthy.

### Fixed

- **The language guard caught a verbatim Dutch quotation in the configuration**, which is
  the guard working rather than failing. Reshaping it as an `{nl, en}` pair then tripped the
  *translation* guard, which requires all four languages — also correct, since a two-language
  block is an incomplete translation to anything that cannot see intent. Both were right and
  the field was wrong: this repository does not redistribute regulatory text, only the facts
  read out of it, so the footnote is carried in rendering with its provision number and the
  original stays in the book.

## [1.57.0] — 2026-08-12

### Added

- **Placarding and marking of the vehicle, ADR 5.3.** The last of the seven gaps in
  `docs/dg-coverage.md`, and the one carrying the note that it is "the most common
  real-world failure". The application named chapter 5.3 in its 1.1.3.6 output — *orange
  plates and placards on the transport unit* — and derived nothing.

  **That sentence was also wrong, in the direction that matters.** 5.3.1.5 gives a vehicle
  carrying packages exactly two reasons to placard: 5.3.1.5.1 for class 1 other than
  division 1.4 compatibility group S, and 5.3.1.5.2 for class 7 other than excepted
  packages. A load of packaged petrol, nitric acid or toxic liquid needs **no placard at
  all** — the orange plates of 5.3.2.1.1 are the whole of it.

  Telling a driver to placard anyway is not a harmless excess. It teaches that the placard
  is decoration, and the next load where it *is* class 1 on board is the one where that
  lesson has already been learnt. So the refusal is a stated finding with its provision
  beside it, and not an empty list — an empty list reads as a check that did not run, and
  whoever cannot tell those apart will placard to be safe.

  Three things come with it:

  - **The two numbers, printed.** Where the consignment holds one dangerous substance and
    nothing else, 5.3.2.1.6 lets the front and rear plates carry the hazard identification
    number over the UN number instead of being blank. Both come out of table A — columns
    (20) and (1) — so the check prints them rather than describing them: `33 / UN 1203`.
  - **The environmentally hazardous mark hangs on the placard, not on the substance.**
    5.3.6.1 opens *"When a placard is required to be displayed in accordance with the
    provisions of section 5.3.1"*. So packaged environmentally hazardous class 9 puts no
    mark on the truck, while the same substance beside a class 1 line does. Reading 5.3.6
    without its opening clause would mark every vehicle carrying a marine pollutant. The
    finding says in the same breath that the mark on the *package* (5.2.1.8.3) is a
    separate question, so "not the case" cannot be read as relieving it.
  - **1.1.3.6.2 relieves the unit of the plates and the placards together.** Inside the
    exemption the section says so and stops.

  What is not answered is said rather than assumed: this is **carriage in packages**. Tanks
  and bulk have their own subsections of 5.3 — numbered plates on the sides under 5.3.2.1.2
  and 5.3.2.1.4, placards for every class rather than two — and the elevated temperature
  mark of 5.3.3 turns on a carriage temperature of 100 °C liquid or 240 °C solid, which
  nobody tells the application.

- **`scripts/read_land_regulations.py` can be asked for chapter 5.3 and chapter 1.10.** The
  provisions above were quoted from ADR 2025 Volume II on a runner and implemented from
  that text, not from memory of it — the rule this repository set for itself in v1.33.0.
  The Dutch edition was read alongside as a second reading; its complete-volume PDF turns
  out to have a text layer clipped at the right margin on about 5% of its lines, which is
  worth knowing before anyone quotes from it.

- **`backend/tests/test_adr_placarding.py`** — 18 tests, weighted towards the refusals,
  because those are the findings that are easy to get wrong in the safe-looking direction.

## [1.56.0] — 2026-08-12

### Changed

- **The classification table is ADR 2025, read out of the book.** It was an export of ADR
  **2023**. That was written down honestly — the manifest has said so since v1.49.0 — and
  patched where the gap showed: v1.52.0 carried the eleven rows 2025 added in by hand and
  flagged the two it withdrew.

  A patch covers what an edition *added*. It cannot cover what an edition *changed*, and
  2025 changes a field on **316 of the 2,334** UN numbers the two editions share. Three of
  those were answers the application was giving with confidence:

  - **UN 3423 tetramethylammonium hydroxide, solid** is class **6.1**, not class 8. Labels
    6.1 + 8 instead of 8, transport category 1 instead of 2, and hazard identification
    number **668** instead of 80 — the number that goes on the orange plate.
  - **The three UN 0015 rows** have their own subsidiary hazard back: 1, 1 + 8 and 1 + 6.1.
    The export gave all three the same labels column, so the corrosive and the toxic
    variant lost their second label on the way to the document, and nothing distinguished
    the rows well enough to warn about it.
  - **UN 1950 aerosols** now stand in the ADR's own order, which opens at 5F — the
    flammable spray can, and the overwhelmingly common case. The export was sorted
    alphabetically by classification code, so an aerosol whose code the user had not given
    was filled in as 5A, the *non-flammable* row. That is the exact reading v1.51.0
    measured as costing a factor of three in 1.1.3.6 points.

  All twenty-three columns are read by the new `scripts/extract_adr_table_a.py`: **3,158
  rows over 2,345 UN numbers, no unreadable page**. Four columns the application did not
  hold before come with it — the carriage provisions of (16) to (19), the V, VC/AP, CV and
  S codes.

- **The alphabetical index turns out to be the whole of table A, set a second time.** 325
  pages against 294, different column widths, different line breaks — an independent
  typesetting of the same data. So every field is read twice and the two readings are laid
  against each other, which is the discipline this repository already applies to a machine
  reading and which could previously only be applied to the names.

  | | |
  |---|---|
  | classification code, packing group, labels, special provisions, LQ, EQ, packing instructions, all four carriage columns, hazard number, tunnel code | agree on **every** one of the 2,345 UN numbers |
  | class, transport category | agree on all but eight |

  The sixteen that differ are named rather than rounded away. Eight are the *index* failing
  over one run of its own pages — every iodine entry, which the alphabetical order puts
  together — and three are classes the table dropped that the index supplied, which is what
  a second reading is for.

- **The eleven rows transcribed by hand in v1.52.0 have become the check on the machine.**
  `adr_2025_additions.json` has stopped being a source the application reads and is now a
  fixture: a reading made by eye, off the page, of the hardest rows in the book, for the
  machine reading to be compared against. Two methods, one page, and they agree.

- **Which UN numbers ADR 2025 no longer knows is derived, not listed.** It is the
  difference between the two tables — UN 1499 and UN 1999 — and a difference cannot be
  forgotten at the next edition the way a hand-kept list can.

### Fixed

- **`is_transport_forbidden` was reading a German sentence out of a Dutch table.** The 2023
  export wrote `BEFÖRDERUNG VERBOTEN` across the row of a substance not admitted for
  carriage, and the check looked for that word in the labels column. The Dutch edition
  writes nothing at all — the row is simply empty.

  Reading the emptiness instead would have been worse than the bug: **it is also how "not
  subject to ADR" is written.** UN 1798 nitrohydrochloric acid may not be carried and UN
  1845 dry ice travels freely, and their rows are equally blank. So the prohibition is
  taken from the export, which names it in words, and the manifest errata says that is
  where it comes from. Nineteen entries that travel freely would have been refused
  otherwise.

- **The packing instruction was cut at the first space.** Table A separates the
  instructions with commas — `P001, IBC02, R001` — where the export used spaces, so the
  field came back as `P001,` with the comma attached.

### Added

- **`scripts/extract_adr_table_a.py`.** What the reading had to survive is in its module
  docstring, because none of it is guessable from the output: there are no column rules
  anywhere in the table, the layout is made anew on every page, the column numbers are
  centred over cells whose content is left-aligned, a wrapped name leaves an indent that is
  every bit as sharp a mode as a real column, the UN number is set vertically centred so a
  row does not begin where its number is, and two cells can abut with nothing between them
  so that the text layer hands over `(B1000C)V2` as a single word.

- **`backend/tests/test_adr_table_a.py`** — 24 tests over both halves of the claim: that
  the reading is sound, and that the change reached the checks that compute with it.

## [1.55.1] — 2026-08-11

### Changed

- **The repository speaks English again, including where the guard could not
  look.** v1.46.0 translated some 3,000 lines of comment and left
  `test_source_language.py` behind to keep them that way. That guard throws away
  every quoted string before it looks, on purpose — the import format really is
  `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks` and a guard that fired on it
  would be switched off within the week. The exemption turned out to be a hole,
  and four kinds of prose fell through it:

  - **The changelog.** English until v1.49.0, when ten releases' worth of Dutch
    entries went in — mine, because the person I write to writes Dutch. Nobody
    reading the repository does. All ten are translated, along with v1.34.1,
    which had been Dutch since it was written. The one Dutch fragment that stays
    is the quoted error message in v1.24.1: it is an example of what the app
    actually renders.
  - **Provenance metadata in the seeds.** The `_comment`, `source` and
    `cross_check` fields say where a table came from and how it was checked —
    the closest thing this project has to a chain of custody, and written for a
    reader rather than for the code.
  - **What the scripts print.** `--help` and the self-check output of
    `scripts/extract_*.py` are the interface of a tool a contributor runs, and
    they answered in Dutch.
  - **The workflow inputs.** What `commit`, `min_agreement` and `show_un` mean
    is read from the Actions tab, and `tag-release.yml` refused a mismatched
    version in Dutch.

  The `{nl, en, de, fr}` blocks, the goods names, the Dutch proper shipping
  names out of ADR Table A and `DISCLAIMER.nl.md` are untouched. Those are the
  product.

- **The rule set manifest reads in English.** It is provenance rather than
  interface, but one line of it reaches the screen: the compliance panel shows
  the editions the result was computed with. That line now says
  `2025, with a Table A from the 2023 edition` and `67th edition (2026)`.

### Fixed

- **The comment guard could not see a JSX comment.** It read `//` and a `/*` at
  the start of a line, which is not how a comment is written inside JSX — that
  is `{/* … */}`, and it is the form the panels use. Six Dutch comments had sat
  in `DgCompliancePanel`, `DangerousGoodsStep`, `ImportColumnMapping` and
  `ResponsiveRecords` since v1.46.0 without the guard ever looking at them. It
  looks now, and found them on the first run.

- **A workflow's own prose was never scanned at all** — only its `#` comments
  were. Input descriptions, `::error::` and `::warning::` output and `echo`
  lines are what a person reading the Actions tab sees, so they are read now
  too.

### Added

- **`test_repository_language.py`**, covering the three places the older guard
  cannot reach by design: the changelog with its code spans removed, the
  provenance metadata in `backend/seed` and `backend/app/config`, and — read out
  of the syntax tree rather than with a regular expression — everything the
  scripts print. Each has a companion assertion that the scan reaches the files
  it claims to, because a scan of nothing passes just as well as a scan of
  something clean. The translation exemption is asserted rather than assumed:
  the day someone tightens this, `"nl": "Gescheiden van (separated from)"` must
  not start failing, because the fix for that would be to delete Dutch a user is
  meant to read.

## [1.55.0] — 2026-08-11

### Changed

- **The lines table now shows only the columns that genuinely fit; the rest are in the
  detail panel.** The panel of v1.54.0 gave the line the full width, but the table itself
  went on showing all thirteen columns and therefore scrolling sideways. Now the columns
  that no longer fit fall away, and that is allowed because nothing is lost: what falls
  away is in the panel, and the table says underneath how many that is.

  **Measured on the table itself and not on the window,** because here the two are not the
  same thing: the side menu can be folded open during the wizard and costs 224px. A
  breakpoint on the window width would then go on showing thirteen columns in the room for
  six. A `ResizeObserver` on the table is right in both cases.

  The columns are ranked by what you need while entering lines:

  | | Columns |
  |---|---|
  | Always stay | Description, Quantity |
  | Then | Total mass, Status, Dangerous goods package |
  | Then | Length, Width, Height |
  | Then | Mass each, Cargo form |
  | Last | Volume, Wall thickness |

  What that yields, measured in the browser, in every case **without scrolling sideways**:
  1920px all thirteen columns, 1536px eleven, 1280px nine, 1024px six.

  Two things go wrong otherwise, and both are pinned separately: length, width and height
  are treated as one — showing two of the three because the third happened to fall over the
  edge reads as a fault — and as soon as a column no longer fits it stops, rather than
  skipping that one and trying the next. The latter made the volume appear at 700px while
  the total mass fell away, and a table that leaves out the figure the whole step is for
  but does show the volume looks broken.

- **The detail icon is now a document with a magnifying glass**, instead of the list.

## [1.54.0] — 2026-08-11

### Added

- **A detail button per line, sliding a panel in from the right with every column under
  each other.** The lines table has thirteen columns of input fields and wants 1,620px; on
  anything narrower something has to give — the table scrolls sideways or the fields get
  squeezed. This is the third way out: the line you are working on gets the full width of a
  panel, one field per row, and the table may stay as wide or as narrow as it likes.

  The panel holds the **same fields** as the row behind it, not a readable copy. A panel you
  can only read would send you back to the cramped table to change anything. The line's
  actions come along at the bottom.

  The panel belongs to `ResponsiveRecords` and not to the lines table, because it has the
  same shape as the mobile card: label and value under each other. That component already
  knew how. Desktop only, because on a phone the card *is* that view.

  Further: Escape and the cross close it, focus moves into the panel and back to the button
  on closing, the page behind it is locked while it is open, and a line that disappears from
  under the panel takes the panel with it — the panel holds the line by its key and not by
  its place in the list.

- **The action buttons sit side by side and stay on the right.** They used to stack because
  the cell was too narrow for two 36px buttons; with the panel there is room for three. And
  the column is pinned to the right-hand edge, because the very button that makes the
  sideways scrolling unnecessary was itself behind that scrolling.

### Fixed

- **The description could revert itself.** The description box keeps the typed text in its
  own hands — it needs it for searching the catalogue — and never looked at the value it
  was given from outside again after the first render. With one box on screen that is
  invisible. The detail panel puts a second one on the same line: type in one and the other
  still showed the old text, and the moment you touched it, it wrote that old text back over
  what you had just entered.

## [1.53.1] — 2026-08-11

### Fixed

- **The lines table did not fit on the screen, and the input fields were too narrow to type
  anything into.** Three things worked against each other, and only all three together
  produced a usable table. Measured in the browser: the table *wants* 1,620px and was given
  1,214.

  - **The side menu folds away as soon as the modality is chosen**, with an animation to the
    left, and the button at the top left always folds it back. That is 224px. The menu
    follows the route once — on the way into the wizard and on the way out — and after that
    the user decides; otherwise it folds itself shut again the moment you open it.
  - **The shell may use the screen while the menu is away.** Folding alone was not enough:
    the app is capped at 80rem, so on a wide monitor those 224px went into the margin and
    the table was no better off. With the menu away the cap moves to 1,800px, header and
    content together so that they stay in line.
  - **The table has been given a floor.** A `w-full` table can never be wider than its
    container, so the `overflow-x-auto` around it never engaged and the browser took the
    missing width out of the cells. On a table you *read* that is fine — text wraps. On a
    table you *type* in it is not: the quantity field became 30px and the unit select 28px.
    Now the table keeps the width its fields need and scrolls horizontally when the screen
    is too small for it.

  At 1920px everything now fits without scrolling, with the quantity field and the unit
  select each a good 100px. At 1440px only the table scrolls, not the page.

## [1.53.0] — 2026-08-10

### Added

- **The transport unit's equipment is derived from the load (ADR 8.1.4 and 8.1.5).**
  Equipment was the one heading in `docs/dg-coverage.md` that called itself "the most common
  real-world failure" and was absent from every mode. That had a reason worth naming:
  CargoPilot cannot see a vehicle and can therefore never establish *that* a wheel chock is
  in the cab.

  What the app *can* do is derive the list — and 8.1.5.1 asks for exactly that: the
  equipment is chosen *according to the hazard label numbers of the goods loaded*, and the
  article points at the transport document to identify those numbers. That is precisely the
  document this app draws up.

  - **8.1.5.2** — wheel chock, two warning signs, and per crew member a warning vest, a
    portable lighting apparatus, gloves and eye protection.
  - **The eye-rinsing liquid is an exemption, not a requirement.** The footnote says it is
    *not* prescribed for label numbers 1, 1.4, 1.5, 1.6, 2.1, 2.2 and 2.3. A load of propane
    cylinders is therefore not asked for one — but ammonia (2.3 *with* subsidiary hazard 8)
    is, because that one label 8 is not on the list.
  - **8.1.5.3** — an escape mask per crew member for label numbers 2.3 or 6.1, and a shovel,
    a drain seal and a collecting container for label numbers 3, 4.1, 4.3, 8 and 9 — but for
    solids and liquids only. A gas cylinder with a subsidiary label 8 has no use for a
    shovel.
  - **8.1.4.1** comes with the whole table instead of one answer, because the extinguishers
    hang on the maximum permissible mass of the transport unit and the app does not know it.
    If the consignment stays within 1.1.3.6, **8.1.4.2** replaces that table with a single
    2 kg extinguisher — one of the few places where the exemption makes a visible difference
    to what belongs in the cab.

  The label number is not the class, and that is exactly what it turns on: class 2 is "2" in
  the class column and 2.1, 2.2 or 2.3 on the label, and the footnote names the divisions.
  Read the class column and the exemption never applies to gases at all.

  The panel says what it is: a list to check against, not a finding.

## [1.52.0] — 2026-08-10

### Added

- **The eleven rows ADR 2025 added are now in, with their road transport data.**
  The classification table the app is built on is a **2023** export. UN 0514 and
  UN 3551 through 3560 — sodium-ion batteries, the new vehicle entries, disilane,
  gallium in manufactured articles and tetramethylammonium hydroxide — did reach the
  app through the IMDG 42-24 layer, but with **sea data**: no transport category, no
  tunnel code, no Kemler number. Those three columns exist only in ADR Table A.

  So anyone shipping sodium-ion batteries by road got no points factor, and the
  1.1.3.6 table reported the line as incomplete without being able to say *what* was
  missing.

  Eleven rows is few enough to transcribe by hand, and that is also how this repository
  deals with a regulatory table. What makes it defensible is the same discipline as
  everywhere else: every row was **read twice**, from Table A and from the alphabetical
  index of the same edition — two independent typesettings — and the page it appears on
  was recorded with it.

  | UN | Transport category | Tunnel code | Kemler |
  |---|---|---|---|
  | 0514 | 4 | E | — |
  | 3551 / 3552 | 2 | E | — |
  | 3553 | 2 | B/D | 23 |
  | 3554 | 3 | E | — |
  | 3555 | 2 | B | — |
  | 3556 / 3557 / 3558 | — | — | — |
  | 3559 | 4 | E | — |
  | 3560 | 1 | C/E | 668 |

  That the vehicle entries get no transport category and no tunnel code is not a
  misreading: UN 3166 and UN 3171 do not have them in the existing table either.

### Changed

- **UN 1499 and UN 1999 now say for themselves that ADR 2025 no longer knows them.** They
  remain findable — an older transport document may refer to them, and a lookup that
  returns nothing reads as "this UN number does not exist" — but they no longer pass for a
  current entry.

## [1.51.0] — 2026-08-10

### Fixed

- **One UN number, several Table A rows — and the app silently picked one.** This is the
  most expensive thing the pass over the ADR side turned up.

  The row was chosen on **packing group**, and a warning appeared as soon as a UN number
  had more than one. That covers UN 1263 paint and UN 1993 N.O.S. and it reads like the
  whole problem. It is not.

  **UN 1950, aerosols, has twelve rows in Table A and not one of them has a packing
  group.** They are told apart by the classification code in column (3b):

  | Code | Labels | Transport category | Tunnel code |
  |---|---|---|---|
  | 5A | 2.2 | 3 | E |
  | 5F | 2.1 | 2 | D |
  | 5T | 2.2 + 6.1 | 1 | D |

  Anyone shipping ordinary flammable aerosols — by far the most common case — got the
  non-flammable row. Transport category 3 instead of 2 is a points factor of 1 where the
  ADR prescribes 3, so a load of aerosols scored a third of what it should and could keep
  an exemption it had actually lost. The tunnel code came out as E instead of D, and the
  flammable label was missing from the document. Without a word, because every row has the
  same (empty) packing group.

  UN 2037 gas cartridges has nine such rows. UN 0015, 0016 and 0303 have three each that
  differ only in whether the ammunition carries a corrosive or a toxic label — a subsidiary
  hazard that dropped silently off the description line. And even choosing a packing group
  does not always settle it: UN 1263 has three PG III rows, one with tunnel code D/E and
  Kemler 30 and two with tunnel code E and neither.

  Fifteen UN numbers were resolved this quietly. The row is now chosen on classification
  code first, and what remains open is named: how many rows, what they differ in, and which
  field decides it. Where no field the user fills in tells them apart — the three ammunition
  rows are all 1.2G — the note says so, instead of naming a field that cannot work.

- **Fourteen UN numbers have no usable English proper shipping name, and the German one was
  substituted without notice.** UN 3245 genetically modified organisms, UN 3374 acetylene
  solvent free, UN 2807 magnetized material and eleven others have an empty `name_en` in
  the Table A export; UN 1139 has the truncated "Coating solution (". The fallback to
  German stays — an empty field is worse — but the export now warns: IMDG 5.4.1.4.1 and
  IATA DGR 8.1.2.1 require English, and ADR 5.4.1.4.1 asks for English, French or German
  alongside the Dutch.

## [1.50.0] — 2026-08-10

### Added

- **The tunnel code is now worked out as well, not just printed.** The code from column (15)
  was already on the transport document — 5.4.1.1.1 (k) asks for it — and was assessed
  nowhere else. That is the more dangerous half of the two: anyone reading `(D/E)` on a CMR
  may assume someone thought about what that means for *this* load. They had not.

  Read from ADR 2025 and applied:

  - **8.6.3.2** — the most restrictive code in the load applies to the **whole** load. A
    driver picks one route and needs one code, not a list to weigh up. The order of
    restrictiveness is nowhere written out in words; it is the order of the table in 8.6.4,
    and that is where it comes from.
  - **8.6.3.3** — goods carried in accordance with 1.1.3 are not subject to tunnel
    restrictions **and do not count** towards establishing the code. So for a consignment
    within the 1.1.3.6 exemption there is no code to assign at all. The one exception the
    article names: a transport unit that must carry the LQ marking of 3.4.13 is barred from
    category E tunnels, however mild the codes of the goods themselves are.
  - **The table in 8.6.4** — which tunnel categories are prohibited per code. `B1000C` and
    `C5000D` split on the total net explosive mass per transport unit, and that is summed
    over the whole unit rather than read per line. The worked example from the ADR itself —
    UN 0161, 3,000 kg, prohibited by D and E — is fixed as a test.

  The outcome appears in the compliance panel and with the export. What CargoPilot does not
  know is stated alongside it: which tunnels lie on the route and what category they fall
  in (that is the carrier's, 1.9.5), and whether carriage is in bulk or in tanks — which is
  stricter for five of the twelve codes.

- **ADR 3.5.1.3 and 3.5.1.4 are applied.** Two provisions that are only visible across
  lines, and that went wrong in opposite directions:

  - **3.5.1.3** — excepted quantities with different E codes packed together in one outer
    packaging are bounded by the most restrictive code. 400 g of an E1 substance next to
    200 g of an E3 substance is above the 300 g that then applies, while each line on its
    own sits well within its own code. Exactly the package the line-by-line check let
    through.
  - **3.5.1.4** — the smallest quantities under E1, E2, E4 and E5 (at most 1 g/ml per inner
    packaging and 100 g/ml per package) are subject only to 3.5.2 and 3.5.3. The mark of
    3.5.4 and the limit of 1000 packages in 3.5.5 then do not apply — so those packages no
    longer count towards that limit. The app was refusing a load the ADR allows.

### Changed

- **The 8.6.3 outcome goes onto the document.** The code per substance was already on it;
  the code for the whole load — the one 8.6.3.2 asks for and the one the driver acts on —
  had never been.

## [1.49.0] — 2026-08-10

### Added

- **The Dutch proper shipping names from the ADR are now in.** Until now the app knew every
  UN number only by its English and German name, because the Table A export it is built on
  has only those two columns. In four places in the source and the documentation it
  therefore said the ADR has no Dutch name. That is not true. The ADR appears in an
  official Dutch edition and column (2) of Table A reads BENZINE, ZOUTZUUR,
  LITHIUM-ION-BATTERIJEN there. Only the export did not have it.

  That column has now been read out: **2,345 UN numbers, 3,158 rows, 294 pages**. There is
  no open source for it — this column is nowhere on the internet — so it was read from the
  book itself by the new `scripts/extract_adr_names.py`. The book itself does not go into
  the repository; only the derived fact, exactly as `docs/data-sources.md` promises for
  every other regulatory source.

- **Searching on a Dutch substance name works.** Typing "zoutzuur" returned nothing,
  because the search index held only English and German. UN 1789 is now top of the list,
  "benzine" finds UN 1203 and "lithium-ion" finds UN 3480.

### Changed

- **A Dutch road document carries both names.** ADR 5.4.1.4.1 asks for an official language
  of the country of dispatch and, if that is not English, French or German, **in addition**
  for one of those three. Dutch is the only language that therefore cannot stand alone. The
  description line now reads `UN 1203, BENZINE OF MOTORBRANDSTOF (GASOLINE), 3, II, (D/E),
  10 jerrycan, 200 L` — on the CMR, on the AVC consignment note and in the field itself.
  For sea and air it stays the English name alone, because IMDG 5.4.1.4.1 and IATA DGR
  8.1.2.1 want one. Draw up a Dutch road document first and add a sea leg afterwards and
  the IMO DGD gets `GASOLINE` by itself, just as with the German name.

- **The regulatory manifest now says what is really in there.** While reading out the Dutch
  names the classification table turned out to be an **ADR 2023** export, not a 2025 one,
  while the manifest reported "2025". That is now stated, along with what it costs: UN 0514
  and UN 3551 through 3560 are missing from that table — they are in the app, but with sea
  data from IMDG 42-24 and without transport category, tunnel code and Kemler number — and
  UN 1499 and UN 1999 are still in it while ADR 2025 no longer knows them.

### Fixed

- **Clicking a search suggestion undid what the list had got right.** The suggestion showed
  the name in the language the chosen profile allows, but clicking it put the English
  column in the field. The field now gets what was in the list.

## [1.48.0] — 2026-08-09

### Fixed

- **The error messages spoke Dutch, and only Dutch.** Everything on screen was translated
  into four languages and the errors were not: they were written straight into the `raise`
  as Dutch sentences. A German user who uploaded an empty file was told so in Dutch; so was
  a French one who asked after a UN number the ADR table does not hold. Nineteen messages
  in all — ten HTTP errors, six import limits, two quantity validators and the per-row
  message of the equipment import.

  It is the kind of gap nobody reports, because it only appears once something has already
  gone wrong — the moment the user is least able to work out what happened.

- **The equipment import reported its per-row problems in Dutch too**, in a list shown
  verbatim on screen. Those are now structured the same way and translated per row.

- **An upload error read "Upload failed" where the server had said exactly what was
  wrong.** `uploadFile` assumed `detail` was a string and fell back to a generic sentence
  for anything else. It now goes through the same reader as every other error.

### Changed

- **The server no longer writes sentences; it writes codes.** It cannot translate: an
  error is raised deep in a service that has no idea who is asking, and the language
  belongs to the screen. So the API sends `{"code", "message", "params"}` — the interface
  looks the code up in its own language files and falls back to the English `message` when
  it does not know it.

  That fallback is what makes it safe to deploy: a backend newer than the frontend in
  front of it can send a code the language files do not have yet, and the user still reads
  a sentence rather than a dotted key.

  Schema validators use `PydanticCustomError`, which puts the code in the `type` field of
  the 422 body and the parameters in `ctx` — the mechanism FastAPI already had, rather than
  a convention invented on top of the message text.

- **The operator log speaks English**, along with the rest of the source. The startup
  messages about `APP_SECRET_KEY`, CORS and the admin password were the last Dutch text
  outside the language files.

- Tests that matched on a Dutch sentence now assert on the code. Pinning the wording of a
  message is what makes it painful to translate — and these had to be changed by hand for
  exactly that reason.

### Added

- **`test_error_messages.py`.** Every code has a translation in all four languages; the
  interpolation names survive that translation, because a sentence that loses its
  `{{limit_mb}}` loses the number it was about; the Dutch file is not the English one
  copied; and — the guard that matters most — no message to the user is written in Dutch
  at the raise site any more. That last one reads the `raise` calls rather than the
  catalogue, because a sentence typed straight into `HTTPException` never passes through
  the catalogue at all.

  Both guards were verified by breaking the code on purpose and watching them fail.

### Documentation

- `AGENTS.md` and `docs/development.md` state the rule, so the next message added goes
  through the catalogue instead of round it.
- `docs/user-guide.md` adds error messages to the list of what follows your language.

## [1.47.0] — 2026-08-09

### Fixed

- **`MAX_PASTE_BYTES` was a setting that did nothing.** It sat in `Settings` with a
  default of 512000 and in `docs/configuration.md` as "maximum size of a pasted import",
  and no line of the application ever read it. The upload cap has always come from
  `MAX_IMPORT_BYTES` in `spreadsheet_io.py` — 10 MB, alongside caps on rows, columns and
  uncompressed `.xlsx` size that are safety limits against a malformed file, not
  preferences. The variable is gone and the real limits are documented instead.

  A documented setting that does nothing is worse than an undocumented one: it invites
  somebody to tune it and then conclude the app ignores them.

- **`APP_NAME` was documented as "the name shown in the interface".** It is the FastAPI
  title and the `app` field of `GET /api/health`; the interface takes its name from its
  own language files and always has.

- **`ROADMAP.md` still advertised 400 goods**, three releases after the catalogue reached
  1,093 — and Dutch, English and German, two releases after French. Nothing breaks; the
  number was simply a lie in the shop window.

- **`docs/getting-started.md` pinned v1.33.0** as the example version to pull and to keep
  when cleaning up Docker Hub tags.

- **`2,928 UN numbers` was never right.** `un_numbers.json` holds 2,928 ADR Table A
  **rows** over **2,336 UN numbers** — a substance with several packing groups has a row
  per group. Three documents stated the row count as a UN-number count. Every other figure
  on those pages was re-measured against the seed files and is correct: 2,338 EmS
  schedules, 2,860 DGL rows over 2,347 UN numbers, 629 segregation assignments over 539 UN
  numbers, 110 stowage/handling/segregation codes, 2,849 UN cards.

- Missing entries in three tables of contents, including the **Settings** section added in
  v1.45.0.

### Added

- **`test_documentation_matches_the_app.py`.** Three guards, each pinning a defect this
  pass actually found: every `Settings` field is documented and every documented variable
  is still a setting; the goods count claimed anywhere in the documentation is the count
  in `materials.json`; and every internal link resolves to a file *and* an anchor that
  exists. Prose and regulatory reasoning are deliberately not guarded — those cannot be
  checked mechanically and the suite should not pretend otherwise.

- **`docs/development.md` explains that there is no migration runner.** `create_all`
  creates missing tables and never adds a column to an existing one, which is why the
  settings tables hold JSON and why `startup.SETTINGS_TABLES` exists. That was load-bearing
  knowledge living only in a test docstring.

### Documentation

- The **Settings** screen now appears where a reader would look for it: the transport-mode
  step of the user guide, the signature section of `docs/documents.md`, the first-admin and
  troubleshooting sections of `docs/getting-started.md` — the last of those because
  "address search returns nothing" now has a legitimate cause that is not a fault.
- `docs/dg-coverage.md` is stamped v1.47.0 with a note that nothing in it has changed since
  v1.41.0: v1.42.0 to v1.46.0 touched the catalogue, the interface language, the settings
  and the source comments, and not one regulatory check.
- `.env.example` speaks English along with the rest of the source.

## [1.46.0] — 2026-08-09

### Changed

- **The source speaks English.** Roughly **3,000 lines of comment and docstring**
  across `backend/app`, `backend/tests`, `scripts/`, `frontend/src`, the workflows and
  `.env.example` were Dutch. That was defensible while one person wrote all of it and
  stopped being defensible the moment anyone else read it — because this project puts a
  great deal of its reasoning *in* those docstrings. A test that explains which defect
  provoked it is worth nothing to a reader who cannot read the explanation.

  Nothing a **user** reads changed. The interface files, the seed labels, the field
  names and the regulatory texts stay in four languages; only what a developer reads was
  translated. The test docstrings kept their length and their voice — they still name the
  defect, the measurement and the trade-off, in English now.

- **A new package line starts in `pcs`.** Left over from v1.45.0: `WizardPage` still had
  the Dutch string in two more places.

### Added

- **`test_source_language.py` keeps it that way.** Without a guard, the next change adds
  one Dutch comment, the one after it adds three, and in a year the work has to be done
  again. It scans every comment and docstring in those five trees.

  Two things it does *not* do, both deliberate. It ignores text inside string literals,
  because Dutch in a string is data — the import format is
  `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks` and the AVC form's own column is called
  `gewicht in kg`. And its word list holds only function words, leaving out anything that
  collides with English: "door" is a Dutch preposition and an English noun, and this
  repository really does write about the back door of a CI pipeline. A guard that cries
  wolf gets switched off.

### Documentation

- `AGENTS.md`, `CONTRIBUTING.md` and `docs/development.md` state the rule, so it is a
  convention rather than a one-off sweep. `AGENTS.md` also still said "three interface
  languages"; French arrived in v1.44.0.

### Internal

- The translation ran through a line-based extract/splice tool rather than an AST pass.
  The previous bulk edit in this repository used `ast` column offsets, which count UTF-8
  **bytes**, and dropped text outside the braces of every dict containing a word like
  "Träger". Whole lines have no such trap. The tool also refuses to replace a block that
  contains code — a string constant's closing `"""` looks exactly like a docstring
  opening, and three such blocks were caught that way instead of deleting the code
  between them.

## [1.45.0] — 2026-08-09

### Added

- **Settings that belong to you, and settings that belong to the installation.** Until now
  the settings screen offered two things: a theme and a language. Both lived in
  `localStorage`, which is to say in one browser — sign in from a second device and the app
  was back in Dutch on a white background. Neither was ever really *yours*.

  They are stored with the account now, and they brought company. Per user: the transport
  mode to open straight into, the unit a new package line starts with, and the details that
  are the same on every consignment and were retyped on every consignment — consignor name,
  address and contact, the usual carrier, the loading point, the 24-hour emergency number
  that IMDG 5.4.1.5.11 and the IATA DGR shipper's declaration both ask for, and a signature
  drawn once instead of once per shipment. They are filled in only where the field is still
  empty: a prefill that overwrites what somebody just typed is worse than no prefill.

- **An administrator section.** Instance-wide, behind `require_admin`, and it exists mainly
  for one question: *does this installation talk to the internet?* Address autocomplete and
  the startup catalogue sync are the only two requests CargoPilot makes outward, and they
  now have switches next to each other. Also there: the language and theme new users start
  with, the organisation name and address offered as a consignor to anyone who has not
  filled in their own, whether the UN card download is offered, and how long a session
  lasts.

  Each switch was checked through the endpoint it governs rather than only through the
  store. A toggle that saves but changes nothing is worse than no toggle — the
  administrator believes address lookups are off.

- **The environment variables still decide when nothing is saved.** `GEO_ADDRESS_API_URL`,
  `CATALOG_AUTO_SYNC` and `ACCESS_TOKEN_EXPIRE_MINUTES` were the only way to configure
  these until now and are documented as such. A stored setting is an *overlay* on top of
  them, so an installation that never opens this screen behaves exactly as its `.env` says.
  What it gains is that a change no longer needs a container restart.

### Changed

- **A new package line starts in `pcs`, not `stuks`.** The default unit was the literal
  Dutch string, hard-coded in the wizard, and it reached German and French screens too.

### Fixed

- **The French translation was never actually compared.** `translations.test.ts` checks
  that every language file carries the same keys, in a loop that read
  `for (const language of ["en", "de"])`. French was added in v1.44.0 and fell outside it —
  the language with the most room for gaps was the one language not being checked. The loop
  is derived from `SUPPORTED_LANGUAGES` now, so a fifth language cannot slip past it either.

### Internal

- **The settings tables hold one JSON document each, and that is deliberate.** This
  application has no migration runner: `init_app` calls `Base.metadata.create_all`, which
  creates *missing tables* but never adds a column to a table that already exists. A
  column-per-setting schema would have worked perfectly on a fresh install and broken every
  upgrade with "no such column". With a JSON payload the schema never changes again —
  adding a preference is a field on a Pydantic model, and a database written by an older
  version simply lacks the key and falls back to its default. `test_settings.py` pins that
  in both directions, along with what a corrupt or no-longer-valid payload must do: fall
  back, not take the app down.

- Removed a dead `Field` component and its style constant from `WizardPage.tsx`.

### Documentation

- `docs/configuration.md` opens with which of the two places wins, and a table of the
  environment variables that now have a screen counterpart — including when each takes
  effect, because the catalogue sync is read at startup and cannot take effect sooner.
- `docs/user-guide.md` has a **Settings** section, with the administrator part separate.
- `docs/privacy.md` names the stored signature explicitly. It is the only image CargoPilot
  keeps, it is opt-in, and a document about what is *not* stored has to be exact about what
  now is.

## [1.44.0] — 2026-08-09

### Added

- **French, as a fourth language.** Not for reach — for the regulations. ADR, RID and ADN
  are published by UNECE and OTIF in English, **French** and Russian; the CMR and the CIM
  are French documents by origin, abbreviations included. Anyone preparing a waybill for a
  Belgian, French, Luxembourgish or Swiss leg needs the French wording because the
  authority at the roadside reads it, not as a courtesy.

  Complete on arrival, because a half language is worse than none: **1,706 translated
  blocks** in the data files, **161 dictionaries in the source code**, **335 interface keys**
  and the **1,093 goods** of the catalogue.

  The vocabulary is the one the French editions use, not a dictionary rendering: *fût* and
  *jerricane* rather than "tonneau", **GRV** for an IBC, *désignation officielle de
  transport* for the proper shipping name, *séparation* against *arrimage*, *disposition
  spéciale* for a special provision, and for the CMR the terms of the convention itself —
  *expéditeur*, *destinataire*, *prescriptions d'affranchissement*.

  A missing French text falls back to English before Dutch: that reader gets further with
  English. It should rarely fire — `test_languages.py` refuses an incomplete language — but
  it does apply to goods a user adds or renames themselves.

### Changed

- **The language guards no longer name a language.** `test_languages.py`,
  `test_catalog_search_language.py` and the frontend's `translations.test.ts` had `"de"`
  written into them. That is fine until a fourth language arrives, and then the guard does
  not guard it: the tests kept passing while French was missing everywhere, and two of them
  actually *failed* on French being present because they asserted the set was exactly
  `{nl, en, de}`. A guard that treats a new language as an error is not a guard.

  They all read `SUPPORTED` now and require every language in it beyond the two source
  languages. Switching on a fifth is one line in `app/core/languages.py`, and the tests
  immediately say what is missing.

### Fixed

- **The French for boxwood is *buis*, which is Dutch for a pipe.** The catalogue search
  deliberately matches across all languages — someone typing "Stahl" while reading Dutch
  should still find steel — so a bare `Buis` on boxwood outranked every Dutch search for a
  tube. Boxwood is now `Bois de buis`, which is equally correct and does not collide. Found
  by two existing tests, which is what they are for.

### Documentation

- README, `CONTRIBUTING.md`, `docs/user-guide.md`, `docs/data-sources.md` and
  `docs/development.md` name the fourth language.

- **`docs/dangerous-goods.md` states what French does *not* get.** The interface, the
  labels, the compliance findings and the goods database are French; the proper shipping
  name is not. The ADR Table A export this application is built on carries an English and a
  German name column and no French one, so a French user preparing a road document gets the
  English name rather than `ESSENCE`. That is a gap in the data, not in the translation, and
  it is written down rather than papered over with a name no table prescribes.

## [1.43.0] — 2026-08-09

A clearing-out. Nothing here changes what the application answers; it changes how much of
it there is.

### Removed

- **Two scripts that had finished their work.** `purge-history.sh` says so itself — *"Status:
  reeds uitgevoerd (juli 2026)"* — and `cleanup-dockerhub-tags.sh` was never wired to
  anything: the Cleanup Docker Hub tags workflow carries its own copy of that logic inline.
  Both remain in the git history if they are ever wanted back.

- **Four functions with no callers anywhere**: `decode_access_token` (a compatibility
  helper for callers that never arrived), `stowage_code_text`, `manifest_summary`, and the
  four schema classes `MaterialBase`, `MaterialOut`, `ProfileBase`, `ProfileOut`.

- **Twelve unused imports** across the backend, the tests and the scripts.

### Changed

- **The pipeline computes the solid block through `calc_solid_block` instead of writing the
  formula out again.** This is the one item here that is more than tidying. The calculation
  engine holds a function for it, and the pipeline computed `w * h * length_m` and then
  `* density` in two separate branches — the same formula in three places, two of them out
  of reach of the tests that check the engine. It is the pattern this project has paid for
  four times: `calc_round_bar` and `calc_round_tube` also sat there uncalled until v1.37.1,
  and a round bar weighed 27% too much for as long as they did.

  `test_no_dead_code.py` now asserts the general form of it: every `calc_` function in the
  engine has a caller outside the engine.

- **A `.dockerignore`.** There was none, so the whole working tree went to the daemon as
  build context on every build, `.git` included. Measured: **637 MB before, 586 MB after**.

### Documentation

- **`un_cards/` is not empty, and the cost is now written down.** Both `docs/data-sources.md`
  and the `Dockerfile` said the folder is empty in a fresh checkout and gets filled by a
  workflow. That was the design. What the repository actually contains is **2,849 PDFs,
  575 MB**, and the `Dockerfile` copies them into the image — roughly nine tenths of what a
  `docker pull` transfers, paid by every installation on every update, including the ones
  that never open a UN card.

  They are not dead weight: the UN card export serves exactly those files. But 575 MB per
  pull is a decision rather than a default, and nothing in the repository said so. Nothing
  is removed here; the number is now visible, with the two ways out named.

### Note on the method

While clearing out, a deletion without an end boundary truncated
`app/services/dg/amendment_42_24.py` and took `not_covered()` with it. 117 tests went red
and the cause was clear within a minute. Worth recording, because the risk in a clearing-out
is never what you meant to remove.

## [1.42.0] — 2026-08-09

### Added

- **The goods database grows from 400 to 1,093 entries**, each with a density, a min/max
  band, search aliases and a name in Dutch, English and German. What came in is what
  actually moves: 173 more agricultural commodities (grains and their by-products, oilseeds
  and meals, pulses, nuts, vegetables, fruit, spices), 68 more timbers including the
  tropical hardwoods a shipper meets on a packing list, 56 more steel and non-ferrous
  products in the form they travel in — coils, plate, rebar, billets, cathodes, turnings —
  76 more liquids and 43 more chemicals, 67 more construction materials, 39 more ores and
  minerals, and the rest spread over food, plastics, paper, textile, packaged general
  cargo, waste and insulation.

  Eighteen candidates were dropped during the merge because they turned out to repeat a
  good that was already there. That is worth saying out loud: a second entry for the same
  goods is worse than no entry, because the user picks one of the two and which one he
  picks decides his weight.

- **`test_materials_catalog.py` holds the invariants** that at 400 entries you could still
  check by eye and at 1,093 you cannot: no good appears twice, no alias belongs to two
  goods, all three languages are present on every good, every category is one `units.py`
  knows — an unknown one would silently fall back to the default density basis — and every
  density lies inside its own min/max band.

### Fixed

- **Searching for a good could return a different good entirely.** Before a query is
  matched it is normalised against a synonym table, and that table is not the small
  hand-written file it looks like: every alias of every good is added to it, so it holds
  some 4,400 keys. The replacement worked on character sequences rather than words. What
  that did, measured on the old 400-entry database:

  | typed | rewritten to | top hit |
  |---|---|---|
  | `broccoli` | `meel / bloem / bloemsteenkool (kisten)` | Flour |
  | `cashew` | `cessenew` | Ash *(the wood)* |
  | `Kupferkathoden` | `koperkathoden` | Copper |

  "cashew" contains "as", which is an alias of ash wood. The query was rewritten into
  something else and the good the user had literally typed did not even make the list. This
  predates the expansion — but more goods means more short aliases, so it was going to get
  worse, not better. A synonym now has to match a whole word, accents included: `\b` does
  not count ü or é as word characters, so "kupfer" inside "Kupferkathoden" needed its own
  boundary.

- **A good's own name now outranks another good's alias.** Cauliflower carried `broccoli`
  as an alias, so typing "broccoli" landed on cauliflower even though broccoli is itself in
  the database. Two things were wrong: the synonym table let a stray alias claim a name
  before its owner could, and the scoring left the two tied so the order of the rows
  decided. Names are registered before aliases now, and an exact match on a good's own name
  scores higher than a match on someone else's alias.

- **The stray `broccoli` alias is removed from cauliflower** in the seed. Note what that
  does and does not reach: the catalogue sync deliberately folds locally present aliases
  back in so that anything added by hand survives an update, which means a *deletion* never
  propagates. A fresh install is clean; an existing one keeps the alias but is no longer
  misled by it, thanks to the ranking fix above.

### Performance

- The first version of the word-boundary fix dropped the cheap substring pre-check and ran
  a regular expression over all 4,400 synonyms. That was correct and unusable: **1,446 ms
  per search**, against roughly 20 ms before. The pre-check is back in front of the regex.
  Measured end to end on the full 1,093-entry database: **median 63 ms per search, 115 ms
  at the slowest**, against 20–53 ms on the old 400-entry database. Search does get slower
  when the catalogue is 2.7× larger; it does not get slower per good.

### Documentation

- `docs/data-sources.md` now carries the count per category and states how a new good
  reaches an installation that is already running. The page implied it could not:
  `seed_catalogs` fills the table only when it is empty. That is true of `seed_catalogs`
  and false of the application — the startup catalogue sync reads the same seed file and
  upserts. Measured rather than assumed: seeding an old database, adding one good and
  restarting, `seed_catalogs` added nothing and the sync added it.

## [1.41.0] — 2026-08-08

### Added

- **Table 7.5.2.2 is read instead of pointed at.** When a consignment held class 1 packages
  of more than one compatibility group, CargoPilot counted the groups and handed the
  question back: *check the compatibility groups.* That is honest, and it is also the one
  question the user cannot answer — they do not have the book. The table is now in the
  configuration and gets read: an empty cell is a refusal, an X passes without a word, and
  the four footnotes come back as the condition they actually state.

  So detonators (group B) beside a blasting explosive (group D) no longer produce "check the
  table" but footnote (a): permitted, provided the two are effectively segregated by separate
  compartments or a special containment system, in a manner the competent authority has
  approved. Group N beside C, D or E returns both footnotes printed in that cell, because
  both apply. Two packages of group L return footnote (d): only with the same type of
  substance.

- **Rail gets its own table, and it is not the same table.** RID 7.5.2.2 was read on page
  1102 and compared cell by cell with ADR's on printed page 593. The tables are identical
  except for one thing: **RID has no compatibility group A.** Road runs A to S, rail B to S,
  and neither text lists group K. That is a difference in what the table answers rather than
  in an answer, so a rail leg is evaluated against the rail table, and a group A package on
  rail is told the table does not cover it — instead of quietly being handed ADR's row. The
  four footnotes are word for word the same in both texts.

  How the reading of the grid was checked: both tables are symmetric, and
  `test_compatibility_table_7522.py` asserts it. A table of crosses arrives from a PDF as a
  column of loose characters, and miscounting one column produces something that still looks
  plausible — but loading together is reciprocal, so a shifted column almost certainly breaks
  the symmetry somewhere.

- **RID 7.5.3, the protective distance.** The provision listed as the most concrete open item
  for three releases, read from page 1103 and implemented. A unit placarded 1, 1.5 or 1.6
  must be separated on the same train from one placarded 2.1, 3, 4.1, 4.2, 4.3, 5.1 or 5.2
  by 18 m, or by two 2-axle wagons or one wagon with four or more axles.

  Two things the text says precisely and that are easy to read past. **Model 1.4 is not among
  the triggers** — it has its own placard model — so a wagon carrying only division 1.4 goods
  falls outside. And **the counterpart list is short**: classes 6.1, 8 and 9 are not on it,
  however dangerous they are otherwise.

  This is the one provision where borrowing the ADR chapter would not have produced a rougher
  answer but no answer at all: 7.5.3 is about how a train is made up, and a road transport
  unit travels alone. Since CargoPilot cannot see the rest of the train, a consignment with a
  class 1 wagon and no counterpart of its own still gets the provision, addressed to the
  carrier, rather than silence.

### Fixed

- **1.4S counted for the compatibility table after all.** Footnote (a) to 7.5.2.1 takes 1.4S
  out of the comparison with *other classes*, and the code carried that exception into
  7.5.2.2 as well. But 7.5.2.2 is about explosives among themselves and has a row S, and that
  row is not all crosses: S against group L is empty, so prohibited. Carrying an exception
  from one provision into another had been silently approving that combination.

- **Rail cited a code the RID does not have.** RID column (18) names the foodstuffs provision
  **CW 28**; CargoPilot quoted ADR's CV28 on rail too. The text of 7.5.4 is identical in both
  regimes so nothing changes about the requirement, but a CIM quoting a code that does not
  exist in its own regime is the same category of defect as the tunnel code that used to be
  printed on it: information the application added itself.

### Documentation

- `docs/dg-coverage.md`: rail is no longer described as mostly road on loan. Its quantity
  calculation, mixed-loading table, compatibility groups and protective distance are now all
  cited to RID. Recorded in passing and deliberately not implemented: **RID 7.5.2.4**, which
  prohibits loading limited quantities together with any explosive except division 1.4 and
  UN 0161 and 0499. It needs nothing the application does not already compute, and it is
  named as the next rail item.

## [1.40.1] — 2026-08-08

### Fixed

- **Two explosives in one consignment produced a server error instead of an answer.**
  Detonators of compatibility group B next to a blasting explosive of group D — an
  everyday combination — made the compliance check raise `TypeError` rather than return a
  result. Both the panel in the wizard and the export run through `check_compliance`, so
  no document came out either.

  The fault was on the seam. v1.38.0 turned `class1_products` from a list of labels into a
  list of `(label, UN number)` pairs, because the footnotes of table 7.5.2.1 need the UN
  number. The 7.5.2.2 message a few lines below still called `", ".join(class1_products)`
  and has been handed tuples ever since.

- **And the reason nobody noticed is the second defect.** The compatibility group was read
  from the *class* field with a tight anchor, and ADR Table A puts only "1" in the class
  column for explosives — the division and its compatibility group live in the
  classification code. So on every row that comes straight out of the seed data, the check
  found no group, 7.5.2.2 never fired, and the broken line was never reached. A check that
  never ran looked exactly like a check with nothing to report. The group is now read the
  way the IMDG side has always read it: classification code first, then class.

  Two defects that covered for each other — the silent one masked the loud one. Measured
  on the real data before the fix: 344 of 4,000 random consignments of two to five UN
  numbers ended in an exception, 8.6%.

- **A class 1 package with a subsidiary risk beside another class 1 package took the sea
  check down.** In the IMDG 7.2.4 class table, class 1 against class 1 is `*`, which refers
  on to 7.2.7 rather than stating a distance itself. The search for the strictest cell
  compared `int(value) > int(worst)` as soon as anything had been found, so a `*` followed
  by a number was `int("*")`. A number now always beats a `*`, which is what the code
  intended all along.

### Added

- **A sweep that no single provision owns.** Both defects above were found by running the
  compliance check over consignments assembled from the seed data along the same path the
  wizard takes, not by reading code — and they were only findable that way, because a bare
  seed row carries "1" in the class column and it is `derive_product` that fills in the
  division. `test_class1_compatibility_groups.py` keeps a seeded version of that sweep:
  300 consignments per rule set, asserting nothing about any particular rule, only that no
  consignment can make the check fall over.

## [1.40.0] — 2026-08-08

### Changed

- **A release no longer builds anything.** The tag used to recompile the identical commit
  from scratch — four to six minutes for bits that already existed — and run both test
  suites over them a second time. The image `main` built, tested and pushed under its short
  SHA was sitting there the whole time.

  A tag is a name, not a build. `tag-release.yml` now puts the version on that existing
  manifest with `docker buildx imagetools create`: server-side, both architectures, in
  seconds. It is also stricter than a rebuild — what gets released is bit for bit what went
  green through CI, instead of a second compilation that could differ from the first.

  Nothing changes about what is published or when. `latest` still follows `main`, every
  merge still produces a testable image, and `:<version>` still appears on Docker Hub with
  both architectures. Only the second compilation is gone.

  If `main`'s build has not finished, the release waits for the SHA tag to appear and gives
  up after twenty minutes rather than putting a version number on an older image.

- **`ci.yml` no longer triggers on `v*` tags.** With the retagging above there is exactly
  one way a version image comes into existence. Two routes to one outcome is how they drift
  apart.

## [1.39.0] — 2026-08-08

### Changed

- **The same work was being done twice on every push.** `ci.yml` and `dockerhub.yml` were
  both named `CI` and both triggered by pushes to `main` and by every pull request, so
  `pytest` ran twice and `npm ci` ran twice per commit — five checks, two of them a copy of
  two others. A release with three commits on the branch spent fifteen jobs before anything
  was merged. They are now one workflow with three jobs: Backend tests, Frontend build,
  Docker build. The more thorough of the two frontend jobs was kept, so the audit and the
  Vitest run survive.

- **arm64 is built only when an image is actually published.** It is emulated through QEMU
  on an amd64 runner, and that emulation was most of the wall clock. A pull request pushes
  nothing, so its Docker build is a smoke test of the Dockerfile and `linux/amd64` answers
  that. Pushes to `main` and tags still build both architectures. A pull request also no
  longer writes buildx cache — an amd64-only layer overwriting `main`'s scope made the next
  publishing build slower, not faster.

- **Superseded pull request runs are cancelled.** Pushing three times in a row no longer
  leaves two runs burning for a result nobody will read. Runs on `main` and on tags are
  never cancelled; a publication hangs off those.

- **Reading a regulation is something you ask for.** `read-land-regulations.yml` ran on
  every push that touched it, fetching four PDFs of some 40 MB and quoting all six groups,
  on a branch where nobody was reading the log. It is `workflow_dispatch` only now.

### Removed

- **`dockerhub.yml`**, whose remaining job moved into `ci.yml`, and **`release.yml`**, a
  second and unused path to creating the same GitHub Release — `tag-release.yml` has done
  the tag, the release and the image since it was written. Two mechanisms for one outcome
  is how they drift apart.

  The five remaining workflows (`cleanup-dockerhub`, the two `probe-*`, the two
  `extract-imdg-*`) all wait to be asked and cost nothing until then. The number of files in
  `.github/workflows/` was never the cost; the number of jobs per push was.

## [1.38.0] — 2026-08-08

### Fixed

- **Blasting explosives with ammonium nitrate were refused, though footnote (d) permits
  them.** The message CargoPilot showed even named the exception — and then blocked the
  load anyway. The check asked whether the consignment contained any class 1 package and
  any package of another class, and raised one error over the whole consignment. Table
  7.5.2.1 does not work that way: it sets label against label, and three of its cells hold
  a footnote letter instead of a prohibition.

  Footnotes (b), (c) and (d) are now applied, per pair of packages. One forbidden
  combination no longer condemns a permitted one, and one permitted combination no longer
  excuses the rest — load a blasting explosive with both ammonium nitrate and paint and you
  get the permission for the first and the prohibition for the second, each naming only the
  packages it concerns.

  Footnote (d) carries a condition that changes the rest of the load, so the panel and the
  document both state it: the aggregate must be treated as blasting explosives of class 1
  for placarding, segregation, stowage and the maximum permissible load of 7.5.5.2.1. UN
  0083 is excluded by the footnote itself and stays refused.

### Added

- **The regulation reader can print a page verbatim** (`--page 602`, or a range of at most
  twelve). ADR 7.5.2.1 came back "not found" for weeks: the finder scores each occurrence of
  a clause number by how much prose follows it, which is right for a rule made of sentences
  and wrong for one that is almost entirely a grid of crosses. It scored near zero and lost
  to every cross-reference in the volume. When the number will not resolve, the page still
  will.

- **The reader searches through a hyphen.** RID breaks words at the line end —
  `com-\npatibility`, `alka-\nline` — so a phrase search against it found nothing at all.
  "No occurrence" then reads as an answer about the regulation when it is only an answer
  about the typesetting, which for a tool whose job is checking what a text says is the
  worst way to be wrong.

### Fixed (the reader)

- **A table is no longer mistaken for a contents page.** One of the three contents signals
  counted bare clause numbers, and a table like 7.5.2.1 *is* a column of bare numbers —
  "1.4", "5.1", "6.2". So the finder skipped exactly the pages the locator could not reach
  either: both escape hatches failed on the same kind of page, which is how RID's 7.5.2.1
  came back as "no occurrence" for a footnote plainly printed on page 1101. A page carrying
  real sentences is now never a contents page, however many numbers stand in its margin.

### Verified

- **Rail was checked before these permissions were extended to it.** CargoPilot answers RID
  and ADN mixed loading with ADR's table under a stated basis note. Borrowing another
  regime's prohibitions is conservative; borrowing its permissions is not, and this release
  turns three cells from refusals into permissions. RID 2025, table 7.5.2.1 on page 1101,
  carries footnotes (a) to (d) in the same words and with the same UN numbers — so for rail
  this is RID's own rule, not a road rule on loan. ADN is a different regime for stowage and
  its borrowing stays labelled as such.

### Documentation

- The footnote text and its source — ADR 2025 Volume II (ECE/TRANS/352 Vol. II), table
  7.5.2.1, printed page 592 — are recorded in the configuration and in `docs/dangerous-goods.md`,
  because these UN numbers come from a text that is not in the repository.

- Corrected in passing: the footnote (d) that extracts most readily from ADR belongs to
  **7.5.2.2** and concerns compatibility group L. The ammonium nitrate footnote is (d) to
  **7.5.2.1**. Two different tables, two different (d)s.

## [1.37.1] — 2026-08-08

### Fixed

- **A round bar was weighed as a square block, 27% too heavy.** There was no calculation
  path for `round_bar` at all, so a bar fell through to the generic branch and became a
  block of d × d. A 50 mm bar over 6 m came out at 117.75 kg instead of 92.48 — the ratio is
  exactly 4/π. `calc_round_bar` had been sitting unused in the engine the whole time, next to
  `calc_round_tube`; neither had a caller.

- **A round tube produced no weight at all.** v1.37.0 gave it the wall thickness field but no
  branch to use it, so it reported `wall_thickness_missing` however much you filled in. A
  pipe of 108 mm outside diameter with a 4 mm wall over 6 m is now 61.56 kg, against the
  10.26 kg/m in the steel tables.

### Changed

- **A round section is described by a diameter, a length and a wall — no height.** The width
  column *is* the diameter and the inner diameter follows from the wall thickness, so the
  height field shows a dash and is labelled accordingly. Asking for a measurement that adds
  nothing is only an opportunity to enter something wrong.

- **A wall thicker than the radius is refused** rather than producing a negative
  cross-section, because a negative weight looks exactly as confident as a positive one.

## [1.37.0] — 2026-08-08

### Fixed

- **A steel angle profile was weighed as a solid bar, five times too heavy.** Ten angle
  profiles of 6 m, 80 × 80, came back at 301.44 kg each. An L 80×80×8 is 9.63 kg per metre,
  so about 57 kg for six metres. The cross-section *was* recognised — the detector returns
  `angle_profile` — but the calculation path for it demanded four measurements out of the
  *description*. Enter three in the columns and the line fell through to the generic branch
  and became a solid block of 600 × 8 × 8 cm.

  Reported from use, and the worst kind of defect this application can have: a confident
  wrong number on a transport document, with nothing on screen suggesting a measurement was
  missing.

### Added

- **Wall thickness, the fourth measurement.** For an angle profile, a square tube or a round
  tube the line carries a wall thickness in millimetres, and the engine's existing
  cross-section formulas finally receive it. L 80×80×8 over 6 m is now 57.27 kg against the
  9.63 kg/m in the steel tables.

  **The field only appears where it means something.** A plate, a beam, a plank or a block is
  fully described by three measurements, so no fourth field is shown — as you pointed out
  about wooden planks.

  **And it is required where it applies.** A shape with a wall and no thickness produces no
  weight at all: the line reports `wall_thickness_missing` and asks. Falling through to a
  solid block is exactly what caused this, and no number is better than that number. The
  transport volume is still given, because that depends only on the outer measurements.

### Changed

- **The recalculate button is gone; the calculation follows the input.** A button you have to
  press to see a correct figure is a button that gets forgotten, leaving a stale weight on
  screen. Changing a quantity, unit, form or dimension now recalculates shortly after typing
  stops. Manual weight corrections deliberately do not trigger it — those are an answer to a
  calculation, and would otherwise restart it.

## [1.36.1] — 2026-08-08

### Fixed

- **Releasing no longer moves `main` out from under the next branch.** The version lives in
  five places, and `frontend/package-lock.json` — which holds it twice — was not being
  checked. So it drifted at every release, and the **Tag release** workflow repaired it by
  committing to `main` after the merge. The repair worked. It also meant every branch created
  before that commit conflicted on `VERSION` and `CHANGELOG.md` and could not be merged until
  it was rebased; that happened twice in one day, over four lines of JSON.

  The check now covers all five values and runs on every pull request, so the mistake fails
  where it is made. The release workflow verifies and stops rather than repairing, and writes
  nothing to `main`.

### Added

- **`scripts/bump_version.py`** sets all five at once, because nobody edits a lock file by
  hand and forgetting it was the whole problem. It leaves the rest of the lock file
  byte-identical, so a version bump stays readable in a diff.

### Removed

- `scripts/finalize_release_metadata.py`. Half of it was dead — the changelog archive it
  merged was consumed long ago and cannot recur — and the other half is now a check instead
  of a write.

## [1.36.0] — 2026-08-08

### Changed

- **The form a good travels in is now a choice on the line, not an average in the code.**
  v1.35.0 weighed all timber at a stacking factor of 0.65. That is a reasonable figure for
  neatly stacked sawn timber and a poor one for everything else: loose-tipped firewood is
  nearer 0.45 and a tight package nearer 0.75. One average describes nobody's load.

  Each line now carries a **form** — solid, sheets, bundled, stacked or loose bulk — and the
  form carries the factor. So 20 m³ of oak is 14,400 kg solid, 10,800 bundled, 9,360 stacked
  or 6,480 loose, and the shipper says which. The same choice applies wherever it matters:
  steel plate against steel scrap, plastic granulate against regrind, baled paper against
  loose.

  The default still fits the goods — sawn timber starts stacked, sheet material flat, metal
  solid — so nothing needs choosing to get a sensible answer.

- **The form does not apply where the density already describes the shipped state.** For
  gravel, grain and ore the stored figure *is* a bulk density; laying a loose factor over it
  would subtract the air twice. Same for liquids and for the per-pallet averages. Those
  lines show a dash instead of a dropdown, and the API returns an empty list of forms for
  them.

- **The result says what it used.** The compliance of a number matters as much as the
  number: a line reports the form it was weighed in and the density that produced it, so
  9,360 kg can be traced to 468 kg/m³ rather than 720.

## [1.35.0] — 2026-08-08

### Added

- **Timber is weighed as it travels: stacked, not solid.** Oak's 720 kg/m³ is the density
  of the wood, and between the boards of a stack there is air. Entering 20 m³ of oak
  returned 14,400 kg — the weight of 20 m³ of solid oak, which almost nobody carries. A
  volume entered for timber now uses a **stacking factor of 0.65**, so the same 20 m³ is
  9,360 kg at 468 kg/m³. Sheet material — plywood, OSB, MDF, HDF, chipboard, hardboard,
  softboard, cork, CLT and glulam — stacks flat and keeps its own density.

  Two things this deliberately does not do. It does not touch a line with explicit
  dimensions: a beam of 0.2 × 0.2 × 3 m is 0.12 m³ of actual wood and is weighed solid.
  And it does not present the factor as a measurement — it is a nominal packing figure,
  stated as such, and entering the weight by hand overrides it.

- **Length, width and height are fields on the line.** A description no longer has to read
  `balk 200x200x3000` for its measurements to count. Anything recognised in the text still
  appears as a placeholder; what you type wins. On a phone the three sit behind "view more",
  with quantity and unit on the collapsed card.

### Fixed

- **Dimensions typed into the table were ignored by the calculation.** They were carried
  into the displayed length, width and height, but every calculation path went on reading
  what had been parsed out of the *description*. So the columns looked editable and changed
  nothing. They now feed the calculation, and a length on its own is enough for a catalogue
  profile. Two of the three measurements is still not a block: nothing is computed rather
  than a third being invented.

### Changed

- `docs/data-sources.md` records the stacking factor and why it lives in `units.py` rather
  than in the goods database: `seed_catalogs` only fills that database when it is empty, so
  new seed values never reach an existing installation, and a calculation that is only right
  for new users is worse than none.

## [1.34.1] — 2026-08-08

### Fixed

- **"1500 litres of petrol" is enough to compute with, and was rejected anyway.** The line
  reported `dimensions_missing` and left weight and volume empty, while everything needed
  to work it out was on the screen: the unit gives the volume, the density of petrol
  (745 kg/m³) gives the mass. 1500 L is now 1,117.5 kg and 1.5 m³.

  The cause is the kind worth recording. v1.34.0 delivered a units module, a dropdown that
  used it and an API to compute with it — but the pipeline that determines the weight never
  asked for any of it and went on demanding dimensions. Half connected is not connected.

  The conversion only steps in when there are no dimensions and no profile, and only for a
  **recognised** goods item: `match_material` falls back on the density of steel, and 1500
  litres times 7850 would look every bit as confident as the answer that is right. So an
  unknown substance stays reported as unknown, and fifteen pallets without a weight per
  pallet stay unknown — a count carries no physics in it.

## [1.34.0] — 2026-08-08

The goods step becomes a table on desktop and cards on a phone, and a quantity finally
carries a unit.

### Added

- **A unit instead of a word.** The unit of a goods line was a free text field with
  "stuks" as its default, so entering 1,200 litres of diesel gave you 1,200 *pieces* of
  diesel and left the weight to you. It is now a dropdown, and every unit knows what it
  measures — mass, volume, length or a count. Density bridges mass and volume, so 1,200 L
  of diesel is 1,002 kg, and 20 tonnes of gravel is 12.5 m³.

- **The list suggests, it does not fence you in.** The category of the recognised goods
  decides what appears first: litres and m³ for liquids, tonnes and m³ for bulk, pieces and
  pallets for general cargo, m³ for timber. Every other unit stays one click away, because
  400 goods in 16 categories always hold exceptions and being stuck on one is worse than an
  unusual unit. What people actually type — `liter`, `cbm`, `kubieke meter`, `MT`, `Stück`,
  `big bag` — still resolves, so shipments saved under the old free-text field keep working.

- **Where it cannot calculate, it says so.** Forty pallets without a weight per pallet weigh
  an unknown number of kilos. The conversion reports that rather than returning zero: a
  total that looks right and means nothing is the same failure as a check that never ran
  looking like a check that passed.

- **`ResponsiveRecords`** — one set of data in two shapes. A real table on desktop, where
  rows can be compared; the card pattern on a phone, where they cannot. Built from
  *Designing User-Friendly Data Tables for Mobile Devices* (Zahra Mohammadi, Bootcamp,
  July 2025): each row becomes a card with the identifying field in a tinted header and the
  actions as icons beside it, the body a list of label–value pairs, and only the priority
  fields shown until "view more" opens the rest. The unit sits small behind its value —
  `1 200 L` — instead of claiming a column of its own.

### Changed

- **The goods step uses it.** On a phone each line is a card headed by its description, with
  quantity and unit as the one visible field and weight, volume, the dangerous goods flag
  and the status behind "view more". On desktop the same lines are a table with a column per
  field. Nothing is dropped on the small screen; it is only folded away.

### Fixed

- **`docs/data-sources.md` claimed something the data does not say.** It stated that each
  goods entry records whether its density is bulk, solid, liquid or an effective pallet
  figure. There is no such field — only the category. The distinction is real (20 m³ of
  gravel, of steel and of stacked timber are three different masses), so the basis is now
  derived from the category and reported as derived, and the page says so.

## [1.33.0] — 2026-08-07

The land regulations are read instead of recalled, and reading them found two things the
application had wrong.

Every rule about road, rail and inland waterway in CargoPilot came from an ADR Table A data
export plus general knowledge of how the three regimes are structured. The documentation
said the regulatory texts were out of reach and marked every such rule as unverified. That
premise was false: **ADR and ADN are published free of charge by UNECE and RID by OTIF.**
Only the IMDG Code and the IATA DGR are sold. What was missing was a network route from the
development container, not the documents.

### Added

- **`scripts/read_land_regulations.py` and a workflow to run it.** It fetches ADR 2025
  (both volumes), RID 2025 and ADN 2025 from their publishers on a CI runner and prints the
  provisions the application implements, addressed by the number they carry in the text. It
  commits nothing — the quoted text stays in the run log, and only the values read out of it
  are stored, each with its provision.

- **ADN gets its own exemption rule, because it has one.** ADN 1.1.3.6.1 has no points
  calculation at all: it exempts a consignment in packages when the gross mass of everything
  together stays under 3,000 kg *and* no class exceeds its own figure — 0, 300 or 3,000 kg
  depending on packing group, class 2 group, or whether a model No. 1 label is required.
  Carriage in tanks is never exempt. Until now an inland waterway shipment was shown the ADR
  points table, which is not an approximation of that answer but an answer to a different
  question, and the two can point opposite ways: 1,200 litres of a packing group III liquid
  loses the ADR exemption at 1,200 points and keeps the ADN one. The panel now carries an
  ADN card with its own status, the per-class figures and the conditions of 1.1.3.6.2 that
  survive the exemption.

### Fixed

- **Nine substances were counted at more than twice their proper weight.** Note (a) to the
  table in ADR/RID 1.1.3.6.3 allows UN 0081, 0082, 0084, 0241, 0331, 0332, 0482, 1005 and
  1017 up to 50 kg rather than the 20 kg of transport category 1, and RID 1.1.3.6.4 gives
  the matching multiplier: times 20, not times 50. CargoPilot applied times 50 to all of
  category 1, so 50 kg of chlorine or anhydrous ammonia scored 2,500 points and lost an
  exemption the text grants at exactly 1,000 — the application demanded orange plates, a
  driver certificate, written instructions and an ADR vehicle for loads entitled to go
  without them.

- **The IATA Q status reaches the document, not just the screen.** Whether the Q check of
  5.0.2.11 actually ran was derived in the API route, so the compliance panel said "no Q
  check was performed" and the export said nothing — at the one moment the document leaves.
  `exporter.py` states in its own comment that the screen must never be the only place this
  is enforced. The status is now part of the compliance outcome, so every caller sees it.

- **A position that was never checked no longer counts as checked.** A position holding two
  or more substances with no `n` and no `M` was skipped silently, so as soon as one other
  position was filled in the whole shipment reported "checked". It is now reported as not
  checked, and one unchecked position makes the shipment unchecked.

### Changed

- **Rail stops hedging about its own chapter.** RID 1.1.3.6.3 prescribes the same five
  transport categories with the same maxima (0, 20, 333, 1000, unlimited) and 1.1.3.6.4 the
  same multipliers (50, 3, 1) against the same calculated value of 1,000. The arithmetic was
  right all along. The old note said RID "has its own 1.1.3.6 which CargoPilot does not
  hold" — true, but it invited the user to distrust a number that is the number RID
  prescribes. The panel now cites 1.1.3.6.3/1.1.3.6.4 and names the one real difference:
  RID counts per wagon or large container, ADR per transport unit.

- **The 3.4/3.5 limits are confirmed against the published text.** ADR 3.4.2's 30 kg,
  3.4.3's 20 kg for shrink- and stretch-wrapped trays, 3.5.5's 1,000 packages and the whole
  of table 3.5.1.2 (E1 30/1000, E2 30/500, E3 30/300, E4 1/500, E5 1/300) are as shipped in
  v1.31.0. That release claimed they had been verified without leaving a record of it; there
  is now a record, and the values were correct.

- **`docs/dg-coverage.md`** separates what has been read from what has not. Road, rail and
  inland waterway carry provision numbers; sea and air keep their `[verify]` markers,
  because the IMDG Code and the DGR genuinely cannot be read here. The gap ranking loses
  two entries and gains an ordered list of what to build next, starting with RID and ADN
  mixed loading — which no longer needs anything CargoPilot cannot get.

- The pinned example image and Docker Hub cleanup tags in the installation and privacy
  guides, and the sample health response, moved off v1.29.3.

## [1.32.0] — 2026-08-05

Nine dangerous-goods specialist findings from the v1.31.0 review are closed: air
prohibition, Q noise, multi-PG silence, class 1 mass, the 8-tonne LQ mark, the class 8
pair exception, forbidden substances in the points table, modality-filtered hints, and
the inner-packaging field when LQ/EQ have no route.

### Added

- **Division 2.3 (toxic gases) is refused for air transport.** Enrichment reads the
  division from the labels column when Table A only states class "2", so chlorine
  (UN 1017) and similar gases raise an ICAO TI / IATA DGR error on the air stack instead
  of staying silent.
- **Net explosive mass for class 1.** A dedicated field feeds ADR 1.1.3.6.3 points and the
  NEM figure on land transport documents (5.4.1.2.1). Without it the points table reports
  incomplete rather than counting product mass as explosive mass.
- **ADR 3.4.13/3.4.14 when LQ packages exceed 8 tonnes gross** on a transport unit: the
  large LQ mark of 3.4.15 is required and the 3.4.14 waiver no longer applies.
- **IMDG 7.2.6.5 next to the acid×alkali pair** that triggered a segregation finding, as
  an info note that leaves the warning in place.

### Fixed

- **The IATA Q check no longer starts on auto-filled n alone.** Participation requires an
  entered M (maximum per packing instruction), so every air shipment is not marked
  incomplete when all-packed-in-one does not apply.
- **Multi-row UN numbers respect the user's packing group** and warn when several groups
  exist without a choice, instead of silently taking the first Table A row.
- **Carriage-prohibited substances are excluded** from the 1.1.3.6 points table and from
  document lines; the panel names them separately.
- **Modality hints follow the active profiles:** EmS/IMDG noise stays off a pure road
  prepare, and the air prohibition hint appears only when IATA is selected.
- **The net-per-inner field is hidden when LQ is 0 and EQ is E0**, so the step is not
  permanently "incomplete" for substances with no limited/excepted route.

### Changed

- The dangerous-goods coverage assessment records the specialist fixes as shipped in
  v1.32.0.

## [1.31.0] — 2026-08-05

The limited and excepted quantity limits are applied instead of only explained, and the
dangerous goods step becomes readable again.

### Added

- **The LQ and EQ limits of chapters 3.4 and 3.5 are checked against the entered
  quantities.** A new "net per inner packaging" field feeds a per-line assessment for the
  ADR, RID, ADN and IMDG profiles: the column 7a limit and the E-code limits of table
  3.5.1.2, the 30 kg gross limit of 3.4.2 (naming the 20 kg tray limit of 3.4.3) and the
  1,000-package cap of 3.5.5. The limit values were verified against the published
  3.4/3.5 text before the check was written. Qualifying is reported, never granted: the
  LQ/EQ mark and the packaging and testing requirements remain conditions, and a
  qualifying line is never removed from the 1.1.3.6 points calculation. Mass is never
  compared against a volume limit, and a number without a unit is asked about rather
  than guessed at. On IMDG the values come from the 42-24 Dangerous Goods List, with
  differences from the ADR value flagged; on RID and ADN the same basis note appears as
  for the points table; for air no claim is made.

### Fixed

- **Live compliance checks from the wizard work again.** The wizard sends its line
  identifier as a number; the schemas introduced in v1.30.0 rejected that with HTTP 422,
  so every live check from the wizard failed before anything was computed and the panel
  showed a validation error instead of an outcome.

### Changed

- **The dangerous goods step folds its findings into collapsible summary cards.** The
  headers carry the outcome — status chips, severity counts, totals — and the
  substantiation unfolds on demand. Nothing is silenced by the fold: a carriage
  prohibition stays outside the cards, a section holding an error opens by itself, and
  every collapsed header shows the counts of what is inside.

## [1.30.1] — 2026-08-05

A release-metadata and documentation cleanup following v1.30.0.

### Fixed

- Synchronise the frontend lockfile version with the canonical application version before a release tag is created.
- Restore the changelog to one continuous file; the temporary archive through v1.29.5 is merged back before tagging.
- Update the dangerous-goods coverage assessment: a missing IATA Q calculation is no longer silent since v1.30.0, although n and M still require manual input because CargoPilot does not contain IATA quantity tables.

### Changed

- Release preparation now normalises derived metadata before tagging, preventing the application version and npm lockfile from drifting apart again.
- LQ/EQ application is documented as the next data-supported dangerous-goods priority.

## [1.30.0] — 2026-08-05

The compliance boundary, authentication boundary and build boundary are now explicit instead of relying on the browser or deployment convention to do the right thing.

### Fixed

- **The IATA compliance contract now uses one canonical profile name.** `IATA_DGR` is accepted end to end by the wizard, API and calculation engine. The previous `IATA` value remains a temporary compatibility alias, while unknown profiles still fail with HTTP 422.
- **An absent IATA Q calculation no longer looks like approval.** Compliance results say whether Q was checked, incomplete, exceeded or not checked, and the panel warns when all-packed-in-one may apply but n/M data is absent.
- **Changing a password now ends every existing session for that user.** Tokens carry a one-way fingerprint of the current password hash; after a password change old cookies no longer authenticate and the current cookie is cleared.
- **Interrupted export cleanup covers the formats CargoPilot actually creates.** PDF, ZIP, XLSX and temporary files are removed case-insensitively at startup; one undeletable file no longer stops the rest, and unrelated files and directories are untouched.

### Added

- **Strict authentication and administrator safety rules.** Login cookies automatically use `Secure` for HTTPS or trusted `X-Forwarded-Proto=https`, with `COOKIE_SECURE` as an explicit override. Roles are limited to `admin` and `user`; an administrator cannot remove their own administrator access or remove the last active administrator.
- **Bounded spreadsheet and remap imports.** Raw uploads are limited to 10 MB, imports to 20,000 rows, 100 columns and 10,000 characters per cell, and XLSX archives to 50 MB after decompression. The limits apply to wizard and equipment imports and nested remap JSON.
- **Executable API contract coverage for dangerous goods.** FastAPI integration tests cover air and multimodal wizard profiles, the legacy IATA alias, unknown profiles and Q-status behaviour.

### Changed

- **Production dependencies are now audited and reproducible.** Docker uses Node 22 and `npm ci`; Python runtime packages are separated from pytest-only dependencies; `pip check`, version consistency and a blocking `npm audit --omit=dev --audit-level=high` run in CI.
- **The frontend moved to React 19.2.8 and React Router 8.3.0.** This removes the vulnerable Router 7 dependency chain while retaining the existing wizard behaviour and frontend test suite.
- **Pull-request Docker builds prove both AMD64 and ARM64 images without publishing them.** Release and main builds retain the publishing path.

### Tests

- The combined release was validated with backend tests, frontend tests, TypeScript and Vite build, production dependency audit, Python dependency validation, version consistency and a multi-architecture Docker build.

## [1.29.5] — 2026-08-04

Road, rail and inland waterway were being treated as one regime. They are three.

### Fixed

- **The tunnel restriction code no longer appears on rail and inland waterway
  documents.** It comes from column 15 of ADR Table A and belongs on the road document
  under 5.4.1.1.1 (k). RID Table A has no such column and the ADN transport document does
  not carry one — yet CargoPilot printed `(D/E)` on a CIM consignment note and on an ADN
  document. That is not a missing check but wrong information the application added by
  itself. The code is now written only when the ADR profile is selected. The CMR is
  unaffected.

### Changed

- **A calculation now says which tables it was made with.** The 1.1.3.6 points and the
  mixed loading of 7.5.2 are computed from the ADR tables. RID and ADN have their own
  versions of those chapters and they are not in CargoPilot. Selecting RID or ADN gave an
  outcome that silently read as *the RID outcome*. The compliance panel now carries a
  note naming the basis, in all three interface languages. The numbers themselves are
  unchanged — a road shipment sees no note, and 1200 points stay 1200 points.

### Added

- **`docs/dg-coverage.md`** — an assessment, per mode, of what CargoPilot actually checks
  against what the regime requires, with the gaps ranked by how much damage the gap can
  do. It separates what was read out of the code from what comes from knowledge of the
  regimes, and marks the latter as unverified: the regulatory texts are not in this
  repository and could not be consulted while writing it. Nothing in it is a citation, and
  nothing in it should become a check before it has been verified against the published
  text.

## [1.29.4] — 2026-08-04

Documentation only. Nothing in the application changed.

### Changed

- **The docs caught up with the last few releases.** The interface badge and the goods
  database still said Dutch and English; the paste box was described as reading Dutch or
  English; the Unraid instructions still told you to fill in `APP_SECRET_KEY`, which is
  now generated; the pinned example image and the Docker Hub cleanup tags still pointed at
  v1.13.2; and the `/api/health` sample predated the `regulatory` block.

- **Getting started now answers the question that actually came in.** "The container
  starts and immediately stops, and the log window closes before I can read it" is a
  troubleshooting entry, naming the affected versions (v1.25.0 – v1.29.2), the fix, and
  what to set if you cannot update yet.

- **The v1.25.0 changelog entry is marked as reverted** rather than left standing as
  advice, and its dead link into `configuration.md` is repaired. The original wording is
  kept, quoted, because a changelog is a record and not a place to quietly rewrite what
  was said at the time.

- **The user guide describes the language choice**, including the one thing that does not
  follow it: the proper shipping name is prescribed per mode, so a sea or air document
  stays English whatever the screen says.

### Fixed

- **A claim in the development notes was wrong, and testing it is what showed that.**
  Both `docs/development.md` and `AGENTS.md` were about to say that `APP_ENV=development`
  preserves `APP_SECRET_KEY=dev-secret`. It does not: a published key is replaced in every
  environment, and `APP_ENV` only silences the CORS and admin-password warnings. The
  generated key is stored and reused, so a developer is logged out once rather than at
  every start. Both files now say that.

- `ROADMAP.md` still listed German as a third interface language and the import column
  mapping as planned; both shipped in v1.29.0 and v1.28.0.

## [1.29.3] — 2026-08-04

**If you are on v1.25.0 or later and the container will not start, this is the release
that fixes it.** No configuration change is needed on your side.

### Fixed

- **CargoPilot refused to start on its own default settings.** Since v1.25.0 the
  application stopped at startup when `APP_SECRET_KEY` was published, empty or shorter
  than 32 characters, or when `CORS_ALLOWED_ORIGINS` was `*`. Those are the values it
  ships with — `app_secret_key: str = "change-me"` and `cors_allowed_origins: str = "*"`
  in `config.py` — and the Unraid template passes `APP_SECRET_KEY` through with an empty
  value. So every installation that had not set both by hand died on startup, in a
  container that exited too quickly to read the message explaining why.

  The reasoning behind the refusal was right: the default signing key is published in
  this repository, and anyone who has it can write themselves a valid admin token, so a
  line in a log nobody reads is not an answer. The conclusion was wrong. A self-hosted
  application with its own data directory does not need to ask the user for a signing
  key — it can make one.

  It does now. On first start CargoPilot generates a key, stores it as `secret_key` in
  `DATA_DIR` with owner-only permissions, and uses it from then on. It survives restarts
  and container recreation because it lives on the mounted volume. A key you set yourself
  still wins, as long as it is not a published value and is long enough. The result is
  strictly safer than what shipped before — random instead of published — and costs the
  user nothing.

  `CORS_ALLOWED_ORIGINS=*` and a documented `ADMIN_PASSWORD` are now reported in the log
  rather than fatal. Neither is worth a dead application, and the CORS case is largely
  theoretical anyway: browsers refuse to combine a wildcard origin with cookies, so the
  cross-site call it warns about does not work regardless.

### Tests

- `test_starts_out_of_the_box.py` builds the application in a real subprocess with a
  clean environment, no `.env`, and nothing configured that a user would not also have —
  including the exact shape the Unraid template produces. It fails on eight of its nine
  cases against v1.29.2 and passes on all nine here.

  This is the test that was missing. The 500 tests that existed all ran with
  `APP_ENV=test`, which is precisely the setting that skips the check, and not one of them
  built the app the way a user starts it. A suite can be large and still miss the only
  thing that matters.

### Changed

- The Unraid template no longer marks `APP_SECRET_KEY` as required, and says the key is
  generated if left blank. `.env.example` and `docs/configuration.md` say the same, and
  the documentation records what the old behaviour was and why it was wrong.

## [1.29.2] — 2026-08-04

Following the rules and being pleasant to use are the same job, not a trade-off.

### Changed

- **A sea or air document now gets the English shipping name instead of refusing to
  export.** 1.29.1 got the regulation right and the experience wrong. If you drafted a
  German road document and then added a sea leg, the German name stayed in the field and
  the export **blocked**, telling you to retype `GASOLINE` — a word CargoPilot had just
  printed in the error message. That is making the user do what the application already
  knows.

  The language of the proper shipping name belongs to the **document**, not to the
  shipment. One shipment produces a CMR reading `BENZIN ODER OTTOKRAFTSTOFF` and an IMO
  Multimodal Dangerous Goods Form reading `GASOLINE`, from the same data. So the name is
  now resolved per document at the moment it goes on paper — in the goods column, in the
  5.4.1.1.1 description line, in the DG table and in the filled IATA PDF — and the export
  says what it did rather than what you still have to do.

  Only what CargoPilot derived itself is adjusted. Wording you typed — a technical name
  on an N.O.S. entry, your own addition — is left exactly as it stands: we cannot judge
  it and must not silently overwrite it.

- **Why a multimodal shipment stays English throughout, including on the CMR**, where
  German would have been allowed: one shipment then carries the same goods description on
  every piece of paper. A forwarder and a customs officer want those to match, and two
  languages for one substance across two documents of the same consignment is a question
  you do not want to be asked. The reasoning is written down in
  `app/services/dg/naming.py` so it reads as a decision rather than an accident.

### Tests

- The export is checked by reading the generated workbook back: the IMO form contains
  `GASOLINE` and does **not** contain `BENZIN ODER OTTOKRAFTSTOFF`, and the CMR from the
  same shipment contains the German name. A warning that says the right thing while the
  document says the wrong thing would otherwise pass unnoticed.

## [1.29.1] — 2026-08-04

The two gaps left open by 1.29.0, closed. One of them was not the gap it was described as.

### Fixed

- **The proper shipping name was always English, even where German was prescribed.**
  1.29.0 claimed the ADR source table "carries Dutch and English but no German". That was
  wrong twice over: the table carries `name_en` **and** `name_de` for all 2,928 entries,
  and it carries no Dutch at all. The German name was sitting in the data the whole time
  and every code path reached past it with `entry.get("name_en") or entry.get("name_de")`.
  A German consignor got `GASOLINE` on a CMR while `BENZIN ODER OTTOKRAFTSTOFF` stood
  right next to it in Table A.

  Fixing it is not "translate along with the screen", because the modes differ. ADR
  5.4.1.4.1 — and along the same line RID and ADN — wants the transport document in an
  official language of the forwarding country, so a German name belongs on a German CMR
  or CIM. IMDG 5.4.1.4.1 wants English, French or Spanish. IATA DGR 8.1.2.1 wants English.
  `BENZIN` on a Shipper's Declaration is not a matter of taste; it is a refused shipment.

  So `app/services/dg/naming.py` gives the German name only when the reader is German and
  no sea or air profile is in play — for a multimodal shipment English satisfies all three
  regimes and German only one. The UN lookup and the type-ahead now carry the same
  language and profiles, so the suggestion the user clicks is the text the document will
  actually carry.

  And for the sequence that would otherwise slip through — draft a German road document
  first, add a sea leg afterwards, keep the German name that is already in the field — the
  export refuses it and names the English wording that belongs there instead.

- **The catalogue search always answered in Dutch.** `search_catalog` took no language
  parameter at all, so an English user got Dutch material names too; German only made an
  existing problem visible. It now takes one, and the route and the frontend pass it.
  Searching still spans every language — type `Stahl` while reading Dutch and you still
  find staal — only the answer follows the interface.

  All 400 goods and the reference items gained German labels, as did the product-type and
  fallback-material tables and the dimension hint under a suggestion. This is not
  decoration: the suggestion a user clicks becomes the description in the goods column of
  a waybill.

### Fixed (CI)

- **The frontend CI job had never once run.** `ci.yml` pinned Node 20 while `jsdom` 30
  declares `^22.22.2 || ^24.15.0 || >=26` and `undici` 8 declares `>=22.19.0`, so
  `npm test` died with `webidl.util.markAsUncloneable is not a function` before a single
  test was collected. The job has been red on `main` since it was introduced in 1.24.2 —
  the backend half was green, which is presumably why it went unnoticed. Both workflows
  now use Node 22, matching what the toolchain asks for.

### Tests

- `test_shipping_name_language.py` pins the ADR/IMDG/IATA split, the fallback for entries
  with no German name, and the road-then-sea sequence. It also holds the lookup and the
  export to the same answer — a suggestion that differs from what gets exported is worse
  than no suggestion.
- `test_catalog_search_language.py` covers the three languages, cross-language searching,
  a German name that exists only as a label, and the guarantee that a label is never
  empty — an empty label means an empty goods column.
- `seed/materials.json` and `seed/reference_items.json` joined the completeness check, so
  a new material has to arrive in all three languages.

## [1.29.0] — 2026-08-03

German as a third interface language, and one place that decides which language anything is in.

### Added

- **Deutsch.** The interface, the field labels, the dangerous goods help texts, the
  compliance warnings and the generated documents are now available in German alongside
  Dutch and English — 592 texts across the document registry, the compliance rules, the
  DG instructions and the seed data, plus the 350 interface strings.

  German transport terminology follows the official wording where the regulations have
  one: *Beförderungskategorie* for the ADR 1.1.3.6 transport category, *Verpackungs-
  anweisung* for the packing instruction, *schriftliche Weisungen* for the instructions
  in writing, and the IMDG distinction between *entfernt von* (away from) and *getrennt
  von* (separated from) — a difference that is the whole point of a segregation warning.

  The disclaimer says in its German text that it is a translation and that the Dutch
  version prevails; the governing law was and stays Dutch.

- **German input is understood too.** A language on the screen does not help if the paste
  box does not recognise what you type into it: an unrecognised product yields no weight
  and therefore no usable document. `Stahl Winkelprofil`, `Quadratrohr`, `Rundstab`,
  `Stahlblech`, `Träger`, `Betonplatte`, `Sperrholz`, `Kunststoffplatte` and their
  neighbours are now detected, the language detector answers in the language you wrote in
  rather than falling back to English, and `Stück`/`Stk` count as units.

  `PVC-Rohr` deliberately does not go through a bare `Rohr` pattern — a plastic pipe
  weighs an order of magnitude less than a steel one, and that is a wrong weight on a
  waybill rather than a cosmetic slip.

### Changed

- **One place decides the language, instead of eleven.** Every module that produced text
  carried its own copy of `"en" if language.startswith("en") else "nl"`. With two
  languages that was correct. With a third it would have silently answered "Dutch" for
  German — a German screen with Dutch warnings and a Dutch export — and `TEXTS[key][lang]`
  would have raised a `KeyError` outright.

  `app/core/languages.py` now holds the supported languages and the fallback order, and
  `normalise()`/`pick()` replaced every two-way branch. `pick()` falls back to the next
  language that does have the text rather than returning nothing: a field label in the
  wrong language can still be read, a field without a label cannot. The frontend has the
  same single point in `src/i18n/language.ts`, so the screen and the backend can no
  longer disagree about which language a document is in.

### Tests

- The completeness of a language is enforced, not eyeballed. `test_languages.py` walks
  the data files and asserts every block with a Dutch and an English text also carries a
  German one, that a list stays a list of the same length, and that a "translation" is
  not simply the Dutch text repeated. An AST pass over `app/` catches the same omission
  in code, and a source check fails on any two-way language branch coming back.
  On the frontend, `translations.test.ts` holds the three bundles to identical keys and
  identical interpolation variables.

### Known gaps

Both were closed in 1.29.1; the second one turned out not to be a gap in the data at all.

- The catalogue search (`search_catalog`) returns material names in Dutch regardless of
  the interface language. It takes no language parameter at all, so this affects English
  users today as much as German ones; the German labels are in the data, waiting. Making
  the search language-aware is its own change, touching the route and the frontend call.

- The proper shipping names come from the ADR source table, which carries Dutch and
  English but no German. A German user sees the German interface around an English or
  Dutch shipping name — which is what belongs on the document anyway, since the proper
  shipping name is prescribed and not translated freely.

## [1.28.1] — 2026-08-03

### Fixed

- **A field that promises a format now has to keep it.** The export only ever checked
  whether a required field was empty. The NHM commodity code on the CIM is labelled
  "box 24, 6 digits", but `72` or `7208 51` passed straight through onto an official rail
  consignment note. That is not cosmetic there: the carrier prices the shipment on that
  code and customs reads it.

  The check is generic — a `pattern` in the document registry — so the next field with a
  fixed shape gets it without new code. An empty required field is still reported as
  missing rather than as misformatted; sending someone twice to the same line for two
  different reasons helps nobody.

### Added

- **`scripts/probe_nhm_sources.py`** and a workflow to run it. Box 24 wants a six-digit
  NHM code and CargoPilot cannot supply a list, so the field says look it up elsewhere.
  Inventing six-digit codes is not an option here, so this measures first: is a candidate
  source reachable, does it carry six-digit codes *with* descriptions — a list of bare
  numbers is useless to someone choosing one — and does it cover the goods CargoPilot
  knows. The same order that worked for the Dangerous Goods List.

  It records nothing. Until a source turns up that holds up, box 24 stays a free-text
  field with a format check.

## [1.28.0] — 2026-08-03

The spreadsheet import used to guess in silence.

### Fixed

- **An unrecognised header meant columns 0, 1 and 2, with no way to tell.** A file laid
  out as `Ref | Benaming | Aant. | Eenh.` — none of those names are in the alias list —
  came out with the reference numbers as descriptions, the descriptions as quantities,
  and the header row imported as a cargo line. What a user saw of that was `status=error`
  and 0 kg, with nothing pointing at the column layout.

  The import still guesses, because the alternative is making every import manual. What
  changed is that it says so, and hands over enough to put it right.

### Added

- **A column mapping panel.** Every column comes back with its header and its first few
  values, so the dropdown reads `2. Benaming · Stalen hoekprofiel 80x80x8x6000` instead
  of "column 2" — with an unrecognised header there is no name to show, so the values
  have to do the work. A field can be left unmapped, and the first row can be marked as
  a header, which is what stops it being imported as cargo.
- The panel is amber when the layout was guessed and plain when the header was
  recognised, so it is obvious which of the two you are looking at.
- `POST /api/import/wizard-remap` applies a different mapping to the same rows. It is
  separate from the upload because **nothing about the file is kept on the server**: the
  rows travel with the request and come back as text. That costs some bandwidth and
  buys never leaving half a shipment sitting on the server.

## [1.27.1] — 2026-08-03

The Dangerous Goods List extractor checked itself against the UN cards, which are also
an IMDG source. That is one IMDG reading held up against another, and it measures
nothing.

### Changed

- **The class cross-check now reads ADR Table A** (`un_numbers.json`) instead of
  `card_data.json`. Agreement goes from 2322/2336 to **2328/2329**, and the fourteen
  differences drop to one:

  - Eleven were the cards, not the list: UN 2984–2992, 3548 and 3550 carried sequence
    numbers in their class field.
  - Six more appear and then resolve — UN 2186, 2421, 2455, 3537, 3538 and 3539. ADR has
    no division to give for these: the label column reads `BEFÖRDERUNG VERBOTEN` for the
    ones forbidden on the road, or `siehe 5.2.2.1.12` for articles carrying the labels of
    each hazard present. They travel by sea and the IMDG Code names their division
    normally. Comparing where one source has no answer is not a check, so those entries
    are left out rather than counted as disagreeing.
  - What remains is **UN 3423**, the genuine 42-24 reclassification from 8 to 6.1 (8) —
    which the list confirms itself with its change marker.

- A UN number can appear in Table A more than once (UN 1950, aerosols, is both 2.1 and
  2.2), so divisions are collected as a set. And where the IMDG Code says class 2 while
  ADR gives 2.1, that is not a contradiction but a difference in how finely the two
  regimes divide; a class that heads an ADR division counts as agreement.

### Removed

- **The `class` field from `card_data.json`** and from `extract_un_card_data.py`. Nothing
  in the application ever read it — only that cross-check. It was also wrong: the card
  parser picked up the wrong line for those eleven substances, and where two card
  variants disagreed `merge()` kept both, producing `["10", "9"]`. Repairing a field
  nobody reads is wasted effort.

### Notes

- The division rule now exists twice: in `parse_hazards()` and in the extractor, which
  runs in GitHub Actions with only pymupdf and cannot import the application. A test ties
  them together over all 2928 Table A entries, and it earned its keep immediately — it
  caught that the copy skipped the label normalisation that turns `9A` into `9`.

## [1.27.0] — 2026-08-03

The manifest from v1.26.0 knew the IATA DGR expires on 31 December 2026, but only told
whoever asked `/api/regulatory`. Someone making an air declaration in 2027 saw nothing.

### Added

- **A compliance result now says when it was computed with an edition that no longer
  applies.** The warning reaches the wizard *and* the export, because a document outlives
  the session it was made in while a screen does not. Expiry is not a prohibition, so it
  warns rather than blocks — stopping the export would only push people to work around
  the check.
- **`stale_rule_sets()`, which is deliberately not the same as `expired_rule_sets()`.**
  The 41-22 UN cards are expired *and knowingly replaced*: columns 16a and 16b have come
  from the 42-24 list since v1.23.0, and what the cards still supply — marine pollutant
  and bulk — did not change with the edition. Warning about that on every single check
  would make warning itself worthless: someone who dismisses a message every time will
  dismiss the one that matters too. A rule set carrying `superseded_by` is left out.

  Today this reports nothing at all. On 1 January 2027 it reports the IATA DGR, and only
  to the IATA profile — a road shipment has no use for an air-freight notice.
- **The manifest id travels with the result**, in the compliance response and under the
  panel, so a bug report can say which data the installation computed with.

## [1.26.0] — 2026-08-03

### Added

- **A regulatory manifest**, at `GET /api/regulatory` with a compact form on
  `GET /api/health`. Per rule set: edition, source, validity period, errata, what it
  covers, and a SHA-256 over every data file behind it.

  It answers two questions documentation cannot. **Has an edition expired?** The IATA
  DGR is replaced yearly and the 67th edition runs to 31 December 2026; from 1 January
  2027 the manifest reports it as expired rather than quietly carrying on. The UN cards
  (41-22) already come out as expired — still used, but only for marine pollutant and
  bulk carriage, and the entry says so. **Do two installations hold the same data?** The
  `manifest_id` is a hash over all seed files together.

  Where something is not tracked, it says so: IATA addenda and operator variations are
  named as out of scope rather than left to look complete.

- **An `Authorization` field on the IATA declaration** — the approval, exemption or DGR
  reference a shipment flies under. The template CargoPilot fills has no form field for
  it (that box sits inside the goods table), so it is written as its own labelled line
  under that table. Left empty it is omitted entirely: an empty box with the word
  "Authorization" in it suggests something was approved.

### Notes

- The reviewer's concern about the IATA edition turned out to be unfounded: the
  compliance rules already cite the 67th edition (2026). A test now ties the manifest and
  those rules together so they cannot drift apart.

## [1.25.0] — 2026-08-03

> [!CAUTION]
> **Reverted in [1.29.3](#1293--2026-08-04). Do not run this version or anything up to
> 1.29.2 unless you set `APP_SECRET_KEY` and `CORS_ALLOWED_ORIGINS` yourself.** What this
> release introduced — refusing to start on a published or empty signing key — matched the
> values CargoPilot itself shipped with, so installations that had not configured both by
> hand simply died at startup. The signing key is generated automatically from 1.29.3
> onwards; see [Configuration](docs/configuration.md#the-signing-key-looks-after-itself).
>
> The note as it read at the time:
>
> > **Upgrading may stop your container on purpose.** If you never set `APP_SECRET_KEY`,
> > CargoPilot now refuses to start and tells you what to put there — including a
> > ready-made key. Changing the key logs everyone out; nothing else is lost.

### Fixed

- **An installation that never set `APP_SECRET_KEY` had no working authentication.**
  That key signs the JWT that says you are logged in, and its default — `change-me` —
  is published in this repository. Anyone holding it can write themselves a valid admin
  token, so there was no login to bypass; it was already bypassed. `APP_ENV` defaults to
  `production`, so this was the state of every deployment that followed the quickstart
  without setting the variable.

  The application now stops at startup. Logging a warning was the alternative and it is
  not one: logs go unread and the app keeps serving.

### Added

- **`app/core/security_checks.py`**, run before the application is even assembled.
  Three things are refused in production, all reported at once so a single restart is
  enough:

  - `APP_SECRET_KEY` that is empty, published (`change-me`, `dev-secret`, the
    placeholder from `.env.example` — which is 34 characters and would otherwise have
    passed a length check) or shorter than 32 characters.
  - `CORS_ALLOWED_ORIGINS=*` while the API works with cookies, which lets any website
    make requests on behalf of a logged-in user.
  - `ADMIN_PASSWORD` set to one that appears in this project's own documentation.

  The error carries a freshly generated key that is usable as-is, and a test asserts
  that the suggested key passes the check — an error message that stops the app has to
  contain its own solution.

- Anything that is not clearly a development environment counts as production, so a
  typo in `APP_ENV` cannot quietly switch the check off.

### Changed

- `.env.example` no longer ships a configuration that would be refused: the secret and
  the admin password are empty with instructions above them, and `CORS_ALLOWED_ORIGINS`
  names an address instead of `*`.

## [1.24.2] — 2026-08-03

Checks that run on their own, and one gap they found.

### Added

- **CI** (`.github/workflows/ci.yml`): backend pytest and the frontend tests plus
  typecheck on every push and pull request to main. The workflows here were all about
  publishing; the tests only ran locally, so a broken test could travel all the way to
  a release.
- **A version-consistency test.** The number lives in four places and they must agree.
  This is not theoretical: an external review of CargoPilot produced a list of problems
  that were largely already fixed, because the reviewer was reading
  `frontend/package.json` at 1.14.1 while the rest of the project was far past it. The
  test also insists the changelog leads with the current version.
- **Export integration tests** that read the generated PDF back: the export runs the
  compliance check itself, a Q above 1 blocks it while a Q within the limit does not,
  the air declaration carries the IATA packing instruction and not the ADR one, the
  emergency contact reaches the document, and the declaration comes out flat so the
  values cannot be edited away.

### Fixed

- **An export above the ADR 1.1.3.6 threshold said nothing.** Only an incomplete points
  calculation produced a warning; going over the threshold, or carrying a category 0
  substance, produced none at all. Neither is forbidden — but the exemption lapses, and
  with it come driver training, an ADR vehicle, orange plates and extinguishers. Someone
  who last saw "exemption possible" on screen now reads on the export that it no longer
  applies, with the totals behind it.

## [1.24.1] — 2026-08-03

Two defects in the compliance panel that only a test would catch, and the tests to
catch them.

### Fixed

- **A slow older check could overwrite a newer one.** Two checks can be in flight at
  once — you keep typing while the previous request is still out — and if the first
  resolves last, its result won. The screen then showed an outcome belonging to input
  from two edits ago. Each check now carries a sequence number and a stale response is
  discarded.
- **A 422 came out as `[object Object]`.** FastAPI answers a validation error with a
  list of `{loc, msg}` per field, and that went straight into `new Error()`. You could
  see something was wrong but not what, or which field. `describeDetail()` in the API
  layer now turns it into `entries → 0 → products → 1 → adr_total_quantity: hoeveelheid
  '-5 L' moet groter dan nul zijn`, and the panel renders it as an alert over several
  lines. Since v1.24.0 refuses unusable input, this is the normal path rather than an
  edge case.

### Added

- **Vitest and Testing Library**, with `npm test` in `frontend/`. Thirteen tests cover
  the panel's core promise — what is on screen belongs to the input that is there now:
  automatic re-check after the debounce, the previous outcome cleared the moment input
  changes, a stale response losing to a newer one, and a validation error appearing
  readably with no old result left beside it.

## [1.24.0] — 2026-08-03

The compliance endpoint validates its input instead of coercing it.

### Added

- **`backend/app/schemas/dg_compliance.py`** — `ComplianceRequest`,
  `ShipmentPosition`, `DangerousGoodsProduct` and a `RegulatoryProfile` enum.
  `POST /api/dg/compliance` took `entries: list[dict]` and `profiles: list[str]`, so
  Pydantic never looked at them and the calculation layer had to make the best of
  whatever arrived.

  Two cases are dangerous there, because they do not surface as an error but as a
  *more favourable* answer than reality:

  - A negative quantity lowers the ADR 1.1.3.6 points total and can suggest an
    exemption that does not apply. `-5 L`, `0` and `0 kg` are now refused.
  - A misspelled profile (`IDMG`) silently produced no sea-transport check at all,
    and the screen then showed a clean result with nothing behind it. Profiles are
    an enum: ADR, RID, ADN, IMDG, IATA.

  Also refused: a packing group other than I/II/III, a transport category outside
  ADR's 0–4, and a Q component with `n` or `M` at zero — which used to drop out of
  the sum unnoticed. All of these return **HTTP 422 before anything is calculated**.

  Empty stays allowed. The wizard sends half-filled input while you work, and the
  check is supposed to report `incomplete` rather than refuse the request. Fields
  the schema does not name are passed through untouched, and `class` keeps its own
  name on the way to the calculation layer.

## [1.23.1] — 2026-08-03

Community health files, so it is clear how to report something and what happens next.
No change to the application.

### Added

- **`CONTRIBUTING.md`** — says plainly that this is a personal project: reports and
  corrections are very welcome, code should be agreed in an issue first. Covers what a
  useful report contains for weights, documents and dangerous goods, and repeats the two
  standing rules: no regulatory text in the repository, and redact real shipment data
  before attaching anything to a public issue.
- **`SECURITY.md`** — private vulnerability reporting through GitHub, with the scope
  spelled out for a self-hosted app: authentication and the admin bootstrap, file upload
  and PDF handling, path traversal in export and UN card downloads, and
  `CATALOG_AUTO_SYNC` fetching external URLs at startup. Wrong regulatory data is
  explicitly *not* a security issue — it is a normal bug.
- **`CODE_OF_CONDUCT.md`** — Contributor Covenant 2.1, with the private advisory thread
  as the confidential channel since the repository publishes no email address.
- **Issue forms** in `.github/ISSUE_TEMPLATE/`: a bug report, a data-or-document
  correction that asks for the source and its edition, and an idea form that asks for the
  situation rather than the feature. Blank issues are off; the security advisory, the
  documentation and the rule-set-editions table are linked instead.
- **`.github/pull_request_template.md`**, with the project's own checks: changelog, the
  three version files agreeing, both language files, no regulatory text, no real shipment
  data.

## [1.23.0] — 2026-08-03

The Dangerous Goods List itself, all 2860 entries of it, now backs columns 16a and 16b —
the columns 7.2.3.1 lets take precedence over the segregation table.

### Added

- **`backend/seed/dg/imdg_dgl.json`**: chapter 3.2 of IMDG Amendment 42-24, read by
  `scripts/extract_imdg_dgl.py` from IMO resolution **MSC.556(108)**. 2860 rows over 2347
  UN numbers — entries with several packing groups appear once per group — carrying class,
  subsidiary hazards, packing group, special provisions, limited and excepted quantities,
  packing and IBC and tank instructions, EmS, stowage and handling, segregation, and the
  properties column.
- **`app/services/dg/dangerous_goods_list.py`** reads that file per UN number and splits
  the columns the way the code writes them: `Category B SW2 SW5` into a stowage category
  and its codes, `SGG2 SG27 SG31` into segregation groups and SG codes. A dash is layout,
  not a value, and is dropped rather than passed on.
- **Stowage category for 2324 UN numbers**, where the UN cards carried it for none.
- **The change marker.** The list prints a triangle in front of every entry Amendment
  42-24 touched; those 66 entries are flagged, and the wizard says so.
- Special provisions, packing instructions, tank instructions and the properties column
  are surfaced per substance.

### Changed

- Column 16b now comes from the list rather than the UN cards. Coverage goes from 840 to
  847 UN numbers, and 81 codes that the card extraction had dropped mid-list come back —
  UN 1295 for instance carried `SG5 SG8 SG13 SG25` and actually has
  `SG5 SG8 SG13 SG25 SG26 SG36 SG49 SG72`. No substance loses a code except UN 2988,
  whose card row is misaligned (see below). Column 16a gains 118 UN numbers and the H
  codes of 7.1.6, which the cards did not name.
- Segregation groups are taken from 3.1.4.4 and column 16b together instead of 3.1.4.4
  alone, and both lookups now honour the packing group.

### Notes

- The extraction checks itself against two independent sources and refuses to write below
  the agreement threshold. It came out at **EmS 2293/2293** and **class 2322/2336**.
  All fourteen class differences were examined and none is a misread: twelve are defects
  in `card_data.json`, where UN 2984–2992, 3548 and 3550 carry sequence numbers
  (`"4"`, `"5"`, `["13","14","12"]`, `"6.3"`) instead of classes; UN 1950 is the ADR split
  `2.1 / 2.2` against the code's plain class 2; and UN 3423 is a genuine 42-24
  reclassification from 8 to 6.1 (8), which the list's own change marker confirms.
  `card_data.json` is left as it is for now — it is a separate source and correcting it is
  its own job.

## [1.22.0] — 2026-08-02

The IMDG Code's own chapter 7 now supplies the wording behind every column 16a and 16b
code, replacing the fragments that were scrapeable from the UN cards.

### Added

- **The stowage, handling and segregation code descriptions**, in
  `backend/seed/dg/imdg_codes.json`: **SW1–SW31** from 7.1.5, **H1–H5** from 7.1.6 — a
  series the app did not carry at all — and **SG1–SG78** from 7.2.8. Read by
  `scripts/extract_imdg_codes.py` from IMO resolution **MSC.556(108)**, the instrument
  that adopted Amendment 42-24. The compliance findings and the wizard both prefer this
  wording; the card paraphrase remains only as a fallback.
- **Reserved codes are kept apart.** SG64, SG66 and SG73 read `[Reserved]`, which is not
  a provision, so they are never offered to a user as guidance.

### Fixed

- The extractor's first run found nothing: `find_section` anchored `^` against the whole
  page without `re.MULTILINE`. It now matches on the introducing sentence, which is
  unique — the section number appears in the contents list and in five cross-references.
- The workflow reported "nothing to commit" after a successful extraction, because
  `git diff` does not see a file that is still untracked.

### Notes

Two readings confirmed earlier work against the source rather than against a summary.
7.2.3.1 reads, verbatim, *"In case of conflicting provisions, the provisions of column 16b
of the Dangerous Goods List, always take precedence"* — the rule implemented in v1.21.0.
And SG75 is absent from the segregation code list altogether, where SG64, SG66 and SG73
are explicitly reserved: independent confirmation that the SGG1a marking removed in
v1.21.0 had indeed left the Code.

## [1.21.0] — 2026-08-02

IMDG Amendment 42-24 has been mandatory since 1 January 2026. This release closes the gap
without pretending to a full rebuild: the tables that turned out to be unchanged are
confirmed as current, the per-substance changes are applied as a difference layer, and
column 16b now takes the precedence the Code gives it.

### Added

- **An IMDG 42-24 difference layer** (`backend/seed/dg/imdg_42_24.json`), laid over the
  41-22 UN card data. It holds the eleven new UN numbers with their EmS schedules — sodium
  ion batteries UN 3551/3552, the battery-powered vehicle entries UN 3556–3558, disilane
  UN 3553, gallium in manufactured articles UN 3554, the trifluoromethyltetrazole entry
  UN 3555, both fire suppressant dispersing device entries UN 0514/3559 and the new
  tetramethylammonium hydroxide entry UN 3560 — plus 42 amended entries and the new
  stowage code SW31.
- **The new UN numbers are searchable.** Sodium ion batteries exist in IMDG 42-24 and not
  yet in ADR 2025; they are merged into the lookup marked as IMDG-only, so a sea shipment
  can find them instead of coming up empty.
- **Per-substance change notes.** UN 2303 became a recognised marine pollutant and gained
  SW1; UN 1361 gained SW27; UN 2956 gained SW11; UN 3536 moved to stowage category D. Each
  change is shown against the substance in the wizard, in Dutch and English.
- **The UN 1361 document requirement of 5.4.1.5.18** — date of production, date of
  packing, mean material temperature and ambient temperature on that day — is raised as a
  requirement when the substance is declared.
- **IMDG 7.2.3.1 precedence.** The class segregation table and a substance's own SG codes
  can disagree about the same pair; the Code says column 16b always wins. Nitric acid
  beside sulphur is the plain case: the table says "away from", SG16 says "separated from",
  and the 16b provision now governs. Both findings stay visible — the governing one says
  it governs, the superseded one says what superseded it — because hiding a segregation
  finding is a worse failure than showing one too many.

### Changed

- **Chapter 7.2 is no longer flagged as out of date.** The only change 42-24 makes there
  is a rewording of 7.2.6.1. The class segregation table (7.2.4), the exemption tables
  (7.2.6.3), the class 1 compatibility matrix (7.2.7.1.4) and the segregation groups
  (3.1.4.4) are unchanged, so the tables the app computes with are the current ones. The
  `rule_sets` metadata on every result says this, names the source of the difference layer,
  and lists what the layer does not cover.
- **A changed classification is reported, never silently applied.** UN 3423 becomes class
  6.1 with a subsidiary 8 in 42-24 while ADR 2025 still lists it as class 8. Segregation is
  still computed on the ADR classification and a warning says so, because swapping the
  class behind the scenes would change the outcome with nothing on screen to explain why.

### Removed

- **The SGG1a tagging.** The separate segregation-group marking for strong acids was
  dropped from the Code with Amendment 41-22 — the UN cards never mention it and 42-24
  leaves 3.1.4.4 alone — but 21 substances still carried it. Removed from the seed, from
  the label lookup and from the documentation.

## [1.20.0] — 2026-08-02

Fixes from an external review: calculation errors, stale state, the IATA PDF, and
export enforcement. Every confirmed defect has a regression test that reproduces
the reported failure.

### Fixed

- **Derived quantities no longer go stale.** The ADR total and the Q net quantity are
  computed values, but they were only filled when empty — so after editing 2 packages of
  10 L into 3 of 20 L, the description showed 60 L while the points calculation still used
  20 L and the Q value 10 L. They are now recomputed from the current package data on
  every derivation; `adr_total_quantity_override` and `q_net_quantity_override` pin a
  manual value. The wizard also re-derives when quantities, contents or packaging change,
  not only when a UN number changes.
- **The Q value could round an exceedance away.** Component ratios were rounded to four
  decimals before summing: 0.50001 + 0.50001 became 1.0 and passed. The sum is now taken
  over unrounded Decimal ratios and only the result is rounded up — that case yields
  Q = 1.1, exceeded.
- **Invalid Q components no longer vanish.** A missing, zero or negative n or M used to
  drop the component silently, and with fewer than two left the whole result disappeared.
  The position now reports status `incomplete` with the reason.
- **Negative quantities are invalid input, not a discount.** A numeric −5 lowered the ADR
  points total; the text "-5 L" was read as +5 because the parser dropped the sign. The
  parser keeps the sign and both calculations treat non-positive quantities as incomplete.
- **The IATA declaration no longer carries an ADR packing instruction.** The automatic
  derivation fills the generic field with the ADR instruction (P001, IBC02, …), and the
  official PDF printed that field. The PDF now uses `iata_packing_instruction`, accepts a
  numeric instruction typed into the generic field, and prints nothing rather than an
  instruction that is invalid in the air.
- **The 24-hour emergency contact reaches the PDF.** It was a required input that was
  never written; it now lands in Additional Handling Information.
- **The stale compliance panel.** The result is cleared the moment the substances change
  and re-checked automatically after a short debounce, instead of keeping the previous —
  possibly green — outcome on screen until someone pressed the button.
- **Info findings looked like problems.** The 7.2.6.3 exemption has severity `info` but
  was styled identically to a warning; it is now visually distinct.

### Added

- **Export re-runs the compliance engine server-side.** The panel in the wizard is an
  aid; the frontend is no longer the only place where compliance is enforced. A DG
  document export now blocks on segregation errors and on an exceeded Q value, and
  carries the remaining findings as warnings.
- **Every compliance result names its rule sets** — including, prominently, that the
  IMDG data on board is Amendment 40-20 (class tables) and 41-22 (per-substance data)
  while **Amendment 42-24 is mandatory since 1 January 2026**. Until the data is
  refreshed, IMDG outcomes are indicative and the current Code prevails. See
  [docs/dangerous-goods.md](docs/dangerous-goods.md#rule-set-editions).

## [1.19.0] — 2026-08-02

SG72, and it turned out to be a relaxation.

### Added

- **The four tables of IMDG 7.2.6.3**, from chapter 7.2 of Amendment 40-20 — the same
  edition as the class segregation table. SG72 in column 16b points at them, and 36
  substances carry it.
- SG72 reads "See tables in 7.2.6.3", which sounds like an extra restriction. It is the
  opposite: *"No segregation needs to be applied … Substances within the same table
  7.2.6.3.1, 7.2.6.3.2 or 7.2.6.3.3 are compatible with one another."* Two organic
  peroxides from table 7.2.6.3.4, for instance, need no segregation between them.
- **The exemption never removes a warning.** Suppressing a segregation finding on the
  strength of a rule is a worse failure than showing one too many, so the exemption is
  reported alongside the finding with its table named. The finding and its legal basis end
  up in view together and the judgement stays with the shipper — which is how a safety
  adviser would read it anyway.
- Table 7.2.6.3.4 carries the caveat of 7.2.6.4: the dangerous reactions of 7.2.6.1.1 to
  7.2.6.1.4 continue to apply. That is stated in the finding.

With this, five provisions remain shown-but-not-checked, and none of them is a rule: SG1
and SG77 modify other provisions, SG48 and SG71 are definitions, and SG69 applies only to
waste aerosols.

## [1.18.0] — 2026-08-02

The remaining segregation provisions, as far as they go.

### Added

- **Provisions that name a substance are now checked.** Eight of them — sulphur, chlorine,
  ammonia, bromine, carbon tetrachloride, ammonium salts, mercury salts, and explosives
  containing chlorates or perchlorates. The wording is resolved to UN numbers in
  `dg_compliance.json`, deliberately narrowly: SG62 says "sulphur", which means elemental
  sulphur (UN 1350, UN 2448), not sulphur dioxide.
- Where a defined segregation group stands in for a narrower wording — SGG2 "ammonium
  compounds" for the "ammonium salts" of SG22 — the warning says so, because the match is
  wider than the provision.
- **Provisions whose target is ordinary cargo are raised as requirements.** Foodstuffs,
  animal and vegetable oils, odour-absorbing cargo, liquid organic substances. CargoPilot
  does not know what non-dangerous cargo travels alongside, so these appear whenever the
  substance is in the shipment — the same shape as the existing ADR CV28 foodstuff
  warning. SG26 is conditional and only appears next to class 2.1 or 3.

### Fixed

- **SG74 was missed by the parser.** It reads "Segregation as for 1.4G" without the word
  "class", so it fell through to the informational bucket instead of becoming a rule.

### Still shown but not checked

Six provisions, and they are not rules: SG1 and SG77 modify other provisions, SG48 and
SG71 are definitions, SG69 is conditional on the substance being waste aerosols, and SG72
points at a table in IMDG 7.2.6.3 that is not in any source we hold. Turning any of these
into a check would mean inventing the rule.

## [1.17.0] — 2026-08-02

Column 16b is now a check, not just a note.

### Added

- **The segregation provisions of column 16b are applied to the shipment.** The class
  table of IMDG 7.2.4 works on class; column 16b adds provisions per substance. Load
  anhydrous ammonia (UN 1005) together with hydrochloric acid (UN 1789) and the compliance
  panel now reports both sides of it: *"Stow separated from SGG1 (Acids). Stow 'separated
  from' SGG1 – acids (SG35)"* against the ammonia, and the mirror-image SG36 against the
  acid. Until now the codes were only displayed.
- **The meaning of each code was read from the cards, not written from memory.** Every SG
  code appears in a fixed sentence — *Stow "separated from" class 5.1 (SG17)* — so the
  action and its target are parsed out of the source itself. Of the 70 codes in use, 48
  name a class or a segregation group and became machine-checkable; the other 22 point at
  foodstuff tables, named substances or a table in the Code, and are shown to the user
  without being acted on. A wrong segregation rule is a safety-relevant error, so guessing
  at the ones that do not parse cleanly is not on the table.
- **Exceptions are honoured.** SG14 reads "separated from class 1 except for division
  1.4S". Treating 1.4S as a second target would warn about a load the Code explicitly
  allows, so the exception is parsed separately and suppresses the finding.
- A bare class target covers its divisions — "separated from class 1" applies to 1.1D as
  much as to 1.3G — and subsidiary risks count towards a match, not just the primary class.

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
