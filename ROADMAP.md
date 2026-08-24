# Roadmap

Where CargoPilot is going. For what has already shipped, see the [changelog](CHANGELOG.md);
for the groundwork behind the items below — market findings, measured regulation, open
questions — see [Roadmap research](docs/roadmap-research.md). What several of these
items ask of the database, and what would have to be built before they can land, is set
out in [The database](docs/database-plan.md).

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
| Generated documents | IMO DG Form, VGM, AWB and B/L instructions, ADN document, stowage plan, placarding sheets for ADR, RID, ADN and IMDG, package label sheet with the class labels at full size, packing certificate, on-board document lists, equipment sheet, packing list, delivery note, and the whole shipment as versioned JSON |
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
  single demonstration in v1.117.0 and locked again in v1.118.0. A second route now
  exists and is worth investigating: IATA's own DG AutoCheck service exposes a Connect
  API that validates a declaration against the DGR — the measured-source principle kept,
  with IATA itself as the source (see [Roadmap research](docs/roadmap-research.md)).
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
installation** rather than a fixed answer.

Three levels, ordered by what the server knows about you. Each step up relaxes exactly
one thing:

| | Who gets in | What the server keeps |
|---|---|---|
| **1 — Open** | Anyone, no account | Nothing about anyone |
| **2 — Closed** | The organisation's people, signed in | Accounts and their settings |
| **3 — Kept** | The organisation's people, signed in | Accounts, settings, and the shipments made |

Level 1 to 2 changes who gets in; level 2 to 3 changes what is kept. **Level 2 is what
CargoPilot does today**, which makes it the default and the one level that needs no
migration to reach.

**The level is set at deploy, not in the application.** It is an environment variable
the application reads and cannot write. A privacy promise an administrator can click
away is not a promise — and level 1 has no administrator interface to click it in.

#### Level 1 — Open

A public installation anyone may use to draw up their transport documents without
leaving anything behind. It follows that there are **no accounts at all**: no login
screen, no user table, no password reset, no second factor. What an administrator would
otherwise set is set in the environment at deploy time, and changing it means restarting
the container.

Two things fall away with the accounts, each a consequence rather than an oversight:

- **What would normally be filled in for you lives in your browser**, never on the
  server: consignor address, contact, carrier, loading point, emergency number,
  language — and your signature, which is the only image CargoPilot ever holds. The
  screen has to say this plainly, because "stored in your browser" is a promise about
  where it is *not*, and it goes when the visitor's browser data goes.
- **No equipment library.** It is the one place operational data lives and it is filled
  by an administrator importing a template. With nobody signed in there is no one to own
  it and no one it belongs to.

Two more have to be built rather than declared, and both are about what an anonymous
caller can make the server do.

##### Mail: two switches, not one

Configuring a mail server needs nothing new. `SMTP_HOST` and the seven values beside it
in `backend/app/core/config.py` have been environment settings since v1.141.0, added in
so many words "for installations that would rather configure it in the environment than
in the screen". At level 1 that stops being an alternative and becomes the only way,
because there is no settings screen to configure it in.

What needs deciding is a different question — **may someone who never signed in make the
server send?** — and merging the two is how an installation becomes a spam relay:

- `SMTP_*` says whether the installation can send at all. Wanted at level 1, for the
  operator's own purposes.
- A **separate** switch says whether the export step offers "mail these documents to…"
  to an anonymous visitor. Off by default at every level; at level 1 it is the one that
  carries the risk.

Stated once, so an operator weighs it rather than discovers it: with that second switch
on, anyone can make the installation send mail from its domain, carrying an attachment
whose text they typed, to an address they chose. The cost lands on the sending domain's
reputation. Turning it on therefore comes with a per-recipient and per-caller cap far
below the general limit, one recipient per send, and no way to reach it by accident.

##### Rate limiting: half-built, and the wrong half

`slowapi` is already a dependency and `app.state.limiter` is already wired up in
`main.py` — but all six `@limiter.limit` decorators sit on authentication routes:
sign-in, password reset, the second factor. Level 1 removes exactly those routes.
**Today's limiter protects nothing that level 1 exposes.**

**Both halves are now done, ahead of the levels themselves.** v1.163.4 fixed how the
limits are counted — the limiter was keyed on `request.client.host`, so behind a reverse
proxy every caller shared one bucket; it now reads `X-Forwarded-For` from the right, one
entry per proxy in `TRUSTED_PROXY_COUNT`. v1.164.0 extended them from the six
authentication routes to the eight endpoints that cost something: document rendering, the
bundle, mailing the bundle, UN cards, reading a carrier confirmation, the assistant's
turn and its model download, and address autocomplete. Every limit in the application is
listed in one table in `test_ratelimit_key.py`, so changing one is changing that list.

Nothing about rate limiting is left waiting on level 1. What that level still needs is
everything else on this page.

The in-app limiter is the floor, because it is what actually ships in a one-container
deployment. An edge limiter in front of it stays a recommendation, not an assumption.

#### Level 2 — Closed

Today's behaviour, named. An organisation hosts it, everyone signs in, and the server
keeps accounts, their settings and the equipment library — and nothing about the
shipments themselves. Everything already built assumes this.

#### Level 3 — Kept

Signing in as at level 2, plus the shipments the organisation made. This is what the
storage unlocks:

- **A shipments page.** A table of the shipments made, with filters (cards on mobile), a
  detail view that offers the documents for download again, and an edit action that
  reopens the shipment in the wizard.
