# UN cards

One reference card per UN number, named after the number it describes:
`un_1203.pdf`, `un_3480.pdf`, and so on. When a UN number has more than one card,
the extras are suffixed: `un_1203-2.pdf`.

It holds **2,849 cards covering 2,336 UN numbers**, fetched by the
**Fetch UN cards** workflow (`.github/workflows/fetch-un-cards.yml`).

The source is Cantell's IMDG UN cards, 2023 edition (IMDG 41-22), published as
`imdg_2023_-_en_part1.pdf`, `part2.pdf` and so on. The part number is **not** the
UN number — `part1` is UN 0004 and `part2` is UN 0005 — so the workflow opens
every document and reads the number out of the card itself. Each card states it
under a `UN number` label and repeats it in the footer; both are read and must
agree.

`manifest.json` records what happened to every part: which UN number it was
identified as, how confident that was, and which of our known shipping names it
matched. Documents that could not be identified — including any card whose
heading and footer disagree — are parked in `_unidentified/` rather than filed
under a guess.

The parts ascend by UN number, so a card that steps backwards is flagged as out
of sequence even when it read cleanly. Nothing was flagged in the run that filled
this folder.

## What the run found

| | |
|---|---|
| Parts fetched | 2,900 of 2,900 — none missing from the source |
| Real cards | 2,849 |
| Confirmed (number **and** shipping name agree) | 2,703 |
| Probable (number verified, name too abbreviated to match) | 146 |
| Contradictory or misread | 0 |
| Out of sequence | 0 |
| Blank templates, discarded | 51 (parts 2850-2900) |
| Unique UN numbers | 2,336 |

The 513 extra cards beyond 2,336 are second and third cards for the same UN
number, which the regulations give a separate entry per packing group; they are
named `un_2031-2.pdf`, `un_2031-3.pdf` and so on, and all of them are handed to
the user.

The tail of the source, parts 2850 to 2900, are the card layout with every field
empty. They carry no substance and were discarded; `manifest.json` still records
that they were seen.

That the 2,336 unique UN numbers match the 2,336 unique numbers in
`backend/seed/dg/un_numbers.json` exactly is a good sign that nothing was missed.

## What they are used for

At the end of the wizard, a shipment with dangerous goods can download the cards
for **the substances it declared** — not the whole library. See
[docs/dangerous-goods.md](../docs/dangerous-goods.md#un-cards).

The cards are reference material for the user's own records. They are not
transport documents and they do not replace the current edition of ADR, RID, ADN,
the IMDG Code or the IATA DGR.
