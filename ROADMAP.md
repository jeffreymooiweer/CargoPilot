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

### Two modes, and one feature only the second has

Today the application writes nothing down while you work: there is no job database, and
a finished job leaves nothing to leak (see [Privacy](docs/privacy.md)). That is right
for a shipper handling sensitive material lists and wrong for an office where five
colleagues serve the same customers every day. So it becomes a **choice per
installation** rather than a fixed answer.

This section used to describe three "privacy levels" on one ladder. The ladder encoded
two questions that are not the same kind of question — *who gets in* and *what is
kept* — and it made a stored shipment history sound like a step *down* in privacy, when
it is a function an organisation switches on for itself. Restated:

| | **Open** | **Organisation** | **Organisation, with history** |
|---|---|---|---|
| Who gets in | Anyone, no account | The organisation's people, signed in | The same |
| Accounts, roles, second factor | — | yes | yes |
| Your defaults: consignor, signature, language… | in your browser | on the server | on the server |
| Equipment library, mail, branding, in-app update | — | yes | yes |
| Shipments page, reopen, return from history | — | — | yes |
| Groupage from kept shipments, departments, address book, DGSA report | — | — | yes |

**The mode is a deployment, not a setting.** Open and Organisation are two applications
in one image: the first has no login routes, no user table, no password reset and no
second factor, and the tests assert their absence rather than a redirect. An environment
variable the application reads and cannot write selects the mode. Unset means
Organisation, because that is what every existing installation is.

**History is a feature of Organisation, not a third mode.** It is set in the environment
too — not because an administrator cannot be trusted with it, but because turning it
*off* destroys data, and a deploy-time variable is the one place the application can
refuse to start instead of asking on a screen (below). It never exists without an
account in front of it: a record of what was shipped with no record of who typed it is
the one combination this page does not offer.

**Two independent pieces of work, on either side of today.** Organisation is what
CargoPilot does now. Open is *removing* from it; history is *adding* to it. Neither
waits on the other, and Open can ship with history never built.

#### Open — shipped in v1.171.0

`CARGOPILOT_MODE=open`, built as this section promised. The account routes are not
mounted — sign-in, users, the settings screen, the equipment library, mail, the
administrator's maintenance — and the test suite asserts their absence route by route.
The defaults live in the visitor's browser and the settings screen says so in four
languages. There is no mail whatever `SMTP_*` says, and no saved settings row is read:
the environment is the whole configuration, so the switches an administrator would
otherwise flip on the screen gained environment names (`ADDRESS_LOOKUP_ENABLED`,
`UN_CARDS_ENABLED`, `CARD_LINKS_ENABLED`, `PUBLIC_URL`, `DEFAULT_LANGUAGE`,
`DEFAULT_THEME`). And the promise is checkable rather than merely true: `/api/health`
and the footer both say which application answers, and [Privacy](docs/privacy.md) has
the section a visitor reads. Rate limiting was already in place (v1.163.4, v1.164.0).

#### Organisation

Today's behaviour, named. An organisation hosts it, everyone signs in, and the server
keeps accounts, their settings and the equipment library — and nothing about the
shipments themselves. Everything already built assumes this, which is why it is the
default and the one mode that needs no migration to reach.

#### History

The shipments the organisation made, kept. This is what the storage unlocks:

- **A shipments page.** A table of the shipments made, with filters (cards on mobile), a
  detail view that offers the documents for download again, and an edit action that
  reopens the shipment in the wizard.
- **Departments.** Group users so the page shows the department's work rather than the
  whole organisation's.
- **An address book and templates.** The same five customers, entered once. A product
  decision, not a technical one: it earns its place when the same consignment is drawn
  up repeatedly.
- **Groupage from the history.** Today the consignments of a trip come in as export
  files, because there is nothing to pick from. With a history, a trip is assembled from
  kept shipments instead. Whether the trip itself — the judgement over the whole load —
  is kept as well is an open question for this phase, not a decision already taken.
- **The DGSA annual report**, which is a statistic over the history and needs it to
  exist.

#### Turning history off destroys data, and says so first

