# Dangerous goods

CargoPilot aims to need one thing from you: the **UN number**. Everything the regulations
derive from that number, it derives for you — and then it checks the result.

> [!IMPORTANT]
> This is a typing aid built on factual reference data. It is not a safety adviser, and
> it does not replace a DGSA. Classification, packaging, marking, labelling and
> documentation remain the shipper's responsibility. The current edition of ADR, RID,
> ADN, the IMDG Code and the IATA DGR is always the authority.

- [What one UN number gives you](#what-one-un-number-gives-you)
- [The checks it runs](#the-checks-it-runs)
- [What blocks an export](#what-blocks-an-export)
- [Per transport mode](#per-transport-mode)
- [UN cards](#un-cards)
- [How complete is the data?](#how-complete-is-the-data)

## What one UN number gives you

Type `1203`, or search for "gasoline". CargoPilot fills in:

| | |
|---|---|
| **Proper shipping name** | In Dutch and English |
| **Class and division** | Real divisions, not just the class — see the note below |
| **Subsidiary risks** | From the labels column, e.g. `8 (5.1)` for nitric acid |
| **Classification code** | `F1`, `M4`, `C1` — kept separate, never mixed into the description |
| **Packing group** | I, II or III |
| **Packing instruction** | Per rulebook — the ADR instruction is never used for air |
| **Transport category and tunnel code** | For the 1,000-point rule and route restrictions |
| **Kemler number** | Hazard identification number |
| **LQ and EQ limits** | Limited and excepted quantities, explained in plain language |
| **EmS emergency schedules** | Fire and spillage schedule for sea transport, with descriptions |
| **Segregation groups** | SGG1–SGG18, for example "SGG1 (Acids), SGG1a (strong acids)" |
| **Stowage codes** | SW codes from column 16a, with the wording that explains them |
| **Segregation codes** | SG codes from column 16b, per substance |
| **Marine pollutant** | Column 4 — yes, no, or depends on the substance |
| **Bulk carriage** | Whether the substance may travel in bulk, and under which BK instruction |
| **Air freight rules** | Cargo Aircraft Only, IATA packing instruction, air prohibitions |
| **Carriage prohibition** | Substances ADR does not permit for carriage at all |

Quantities, packaging type and masses come from the packages you already entered. Only
empty fields are filled — your own corrections always survive.

**About divisions.** ADR Table A lists gases as class "2" and explosives as class "1",
with the real division hiding in the labels column (2.1 / 2.2 / 2.3) or the
classification code (`1.4S`). CargoPilot resolves the actual division, because
segregation and loading compatibility depend on it.

### The description line, written for you

Each rulebook wants the same facts in a different order. CargoPilot assembles the
official line per profile and shows it before you export:

| Profile | Example |
|---|---|
| **ADR / RID / ADN** | `UN 1203, GASOLINE, 3, II, (D/E), 10 jerrycan, 200 L` |
| **IMDG** | Adds the EmS code and marine pollutant marking |
| **IATA** | Adds the packing instruction and Cargo Aircraft Only |

Plus the total per transport category (ADR 5.4.1.1.1.1), which is mandatory when you use
the 1,000-point exemption and used to be manual work.

## The checks it runs

The compliance panel updates as you type.

**ADR 1.1.3.6 — the 1,000-point rule.** Quantities are multiplied by the factor for
their transport category (×50, ×3, ×1, ×0) and totalled. You get one of four verdicts:
exemption possible, over 1,000 points, category 0 (no exemption), or incomplete — plus
what the exemption does and does not release you from.

**ADR 7.5.2 — loading together.** Warns on class 1 (other than 1.4S) with other classes,
on mixed compatibility groups within class 1, and on the CV28 separation of foodstuffs
from labels 6.1/6.2 and certain class 9 substances.

**IMDG 7.2.4 — sea segregation.** The full class segregation table, Amendment 40-20,
with codes 1 to 4 from "away from" to "separated longitudinally". Subsidiary risks count
too, and a subsidiary class 1 risk is treated as division 1.3 (7.2.3.3), which is
stricter than the primary hazard alone. The table is pinned verbatim in a test so a
future edit cannot slip through unnoticed.

**IMDG 7.2.5 — segregation groups.** All eighteen groups, with 632 substance entries
across 539 UN numbers. Warns about acids with alkalis, acids with cyanides (hydrogen
cyanide), acids with chlorites or hypochlorites (chlorine dioxide, chlorine gas), acids
with nitrites, acids with azides (explosive hydrazoic acid), acids with metal powders
(hydrogen), and peroxides with acids.

**Columns 16a and 16b, per substance.** The stowage (SW) and segregation (SG) codes for
2,336 UN numbers, read from the UN cards. Nitric acid, for instance, yields
`SG6, SG16, SG17, SG19, SG36, SG49` — and each is shown with the wording that explains
it, because a bare code tells a user nothing. This used to be the one place the app had
to send you to the Dangerous Goods List itself.

**And they are checked, not just shown.** Load anhydrous ammonia with hydrochloric acid
and you get both sides of it: the ammonia carries SG35 (separated from acids) and the acid
carries SG36 (separated from alkalis).

Of the 70 codes in use:

| | |
|---|---|
| Checked against the rest of the shipment | 49 name a class or a segregation group |
| Checked against a named substance | 8 — sulphur, chlorine, ammonia, bromine, carbon tetrachloride, ammonium and mercury salts, chlorate explosives |
| Raised as a requirement to verify | 7 whose target is ordinary cargo: foodstuffs, oils, odour-absorbing cargo |
| Shown as text only | 6 |

The six that are only shown are not rules: two modify other provisions, two are
definitions, one applies only to waste aerosols, and SG72 points at a table in IMDG 7.2.6.3
that is not in any source we hold. Turning those into checks would mean inventing them.

Exceptions count. SG14 reads "separated from class 1 **except** for division 1.4S", so a
1.4S package alongside does not raise it.

**IMDG 7.2.6.5 — the class 8 exception.** Acids and alkalis of packing group II or III
may travel together in packages up to 30 L or 30 kg, provided they do not react
dangerously and the transport document carries the 5.4.1.5.11.3 statement.

**IMDG 7.2.7.1.4 — explosives compatibility.** The full A-to-S compatibility group
matrix. Group S is compatible with everything except L; group L only with its own type;
the special provisions for groups G, L and N are shown as warnings. Includes the
ammonium nitrate exception of 7.2.7.2.1.

**IATA Table 9.3.A — air segregation.** Incompatible packages (class 1 excluding 1.4S
against 2.1/3/4.1/5.1; class 8 against 4.3), subsidiary risks included, plus the lithium
battery rule keeping UN 3090/3480 apart from classes 1, 2.1, 3, 4.1 and 5.1.

**IATA 5.0.2.11 — the Q value.** Q = Σ n/M, rounded up to one decimal, with a warning
above 1.0.

**Class-specific document requirements** are called out: net explosive mass and
compatibility group for class 1, temperature control for self-reactive substances and
organic peroxides (4.1 and 5.2), the responsible person for class 6.2, and radionuclides,
package category, transport index and criticality safety index for class 7. Sea freight
gets the container packing certificate; air freight the signature in duplicate.

## What blocks an export

Most findings are warnings. Two things actually stop you:

1. **An incomplete classification.** Each profile has its own minimum — UN number,
   proper shipping name and class everywhere; IATA also needs the packing instruction,
   number of packages and quantity.
2. **A carriage prohibition.** Fourteen substances that ADR Table A does not permit for
   carriage (aqua regia UN 1798, symmetrical dichlorodimethyl ether UN 2249, refrigerated
   hydrogen chloride UN 2186 and some n.o.s. entries with incompatible hazards) are
   recognised, shown in red, and refused for export. Carriage is only possible with an
   exemption from the competent authority.

## Per transport mode

The mode you chose selects the rulebook: **ADR** for road, **RID** for rail, **ADN** for
inland waterway, **IMDG** for sea, **IATA DGR** for air. The description line, the
required fields and the checks all follow from it.

For road transport there is no separate ADR document — the CMR and the AVC waybill carry
the 5.4.1.1.1 description themselves. See [Documents](documents.md#the-waybill-doubles-as-the-adr-transport-document).

## UN cards

At the end of the wizard, a shipment with dangerous goods can download the **UN cards**
for the substances it declared — a zip with one reference card per UN number, plus a
README listing what is in it and what is not.

Only the cards for **your** substances are bundled. A load of gasoline and chlorine gets
two cards, not the whole library. If a UN number has more than one card, all of them are
included; deciding which variant applies is not something this app should guess at.

The cards are for your own records. They are not transport documents, they are not
attached to anything CargoPilot generates, and they do not replace the current edition of
the regulations.

The library lives in `un_cards/` and is filled once by the **Fetch UN cards** workflow,
which reads the UN number out of every document rather than trusting its original
filename. In a checkout where that has not been run, the download option simply does not
appear. See [`un_cards/README.md`](../un_cards/README.md).

## How complete is the data?

| Data | Coverage |
|---|---|
| UN numbers with full ADR classification | 2,928 entries |
| EmS emergency schedules | 2,338 UN numbers — **99.5%** exact, from the official EmS Guide |
| Segregation groups | 632 entries across 539 UN numbers |
| UN packaging codes | All 107 codes of ADR 6.1.2 / 6.5.1.4 / 6.6.2 |
| Stowage and segregation codes per substance | 2,336 UN numbers — 1,242 with SW codes, 840 with SG codes |
| Marine pollutant status | 2,336 UN numbers — 202 confirmed, 38 explicitly not, the rest substance-dependent |
| IMDG class segregation table | Complete, Amendment 40-20 |
| Class 1 compatibility matrix | Complete, groups A to S |

Where a value genuinely differs by packing group, CargoPilot **shows both options rather
than guessing**. Forty-three UN numbers have a different EmS schedule per packing group —
UN 1826 (nitrating acid mixture) is treated as oxidising in group I and corrosive in
group II — and UN 3166 (vehicles) differs between gas and liquid propulsion.

Where an exact entry does not exist, an indicative class default is shown, clearly marked
as a suggestion, and it is not filled in automatically.

For where all this comes from, see [Data sources](data-sources.md).
