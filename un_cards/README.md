# UN cards

One reference card per UN number, named after the number it describes:
`un_1203.pdf`, `un_3480.pdf`, and so on. When a UN number has more than one card,
the extras are suffixed: `un_1203-2.pdf`.

This folder is **empty in a fresh checkout**. It is filled once by the
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
of sequence even when it read cleanly.

## What they are used for

At the end of the wizard, a shipment with dangerous goods can download the cards
for **the substances it declared** — not the whole library. See
[docs/dangerous-goods.md](../docs/dangerous-goods.md#un-cards).

The cards are reference material for the user's own records. They are not
transport documents and they do not replace the current edition of ADR, RID, ADN,
the IMDG Code or the IATA DGR.
