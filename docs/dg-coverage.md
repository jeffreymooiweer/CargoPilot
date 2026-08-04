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

**What the regime requires** is not. The regulatory texts are copyrighted and are
deliberately absent from this repository — that is the standing policy in
[Data sources](data-sources.md), and the machine this was written on has no access to them
either. That column is therefore written from knowledge of how these regimes are
structured, and it is reliable at the level of *which chapter governs what*, not at the
level of an exact limit or table value.

The practical consequence, and it is the whole reason this section comes first:

> **Nothing in this document is a citation, and nothing in it is ready to become a check.**
> Every rule named here must be verified against the current published text before it is
> implemented, exactly as the segregation tables and the EmS index already were. A
> segregation rule implemented from memory is worse than no segregation rule, because it
> looks like an answer.

Where a statement is one I would want checked before anyone leans on it, it is marked
**[verify]**.

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
| `seed/dg/un_numbers.json` | ADR Table A: class, classification code, packing group, labels, special provisions, LQ, EQ, packing instructions, transport category, tunnel code, hazard number, English and German names | 2,928 UN numbers |
| `seed/dg/imdg_dgl.json` | IMDG Dangerous Goods List (Amdt. 42-24): class, subsidiary hazards, PG, special provisions, LQ, EQ, packing/IBC/tank instructions, EmS, stowage and handling (16a), segregation (16b), properties | 2,860 rows over 2,347 UN numbers |
| `seed/dg/card_data.json` | Per-substance marine pollutant status and bulk carriage | 2,336 UN numbers |
| `seed/dg/ems.json` | Fire and spillage schedules | 2,338 UN numbers |
| `seed/dg/segregation_groups.json` | SGG1–SGG18 assignments | 629 entries over 539 UN numbers |
| `seed/dg/imdg_codes.json` | SW1–SW31, H1–H5, SG1–SG78 with their wording | 110 codes |

What is **not** held for any substance: IATA quantity limits per packing instruction,
ADN Table C, vehicle or tank codes, and any state or operator variation.

## Road — ADR

**Checked:** the 1.1.3.6 points calculation (categories, factors, the 1,000-point
threshold, category 0 as a hard stop) and the 7.5.2 mixed-loading prohibitions including
CV28 for foodstuffs. Classification comes from Table A. The description line follows
5.4.1.1.1 and the tunnel code is printed, correctly, only here.

This is the mode CargoPilot serves best, and the reason is simple: ADR Table A is the
dataset it was built on.

**Not checked, and worth knowing:**

- **Tunnel restrictions are never evaluated.** The code is printed on the document, but
  there is no route in the application, so nothing compares it against the tunnels on the
  way. A consignor reading `(D/E)` on a CMR may reasonably assume something has been
  considered. Nothing has. **[verify: ADR 8.6 and the column 15 code semantics]**
- **Limited and excepted quantities are explained, not applied.** The LQ value and the EQ
  code are shown with their meaning, but the quantity entered is never compared against
  them, and the exemptions of 3.4 and 3.5 are never applied. A shipment that could have
  travelled as LQ is still put through the full points calculation. **[verify: 3.4, 3.5]**
- **Nothing about the vehicle.** Equipment (8.1.4/8.1.5), placarding and marking (5.3),
  driver training (8.2), the ADR certificate of approval, tank codes. All outside the
  application. The 1.1.3.6 output does list what the exemption releases you from and what
  it does not, which is guidance rather than a check.
- **No security provisions.** Chapter 1.10 and high consequence dangerous goods are
  mentioned in the exemption text and nowhere else.

## Rail — RID

**Checked:** ADR's checks. That is the finding.

RID has its own 1.1.3.6 and its own mixed-loading chapter, and CargoPilot holds neither.
Since v1.29.5 the compliance panel says so next to the points table rather than presenting
an ADR figure as a RID answer, and the tunnel code — an ADR construct that RID Table A
does not have — is no longer printed on the CIM.

**What a rail specialist would additionally expect,** none of which is present:

- **The wagon rather than the transport unit.** RID's quantity limits attach to a wagon or
  a large container, not to a road transport unit. Whether the factors and the threshold
  are numerically the same is exactly the sort of thing that must be read rather than
  assumed. **[verify: RID 1.1.3.6]**
- **Shunting and marshalling.** Provisions that have no road equivalent at all.
  **[verify: RID chapter 7.5 and part 1]**
- **The CIM's own dangerous goods fields.** Box 24 (NHM) is a free-text field with a format
  check; the RID-specific entries in boxes 21/23 come from the shared DG data without any
  rail-specific validation.

**Assessment:** rail is the weakest of the five. The classification and the document are
sound; the compliance answer is an ADR answer wearing a RID label, and now says so.

## Inland waterway — ADN

**Checked:** ADR's checks, with the same caveat now shown.

ADN is not a variation on ADR the way RID is. It splits into two regimes — dry cargo
vessels and tank vessels — and the tank vessel side, with its own substance table, is a
different discipline altogether. **[verify: ADN parts 7.1 and 7.2, and Table C]**

**What is missing beyond the shared gaps:**

- **Anything vessel-specific.** Stowage and segregation aboard a dry cargo vessel, the
  requirements that follow from the vessel type, and every tank vessel provision.
- **The ADN transport document is generated from the shared DG data.** It carries the
  5.4.1.1.1 description and is a correct document as far as it goes; it has had no
  inland-waterway-specific review.
- **No ADN certificate, no expert on board, no degassing or venting provisions.**

**Assessment:** for packaged goods on a dry cargo vessel the document is usable and the
classification is sound. For anything in a tank vessel, CargoPilot has nothing to say and
should not be read as though it has.