Switching history off means the stored shipments have to go. Keeping the table while the
interface claims it does not exist is the one outcome worse than either choice. But the
switch is a deploy-time variable, so there is no screen to confirm it on — so the
application **refuses to start**: it reports how many shipments it found and names the
second variable the operator must set to discard them. Refusing to start is loud, and it
destroys nothing by default.

#### Order of operations, fixed by principle

Mode first, storage second, page third. There must never be a version that stores
without the control. And both are enforced in code with tests, the way
`purge_sensitive_data` already enforces today's promise rather than merely describing
it: at Open the authentication endpoints do not exist, and without history the shipment
endpoints do not exist. [Privacy](docs/privacy.md) becomes a document with three answers
instead of one.

### Interface

- **Branding** shipped in v1.172.0: an administrator sets the installation's own name,
  uploads a logo and a picture per transport mode, and the header, the sign-in page, the
  browser tab, the tiles and outgoing mail follow. The open application takes the same
  files from `DATA_DIR/branding` and the name from `BRAND_NAME`.

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
  words with the one proportion it leaves to the figure measured off the figure. The
  Code's own chapter 3.4 was read in v1.170.0 from the registered edition: the same
  diamond under the sea's own numbers (3.4.5.1), with the two duties the land does not
  have — "LTD QTY" on the transport document (3.4.6.1) and a unit mark with no tonnage
  condition (3.4.5.5). Placards stay refused, because a laser print is not a placard.
- **Structured shipment export, on the road to eCMR/eFTI.** The versioned JSON export
  ships in v1.161.0 — the whole shipment with its derived findings and the editions
  they were computed against, on every transport mode (see
  [Shipment export](docs/shipment-export.md)). What remains is the mapping onto the
  UN/CEFACT multimodal model the EU eFTI regulation builds on (in full force 9 July
  2027), which needs the published model read first, and the per-party signature flow.
  CargoPilot does not become a certified platform; it becomes trivially connectable
  to one.
- **DGSA annual report.** The statistical half of the ADR 1.8.3 adviser's report,
  generated from stored shipments — so it exists only with the history switched on,
  because without stored shipments there is nothing to report.
- **Own articles library.** The company's article codes linked to UN number,
  technical name and default packaging — entered once, reused every shipment; designed
  together with the address book.
- **EDI (IFTDGN) and the port call.** The freely specified UN/EDIFACT dangerous goods
  notification as a far-off target the structured export quietly prepares for.
- **Groupage** shipped in v1.169.0: several consignments on one vehicle, judged as one
  load. Three provisions are decided per transport unit and could not be decided per
  consignment however carefully each was filled in — the 1.1.3.6 points, the mixed
  loading of 7.5.2, and the limited-quantities marking of 3.4.13/3.4.14. The headline
  finding is the one no per-consignment screen can produce: every consignment exempt,
  the vehicle not. Consignments come in as the shipment exports of v1.161.0, because
  there is no stored history to pick from and inventing one would break the privacy
  stance; the trip itself is a calculation and is not stored today. The design question
  the research recorded — trip as entity or as transient calculation — was answered for
  today by the fact that nothing is kept. An installation with a history reopens it:
  whether that installation keeps the trip as well is that phase's question (see
  *History* above).
- **Return shipments in one click** shipped in v1.167.0: the export step turns the
  consignment round — parties swapped, every line set to empty uncleaned, and every
  quantity the outward journey stated cleared, because on an empty drum each of them is a
  number that is not true. The 5.4.1.1.6.1 description was already built; what the item
  turned out to need first was ADR **1.1.3.6.1**, whose reassignment of an empty uncleaned
  packaging to transport category 4 the points check was not making (v1.166.0).
- **A QR code on documents** shipped in v1.168.0: every rendered transport document can
  carry a code that opens this installation's UN cards for the UN numbers on that
  document. It is the first and only route in CargoPilot that answers without a sign-in,
  which is the whole point — the driver at the roadside and the responder on the scene
  have no account here. Off until an administrator turns it on, and it needs the
  installation's public address configured before a single code is printed: a code on
  paper that leads nowhere is worse than no code, because whoever holds the paper cannot
  tell the difference. The research item's open question — link lifetime on an
  installation that stores nothing — turned out not to arise: the link addresses UN
  numbers, not a consignment, so there is nothing to expire.

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
