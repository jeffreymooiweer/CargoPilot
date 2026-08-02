# UN cards

One reference card per UN number, named after the number it describes:
`un_1203.pdf`, `un_3480.pdf`, and so on. When a UN number has more than one card,
the extras are suffixed: `un_1203-2.pdf`.

This folder is **empty in a fresh checkout**. It is filled once by the
**Fetch UN cards** workflow (`.github/workflows/fetch-un-cards.yml`), which
downloads the source documents, reads the UN number out of each one and renames
it accordingly — the source files are numbered sequentially (`part1`, `part2`, …)
with no relation to their contents, so the filename cannot be trusted.

`manifest.json` records what happened to every part: which UN number it was
identified as, how confident that was, and which of our known shipping names it
matched. Documents that could not be identified are parked in `_unidentified/`
rather than filed under a guess.

## What they are used for

At the end of the wizard, a shipment with dangerous goods can download the cards
for **the substances it declared** — not the whole library. See
[docs/dangerous-goods.md](../docs/dangerous-goods.md#un-cards).

The cards are reference material for the user's own records. They are not
transport documents and they do not replace the current edition of ADR, RID, ADN,
the IMDG Code or the IATA DGR.