## Sea — IMDG

This is the most thoroughly developed part of the application, and the only mode where the
segregation question is genuinely answered.

**Checked:** the 7.2.4 class table; the 7.2.5 segregation groups; the per-substance
segregation provisions of column 16b with the 7.2.3.1 precedence rule applied and both
findings kept visible; the 7.2.6.3 exemption tables, reported but never used to remove a
warning; the 7.2.6.5 class 8 exception; the 7.2.7.1.4 class 1 compatibility matrix with
the ammonium nitrate exception; and the Amendment 42-24 difference layer with its
reclassifications flagged rather than silently applied.

Subsidiary risks count throughout, and a subsidiary class 1 risk is treated as division
1.3, which is stricter than the primary hazard alone.

**Not checked:**

- **Stowage category is shown, not enforced.** Whether a substance may go on deck or under
  deck, and what that means for the rest of the load, is displayed as a category letter and
  left there. **[verify: IMDG 7.1]**
- **CTU packing.** The container/vehicle packing certificate is a set of declarations the
  user ticks. Nothing checks the load against them. The VGM has a real arithmetic
  cross-check, which is more than the certificate gets.
- **Limited and excepted quantities**, as on the road side: explained, not applied.
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
5.0.2.11, the Cargo Aircraft Only flag, and the requirement that the IATA packing
instruction rather than the ADR one reaches the declaration. The required-field set for
the Shipper's Declaration is the strictest of the five.

**The significant limitation, and it is not obvious from the interface:**

- **The Q value only computes if the user supplies M.** CargoPilot does not hold IATA's
  quantity tables, so the maximum net quantity per package for the applicable packing
  instruction has to be typed in by hand. Supply neither figure and no Q is calculated and
  nothing is said about it. The check is effectively opt-in, and someone who does not know
  the field exists will not be told that a limit went unchecked. **[verify: IATA DGR
  5.0.2.11 and table 4.2]**

**Also absent:**

- **Every quantity limit.** Net per package, per aircraft type, passenger versus cargo
  aircraft. Without the tables there is nothing to compare against.
- **State and operator variations.** Not held at all. In practice these decide a great deal
  of what actually flies, and an airline's variation can be stricter than the DGR.
- **Section I versus Section II** for lithium batteries, and the whole of the excepted
  quantity and limited quantity apparatus for air.
- **Overpack declarations, dry ice, radioactive material** beyond what the classification
  supplies.

**Assessment:** the segregation and the declaration are sound. The quantity side —
arguably the part of air freight where most shipments actually fail — is not covered, and
the Q value's dependence on user input is the least visible limitation in the application.

## Gaps ranked by what they cost

Ordered by how much harm someone could take before noticing, not by effort.

| # | Gap | Why it ranks here |
|---|---|---|
| 1 | **IATA quantity limits absent, Q silently opt-in** | A shipment can be assembled, declared and exported with no quantity check at all, and nothing says so. The user is not told the check did not run. |
| 2 | **RID and ADN answered with ADR tables** | Now labelled, which turns a wrong answer into an indication. Still the largest correctness gap of the five, and rail and inland waterway are offered as first-class modes. |
| 3 | **LQ and EQ explained but never applied** | Cuts both ways: a shipment that qualified for an exemption is over-restricted, and one that does not qualify is never told. |
| 4 | **Tunnel code printed, never evaluated** | Printing a code that has been considered by nobody invites the assumption that it has. |
| 5 | **IMDG stowage category shown, not enforced** | Lower because on-deck/under-deck is usually the carrier's call, not the consignor's. |
| 6 | **No marking, placarding or equipment checks in any mode** | Consistently absent, so unlikely to be mistaken for present — but it is the most common real-world failure. |

The first four are all the same shape: **the application knows something and shows it, but
does not act on it.** Showing a value next to a field reads as verification whether or not
any verification happened.

## What should and should not be built

**Worth building, in this order:**

1. **Say when a check did not run.** The Q value silently skipping is the clearest case.
   This needs no regulatory data, only honesty about what was and was not computed, and it
   addresses the top-ranked gap directly.
2. **Apply LQ and EQ.** The data is already on board — column 7a and the EQ code are in
   both `un_numbers.json` and `imdg_dgl.json`. This is arithmetic against values already
   held, not new regulatory content. **[verify: the exemption conditions of 3.4 and 3.5,
   which is where the actual difficulty is]**
3. **RID and ADN their own quantity and mixed-loading rules** — but only after the texts
   have been read. The labelling shipped in v1.29.5 is the honest interim.

**Not worth building, or not buildable here:**

- **IATA quantity tables.** Table 4.2 is copyrighted and is not available as open data.
  The same wall the IMDG Code presented. What is buildable is the field, the arithmetic and
  a clear statement when the input is missing — which is item 1.
- **State and operator variations.** These change per airline and per country and would be
  stale within months of shipping.
- **Anything about the vehicle, vessel or aircraft.** Outside what a document preparation
  tool should claim, and a consignor who needs it needs a safety adviser rather than an
  application.

**The pattern worth keeping.** Where CargoPilot cannot answer, it says so — the seven
segregation codes whose target is ordinary cargo are raised as *requirements to verify*
rather than resolved, the 7.2.6.3 exemption is reported but never used to delete a
warning, and 42-24 reclassifications are flagged rather than silently applied. That
instinct is why the IMDG side can be trusted. Extending it to the gaps above is more
valuable than any new table.

---

*This assessment covers CargoPilot v1.29.5. It is guidance for development, not a
compliance statement. Every document the application produces is a draft; see
[DISCLAIMER.md](../DISCLAIMER.md).*
