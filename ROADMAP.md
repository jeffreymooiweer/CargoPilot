# Roadmap

Where CargoPilot is going. For what has already shipped, see the [changelog](CHANGELOG.md).

Versioning follows [Semantic Versioning](https://semver.org/) — see
[Development](docs/development.md#versioning) for how bumps are decided.

## Status

CargoPilot is **under active development**. It is usable today: the current release
covers the full flow from package entry to finished documents for **road, rail, sea and
inland waterway** transport. Air and multimodal are built in and reachable in the code,
but their tiles are locked until their remaining regulatory checks are complete — a
half-right document is worse than none, because it gets signed and handed over. The
gaps that keep them locked are listed per mode in [DG coverage](docs/dg-coverage.md).

Expect additions rather than upheaval — the wizard and the document registry are settled.

## Where it stands now

| Area | State |
|---|---|
| Transport modes | Road, rail, sea and inland waterway released; air and multimodal built but locked pending their remaining checks |
| Official forms filled in | CMR, CIM, IATA Shipper's Declaration, AVC waybill |
| Generated documents | IMO DG Form, VGM, AWB and B/L instructions, ADN document, stowage plan, placarding sheets for ADR, RID, ADN and IMDG, packing certificate, on-board document lists, equipment sheet, packing list, delivery note |
| AI assistant | Optional survey-style assistant over the whole wizard; works without any model, and an admin can install a pinned local model (Qwen3-1.7B via llama.cpp) that only reads — it never decides regulatory content |
| Goods database | 1,093 goods with densities and NL/EN/DE/FR names |
| Dangerous goods | 2,336 UN numbers over 2,928 Table A rows, 2,338 EmS schedules, full IMDG segregation, ADR/RID/ADN and IATA compliance checks |
| Per-substance IMDG data | Marine pollutant, stowage (SW) and segregation (SG) codes for 2,336 UN numbers |
| UN cards | 2,849 reference cards, downloadable per shipment |
| Locations | 4,500+ airports, 17,500+ ports, 750+ stations, offline |
| Interface | Dutch, English, German and French, light and dark |
| Users and mail | User administration with invitations, password reset, two-factor authentication (authenticator app or emailed code), and a configurable mail server that sends documents and account mail in the recipient's own language |
| Settings | Per user: language, theme, default transport mode and unit, consignor details, emergency number, saved signature, two-factor authentication. Per installation, admin only: outbound connections, session lifetime, defaults for new users, the assistant's model, a mail server, the two-factor policy, in-app updating |

## Planned

### Releasing the locked transport modes

Air and multimodal each leave the lock when their known gaps are closed and their
document flows have been verified end to end — the same bar inland waterway cleared in
v1.63.0, rail in v1.122.0 and sea in v1.152.0 (chapter 5.3 derived from the IMDG Code in
v1.150.0, and the sea flow verified end to end in the sea archetypes, which found two
defects before a real consignment did). The work per mode is what
[DG coverage](docs/dg-coverage.md) names:

- **Air (IATA DGR)** — the IATA quantity tables, so the Q value no longer depends on a
  user-entered M and the passenger/cargo-aircraft limit can be derived. The declaration
  and the segregation checks are already sound, which is why air could be unlocked for a
  single demonstration in v1.117.0 and locked again in v1.118.0.
- **Multimodal** — unlocks last, since it is the union of the other modes' documents.

### Companion modules, each in its own repository

Larger capabilities that do not belong inside the core application are planned as
separate projects with their own repositories, talking to CargoPilot over its API. The
core stays what it is — a civilian documentation tool:

- **Route planner** — plan the journey the documents describe, with mode-aware
  restrictions (tunnel codes, dangerous goods routes).
- **Container handling in 3D** — visual load planning: what goes where in the
  container, weight distribution, segregation shown spatially.
- **Container fleet management** — manage a container park: where each box is, its
  condition, inspection dates, who has it.
- **Vessel design** — design tooling for sea-going and inland vessels.
- **Military transport module (MOD-NL)** — the forms and annexes military movements
  need. Kept strictly outside the civilian core application, in its own repository,
  precisely because the core ships publicly and starts empty of any operational data.
  It is the one module that will not be listed publicly.

### Privacy levels, and what they unlock

Today the application writes nothing down while you work: there is no job database, and
a finished job leaves nothing to leak (see [Privacy](docs/privacy.md)). That is right
for a shipper handling sensitive material lists and wrong for an office where five
colleagues serve the same customers every day. So it becomes a **choice per
installation** rather than a fixed answer, set as a restriction level by the admin.
Everything below is gated on it:

- **A shipments page.** A table of the shipments made in the organisation, with filters
  (cards on mobile), a detail view that offers the documents for download again, and an
  edit action that reopens the shipment in the wizard. Only exists above the strictest
  level, because it means storing what a shipment contained.
- **Departments.** Group users so a shipments page shows the department's work rather
  than the whole organisation's.
- **Turning the login page off.** Only at the highest restriction level — an
  installation on a closed network where the network is the boundary.
- **An address book and templates.** The same five customers, entered once. A product
  decision, not a technical one: it earns its place when the same consignment is drawn
  up repeatedly.

### Interface

- **Toasts and snackbars instead of inline notices.** One notification mechanism across
  the application rather than the current mix of messages, notes and banners — fewer
  things competing for the same space, and a calmer screen.
- **Branding.** An admin sets the organisation's own name and logo, and can replace the
  transport-mode images, so the application looks like the company using it.

### Plugins and an open ecosystem

- **A plugin page** in the application to manage what is installed.
- **A licence change** to MIT or similar, so plugins can be written, shared and
  installed freely. (CargoPilot is Apache 2.0 today, which already permits all three;
  the change is about how open the project *reads* to a first-time contributor.)
- **A community hub** — a website where people share plugins, loadable inside the
  application so a plugin installs directly from it. The companion modules above will
  be published there, the military one excepted. Visible to every user; only admins
  can install.

### Wizard and library

- NHM code search and selection as a master data field (CIM box 24). Blocked on finding a
  source that carries six-digit codes *with* descriptions; `scripts/probe_nhm_sources.py`
  measures a candidate. Until then box 24 is a free-text field with a format check.
- Customs reference fields (ENS/ICS2, AES/ITN) shipped in v1.128.0 with their conditions
  in the help text and their formats enforced on export; carrier data intake (AWB number,
  booking reference) from a pasted booking confirmation shipped alongside. What remains
  open here is deriving the conditions from the route automatically — today the help
  text names the rule and the user decides whether it applies.

### Ideas, not committed

- An audit log that records metadata only, never the contents of material lists.

## Not planned

- A pre-filled operational equipment library in the public repository or on Docker Hub.
  The library starts empty by design; see [Privacy](docs/privacy.md).
