# Roadmap

Where CargoPilot is going. For what has already shipped, see the [changelog](CHANGELOG.md).

Versioning follows [Semantic Versioning](https://semver.org/) — see
[Development](docs/development.md#versioning) for how bumps are decided.

## Status

CargoPilot is **under active development**. It is usable today, and the current
release covers the full flow from package entry to finished documents for all six
transport modes. Expect additions rather than upheaval — the wizard and the document
registry are settled.

## Where it stands now

| Area | State |
|---|---|
| Transport modes | Road, rail, sea, inland waterway, air, multimodal |
| Official forms filled in | CMR, CIM, IATA Shipper's Declaration, AVC waybill |
| Generated documents | IMO DG Form, VGM, AWB and B/L instructions, ADN document, packing list, delivery note |
| Goods database | 400 goods with densities and NL/EN aliases |
| Dangerous goods | 2,928 UN entries, 2,338 EmS schedules, full IMDG segregation, ADR and IATA compliance checks |
| Locations | 4,500+ airports, 17,500+ ports, 750+ stations, offline |
| Interface | Dutch and English, light and dark |

## Planned

### Dangerous goods data

- **Per-substance data from the IMDG Dangerous Goods List**: marine pollutant status,
  stowage codes (SW, column 16a), segregation codes (SG, column 16b) and bulk/tank
  admissibility. Today the app knows the segregation *groups* per substance but points
  at column 16b for the substance-specific codes.
- German as a third interface language, including the dangerous goods help texts.

### Wizard and library

- Column mapping UI when an imported spreadsheet has ambiguous headers.
- NHM code search and selection as a master data field (CIM box 24).
- Configurable country and carrier rules for customs references (ENS/ICS2, AES/ITN).
- Import of carrier data (AWB number, booking reference) after confirmation.
- Optional bulk export of the equipment library — on request only, never a default
  export of sensitive data.

### Ideas, not committed

- Watchtower and Unraid auto-update documentation.
- An audit log that records metadata only, never the contents of material lists.

## Not planned

- A pre-filled operational equipment library in the public repository or on Docker Hub.
  The library starts empty by design; see [Privacy](docs/privacy.md).
