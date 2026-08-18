# Roadmap

Where CargoPilot is going. For what has already shipped, see the [changelog](CHANGELOG.md).

Versioning follows [Semantic Versioning](https://semver.org/) — see
[Development](docs/development.md#versioning) for how bumps are decided.

## Status

CargoPilot is **under active development**. It is usable today: the current release
covers the full flow from package entry to finished documents for **road and inland
waterway** transport. Rail, sea, air and multimodal are built in and reachable in the
code, but their tiles are locked until their remaining regulatory checks are complete
(air is temporarily unlocked for demonstration; see below) —
a half-right document is worse than none, because it gets signed and handed over. The
gaps that keep them locked are listed per mode in [DG coverage](docs/dg-coverage.md).

Expect additions rather than upheaval — the wizard and the document registry are settled.

## Where it stands now

| Area | State |
|---|---|
| Transport modes | Road and inland waterway released; air temporarily unlocked for demonstration with its quantity gap open; rail, sea and multimodal built but locked pending their remaining checks |
| Official forms filled in | CMR, CIM, IATA Shipper's Declaration, AVC waybill |
| Generated documents | IMO DG Form, VGM, AWB and B/L instructions, ADN document, stowage plan, placarding sheet, packing certificate, on-board document lists, equipment sheet, packing list, delivery note |
| AI assistant | Optional survey-style assistant over the whole wizard; works without any model, and an admin can install a pinned local model (Qwen3-1.7B via llama.cpp) that only reads — it never decides regulatory content |
| Goods database | 1,093 goods with densities and NL/EN/DE/FR names |
| Dangerous goods | 2,336 UN numbers over 2,928 Table A rows, 2,338 EmS schedules, full IMDG segregation, ADR/RID/ADN and IATA compliance checks |
| Per-substance IMDG data | Marine pollutant, stowage (SW) and segregation (SG) codes for 2,336 UN numbers |
| UN cards | 2,849 reference cards, downloadable per shipment |
| Locations | 4,500+ airports, 17,500+ ports, 750+ stations, offline |
| Interface | Dutch, English, German and French, light and dark |
| Settings | Per user: language, theme, default transport mode and unit, consignor details, emergency number, saved signature. Per installation, admin only: outbound connections, session lifetime, defaults for new users, the assistant's model |

## Planned

### Releasing the locked transport modes

Rail, sea, air and multimodal each leave the lock when their known gaps are closed and
their document flows have been verified end to end — the same bar inland waterway
cleared in v1.63.0. The work per mode is what [DG coverage](docs/dg-coverage.md) names:

- **Rail (RID)** — the remaining RID-specific checks and the CIM flow verified end to end.
- **Sea (IMDG)** — the remaining IMDG document checks around the IMO form, VGM and
  shipping instructions.
- **Air (IATA DGR)** — the IATA quantity tables, so the Q value no longer depends on a
  user-entered M and the passenger/cargo-aircraft limit can be derived. *Temporarily
  unlocked for demonstration:* the declaration and segregation are sound and the
  application states on screen and on the document when the Q check could not run, but
  the quantity side is not verified. To lock it again, remove `DEMO_UNLOCKED_MODALITIES`
  in `frontend/src/pages/ModalitySelectPage.tsx`.
- **Multimodal** — unlocks last, since it is the union of the other modes' documents.

### Update experience

- **A "what's new" dialog after an update.** The first start after an update shows the
  changelog entries new since the version last seen, once, dismissible.
- **Checking for updates.** The application periodically compares its own version
  against the latest release and shows an unobtrusive toast when a newer one exists —
  behind the same outbound-connections switch as every other outbound call, so an
  air-gapped installation stays silent.
- **Updating from inside the application.** Trigger the pull of a newer image from the
  settings screen where the installation allows it; where it does not (plain Docker
  without a manager), the same screen explains the Watchtower and Unraid auto-update
  routes instead.

### Companion modules, each in its own repository

Larger capabilities that do not belong inside the core application are planned as
separate projects with their own repositories, talking to CargoPilot over its API. The
core stays what it is — a civilian documentation tool:

- **Route planner** — plan the journey the documents describe, with mode-aware
  restrictions (tunnel codes, dangerous goods routes).
- **Container handling in 3D** — visual load planning: what goes where in the
  container, weight distribution, segregation shown spatially.
- **Military transport module** — the forms and annexes military movements need. Kept
  strictly outside the civilian core application, in its own repository, precisely
  because the core ships publicly and starts empty of any operational data.

### Wizard and library

- NHM code search and selection as a master data field (CIM box 24). Blocked on finding a
  source that carries six-digit codes *with* descriptions; `scripts/probe_nhm_sources.py`
  measures a candidate. Until then box 24 is a free-text field with a format check.
- Configurable country and carrier rules for customs references (ENS/ICS2, AES/ITN).
- Import of carrier data (AWB number, booking reference) after confirmation.
- Optional bulk export of the equipment library — on request only, never a default
  export of sensitive data.

### Ideas, not committed

- An audit log that records metadata only, never the contents of material lists.

## Not planned

- A pre-filled operational equipment library in the public repository or on Docker Hub.
  The library starts empty by design; see [Privacy](docs/privacy.md).