- **Departments.** Group users so the page shows the department's work rather than the
  whole organisation's.
- **An address book and templates.** The same five customers, entered once. A product
  decision, not a technical one: it earns its place when the same consignment is drawn
  up repeatedly.

#### Going down a level destroys data, and says so first

Moving from 3 to 2 means the stored shipments have to go. Keeping the table while the
interface claims it does not exist is the one outcome worse than either level. But the
level is a deploy-time variable, so there is no screen to confirm it on — so the
application **refuses to start**: it reports how many shipments it found and names the
second variable the operator must set to discard them. Refusing to start is loud, and it
destroys nothing by default.

#### One combination is deliberately not offered

No login *with* a shipment history. This roadmap used to describe turning the login page
off as the **strictest** setting — an installation on a closed network, where the network
is the boundary. That is a different argument altogether: safe because nobody untrusted
can reach it, rather than safe because nothing is kept. Putting both on one ladder would
produce an installation that records who shipped what while having no idea who typed it.

#### Order of operations, fixed by principle

Levels first, storage second, page third. There must never be a version that stores
without the control. And the levels are enforced in code with tests, the way
`purge_sensitive_data` already enforces today's promise rather than merely describing
it: at level 1 the authentication endpoints do not exist, at levels 1 and 2 the shipment
endpoints do not exist. [Privacy](docs/privacy.md) becomes a document with three answers
instead of one.

### Interface

- **Branding.** An admin sets the organisation's own name and logo, and can replace the
  transport-mode images, so the application looks like the company using it.

(Toasts and snackbars as the one notification mechanism shipped in v1.153.0 —
transient messages became toasts, deletes gained a six-second undo, and the two
confirmations that remained deliberate — clearing someone's second factor,
applying an update — became the application's own dialogs. Field validation,
sign-in errors and regulatory findings stay inline by design.)

### Plugins and an open ecosystem

- **A plugin page** in the application to manage what is installed.
- **A licence change** to MIT or similar, so plugins can be written, shared and
  installed freely. (CargoPilot is Apache 2.0 today, which already permits all three;
  the change is about how open the project *reads* to a first-time contributor.)
- **A community hub** — a website where people share plugins, loadable inside the
  application so a plugin installs directly from it. The companion modules above will
  be published there, the military one excepted. Visible to every user; only admins
  can install.

### Installing it without Docker

CargoPilot ships as a container and assumes one: a single image, a Docker
Compose file and an Unraid template, with the in-app updater pulling a newer
image over the Docker socket. That is the right default and it stays — but it
is currently also the *only* way in, which rules out anyone who runs services
natively on a Linux host.

Planned, in rough order of usefulness:

- **A native installation on common Linux distributions** — a package or an
  install script that sets up the service, its data directory and a systemd
  unit, so CargoPilot runs like any other service on the box.
- **Kubernetes** — a Helm chart or plain manifests for installations that
  already run a cluster.
- **Docker stays first-class.** It is what the image is built and tested for on
  every release, and nothing below changes that.

One consequence worth naming up front: the in-app updater replaces the running
container through the Docker socket, which is a mechanism a native install does
not have. Each installation method needs its own update route — the package
manager for a native install, the usual rollout for Kubernetes — and the
settings screen should explain the one that applies rather than offering a
button that cannot work.

### Documents and data (researched)

Each of these has a groundwork section in [Roadmap research](docs/roadmap-research.md);
none is committed until it is planned against that brief.

- **Package marks and labels (chapter 5.2).** The class labels and the environmentally
  hazardous mark ship in v1.160.0: what each package carries per regime, and the labels
  themselves at full size, one per A4 page; the **battery mark and the orientation
  arrows** follow in v1.162.0, both measured out of the edition. Column 6 of the Dangerous
  Goods List follows in v1.163.0, which closes the chapter. The **LQ diamond** of 3.4.7
  follows in v1.165.0 — chapter 3.4's mark rather than 5.2's, drawn from the provision's
  words with the one proportion it leaves to the figure measured off the figure. What
  remains there is the Code's own chapter 3.4, whose numbering is not ADR's and which has
  not been read. Placards stay refused, because a laser print is not a placard.
- **Structured shipment export, on the road to eCMR/eFTI.** The versioned JSON export
  ships in v1.161.0 — the whole shipment with its derived findings and the editions
  they were computed against, on every transport mode (see
  [Shipment export](docs/shipment-export.md)). What remains is the mapping onto the
  UN/CEFACT multimodal model the EU eFTI regulation builds on (in full force 9 July
  2027), which needs the published model read first, and the per-party signature flow.
  CargoPilot does not become a certified platform; it becomes trivially connectable
  to one.
- **DGSA annual report.** The statistical half of the ADR 1.8.3 adviser's report,
  generated from stored shipments — so it exists only at privacy level 3, because
  without stored shipments there is nothing to report.
- **Own articles library.** The company's article codes linked to UN number,
  technical name and default packaging — entered once, reused every shipment; designed
  together with the address book.
- **EDI (IFTDGN) and the port call.** The freely specified UN/EDIFACT dangerous goods
  notification as a far-off target the structured export quietly prepares for.
- **Groupage.** Several consignments on one vehicle with the 1.1.3.6 count and mixed
  loading checked over the whole.
- **Return shipments in one click.** Empty uncleaned packagings back to the filler —
  parties swapped, the 5.4.1.1.6 description applied.
- **A QR code on documents** linking to the shipment's UN cards on the own server.

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
