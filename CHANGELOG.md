# Changelog

All notable changes are documented here, following [Semantic Versioning](https://semver.org/).

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

> [!IMPORTANT]
> **Upgrading may stop your container on purpose.** If you never set `APP_SECRET_KEY`,
> CargoPilot now refuses to start and tells you what to put there — including a
> ready-made key. See [Configuration](docs/configuration.md#cargopilot-refuses-to-start-on-an-unsafe-configuration).
> Changing the key logs everyone out; nothing else is lost.

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
