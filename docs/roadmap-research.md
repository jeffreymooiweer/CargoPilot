# Roadmap research

*Groundwork for the items on the [roadmap](../ROADMAP.md) — deliberately not a plan.
Each section records what was found out about a subject before anyone commits to
building it: what the market does, what the regulation says (measured where it could
be), what already exists in this repository, and which questions a future plan has to
answer. Verified facts are cited; anything not yet verified says so.*

*Researched August 2026. Market claims age; regulation quotes carry their source.*

---

## Package marks and labels (new)

**The idea.** CargoPilot refuses to print placards, and rightly — a laser print is not
a placard. The marks and labels **on the package** of chapter 5.2 are different: they
are routinely printed on A4 sticker sheets in practice, and the application already
knows per substance which label models and marks apply. This is the clearest gap
against the commercial tools (Labelmaster, DGOffice and Brady all sell label printing).

**Measured from ADR 2025** (`read_land_regulations.py`, volume II pages 237–252 and
volume I page 664):

| Mark | Provision | Measured requirement |
|---|---|---|
| Class/division label | 5.2.2.2.1.1 | Diamond 100 × 100 mm minimum, inner line ~5 mm from the edge; reducible proportionally if the package size so requires; cylinders per ISO 7225 |
| Limited quantities mark | 3.4.7 | Diamond 100 × 100 mm, line 2 mm; reducible to 50 × 50 mm with a 1 mm line |
| Environmentally hazardous mark | 5.2.1.8.3 | Diamond 100 × 100 mm, line 2 mm, fish-and-tree black on white; reducible if the package so requires |
| Battery mark | 5.2.1.9 | Rectangle 100 × 100 mm minimum with 5 mm red hatched edging, UN number(s) under the symbol |
| Orientation arrows | 5.2.1.10 | Two opposite vertical sides, arrows per the figure or ISO 780:1997; a measured list of exemptions (pressure receptacles, inners ≤ 120 ml with absorbent, hermetic inners ≤ 500 ml, …) |

**Still to measure at build time:** 5.2.1.1 (the UN number and PSN marking on the
package, including the character-height rule tied to package size) — the quote run
missed it and nothing here should be built from memory. The IMDG and RID/ADN
counterparts of each mark must be read as well; the sea chapter is readable since
v1.150.0.

**What a plan must settle:** true-size rendering on A4 (two 100 × 100 diamonds per
sheet with cut marks, or standard die-cut sticker formats); whether the sheet prints
labels *only* where the check says they apply (it should — a sheet of unneeded labels
invites mislabelling); and the same honesty note the placarding sheet carries, since
5.2.2.1.6 also has visibility/durability demands paper cannot promise.

## Structured export, eCMR and eFTI (new)

**The regulatory wave, verified against multiple sources:** the EU
[eFTI Regulation](https://transport.ec.europa.eu/transport-themes/logistics-and-multimodal-transport/efti-regulation_en)
applies in full from **9 July 2027** — from then, authorities must accept freight
information electronically via certified eFTI platforms. The certification framework
is being finalised through 2026, [Spain mandates digital consignment notes from
October 2026](https://trans.info/en/ecmr-in-2026-434860), and
[39 countries have acceded to the eCMR protocol](https://www.transbook.onl/Transbook/Digitalization)
while under 1 % of European road shipments actually use it yet. Paper remains legal —
consignors are not obliged to switch.

**The technical anchor:** the eFTI data set is built on the **UN/CEFACT Multi-Modal
Transport reference data model (MMT-RDM)**, and eCMR is being aligned to it
([eFTI4ALL](https://efti4all.eu/odette-2025-ecmr-efti-fit-together/)). That is the
model to map CargoPilot's fields against — once, in a document, before any code.

**What CargoPilot should and should not become:** not an eFTI platform (that is a
certification regime for platform providers), but a system whose every shipment can
leave as structured data so that a certified platform, or a plugin talking to one, can
take it from there. The per-party signature flow (consignor, carrier, consignee — the
application already stores one signature per user) is the second half; qualified
electronic signatures are a legal-weight question for the plan.

**First concrete step when planned:** a versioned JSON export of a complete shipment
(values + lines + dangerous goods + derived findings), documented as an API response.
Everything else — MMT-RDM mapping, eCMR pilots, platform connectors — builds on that.

## DGSA annual report (new)

ADR 1.8.3 obliges every undertaking that consigns or carries dangerous goods to
appoint a safety adviser, and 1.8.3.3 obliges that adviser to produce an **annual
report**, kept five years ([overview](https://app.croneri.co.uk/feature-articles/dangerous-goods-safety-adviser-dgsa-requirements),
[EASA template](https://www.badgp.org/dgsa-annual-report)). The report's statistical
half — what was shipped, which classes, which quantities, which incidents — is exactly
what a shipments store can aggregate.

**Dependency, hard:** this requires the shipments page and therefore the privacy
levels. Without stored shipments there is nothing to report, and that is today's
deliberate state. **When planned:** take the EASA template as the outline, generate
the counts CargoPilot can prove, and leave the adviser's judgement sections
(assessments, recommendations) as prompts — a generated opinion would be worse than a
blank.

## Own articles library (new)

DGOffice links a company's own article codes to UN numbers so one code fills the whole
document. CargoPilot holds the pieces already: the goods catalogue (1,093 goods), the
equipment library, and per-substance classification. The missing layer is
*"our article X = UN 1263, PG II, technical name Y, default packaging Z"* — entered
once, reused every shipment. Same restriction-level gating as the address book, and
worth designing together with it: both are "master data the office reuses".

## EDI and the port call (new)

[Hazcheck](https://hazcheck.com/product/hazcheck-workstation/) produces a Dangerous
Goods Note and attaches an EDI message so the shipping line re-keys nothing. The
message standard is **UN/EDIFACT IFTDGN** (dangerous goods notification), publicly
specified by [UNECE](https://service.unece.org/trade/untdid/d16a/trmd/iftdgn_c.htm)
and used by port community systems. Far off, and only worth doing against a real
counterparty — but the structured export above is deliberately its first half, and
the IFTDGN spec is free, so nothing blocks reading it early.

## Groupage, returns, QR (new, smaller)

- **Groupage:** several consignments on one vehicle, with the 1.1.3.6 count and the
  mixed-loading checks over the whole. Everything exists per consignment; the missing
  thing is the level above. The open design question is whether a "trip" becomes an
  entity (which touches the privacy stance) or a transient calculation.
- **Return shipments:** empty uncleaned packagings back to the filler is a one-click
  scenario — swap parties, set `empty_uncleaned`, description per 5.4.1.1.6. No
  research needed; noted so it is not forgotten.
- **QR code on documents:** linking to the shipment's UN cards on the own server.
  Self-contained, no third party. The open question is link lifetime on an
  installation that deliberately stores nothing.

## Route planner (existing item, deepened)

Self-hostable open-source engines exist with dangerous-goods awareness:
[openrouteservice](https://github.com/giscience/openrouteservice) evaluates **tunnel
categories B–E** through a `hazmat` flag on its HGV profile, and
[GraphHopper's custom models](https://www.graphhopper.com/blog/2020/05/31/examples-for-customizable-routing/)
can exclude `hazmat=no` roads and `hazmat_tunnel` categories. Both run from
OpenStreetMap data.

**The honest caveat, from the same sources:** hazmat tagging in OSM — especially
`hazmat_tunnel` — is sparse. A route that *silently* misses an untagged tunnel is the
half-right-document problem in map form. A plan must treat OSM coverage measurement
(for the operator's actual region) as step one, and the module's output as advisory
with the tunnel code of the load printed beside it — the code CargoPilot already
derives. ADR 1.9.5 keeps route choice with the carrier; the module plans, it does not
authorise.

## Container handling in 3D (existing item, deepened)

Open-source foundations exist: [xflp](https://github.com/hschneid/xflp) (Java) solves
truck loading with real-world constraints **including permissible axle load**;
[3DContainerPacking](https://github.com/davidmchapman/3DContainerPacking) (C#)
implements the EB-AFIT algorithm; Python implementations exist but are thinner. The
commercial benchmark ([EasyCargo](https://www.easycargo3d.com/en/),
[3DPACK.ING](https://3dpack.ing/)) draws the **centre of gravity live** and accounts
for weight in placement.

**What nobody in that market has:** segregation. CargoPilot derives IMDG/ADR
segregation per pair of substances; drawing it spatially (these two drums may not
share this container, that one must be 2.4 m away) is the differentiator. **When
planned:** decide build-vs-wrap (a TS/WebGL front over an own solver, versus porting
xflp's constraint model), and take axle load and CoG in from day one — they pair with
the VGM the application already computes.

## Container fleet management (existing item, deepened)

The depot/M&R world ([MRI Intermodal](https://www.mriintermodal.com/solutions/depot-management-software/),
[WHIZTEC](https://www.whiztec.com/container-depot-software/)) is built around:
gate-in/gate-out with **EIR** (equipment interchange receipt, photos, damage remarks),
damage estimates against customer tariffs, M&R workflow (estimate → approval → work
order → QC → billing), stack/yard planning, and **CODECO** EDI reporting to lines.
For a park owner rather than a depot operator the useful core is smaller: which box,
where, in what condition, inspection dates (CSC plate), and hand-over evidence.
**Open question for the plan:** who is the user — own park, or depot service for
third parties? The second pulls in tariffs and billing, which is a different product.

## Vessel design (existing item, noted)

The thinnest-researched module, deliberately: naval architecture tooling (hydrostatics,
stability) is a specialist field with certification implications, and nothing in the
documentation-tool DNA transfers. If it proceeds, scope it first to *data* the other
modules need (hold dimensions, tank layouts as input to stowage) rather than to design
calculations that would carry liability.

## Military module MOD-NL (existing item, boundary noted)

Kept out of the public core and off the public hub, as the roadmap says. Groundwork
consists of exactly one public observation: cross-border military movements use forms
that are themselves standardised (e.g. the EU/NATO customs **Form 302**), so the
module's shape — official forms, filled — matches the civilian core's. Anything beyond
that is not for this repository.

## Privacy levels and the shipments page (existing item, internal groundwork)

No web research applies; the groundwork is in this repository. A `Job` table already
exists in the schema and is **deliberately purged at startup** (`purge_sensitive_data`
in `backend/app/core/startup.py`) — the stateless promise of
[Privacy](privacy.md) is enforced in code, not just described. That is the switch a
restriction level would flip. Order of operations is fixed by principle: levels first,
storage second, page third — there must never exist a version that stores without the
control. Departments imply a user–department relation and per-department visibility
filters; both belong in the same design round.

## Toasts and snackbars (existing item, options)

Current mix: inline notices, banners and cards. The React ecosystem's mature options
are `sonner` and `react-hot-toast` (both small, both a11y-conscious); either fits the
stack. The real work is not the library but the sweep: one inventory of every current
notice with a decision — toast, inline (validation belongs at the field), or gone.
Low risk, high visible payoff, no dependencies on anything else.

## Branding (existing item, small design note)

Logo, name, and the transport-mode images as admin uploads. Two things the plan must
not forget: the **mail templates** embed the logo as CID attachment
(`backend/app/services/mail_templates.py`) and must pick up the custom one; and
uploaded images are user content — size caps and format checks at the upload edge,
plus a "reset to default". The four-language interface strings stay; branding does
not mean re-wording.

## Plugins, licence, community hub (existing items, model found)

The pattern to copy is **[HACS](https://hacs.xyz/)** (Home Assistant Community
Store): community code lives in the authors' own GitHub repositories, the store
indexes them, the app installs from the index, and the curated core stays separate.
That model gives CargoPilot: a hub website that is an *index*, not a file host;
admin-only install (already the stated intent); and a natural quality boundary
(regulatory checks stay in core — a plugin must not be able to silently alter what a
document claims, which should be written down as a hard rule in the plugin API design).

**Licence:** Apache 2.0 already permits writing, sharing and installing plugins
freely. The switch to MIT is presentational; the one substantive difference is that
Apache 2.0 carries an explicit patent grant that MIT lacks — worth knowing before
giving it up. No blocker either way.

**Technical shape to evaluate in the plan:** backend plugins as Python entry points
with a declared, versioned API surface; frontend extension points (a route + a menu
slot) rather than arbitrary code injection; a manifest per plugin (name, version,
permissions, core-version compatibility) mirroring HACS.

## Installing without Docker (existing item, routes)

Three routes, in order of reach: a **systemd service** installed by script or native
package (nfpm/fpm build `.deb`/`.rpm` from one spec — to be verified when planned), a
**Helm chart** for Kubernetes, and Docker unchanged. Groundwork observations from
this repository: the backend is a single uvicorn process with `/data` as its one
stateful path, which makes a unit file trivial — but the **in-app updater and the
entrypoint's socket handling are Docker-specific**, and the settings screen must show
the update route that matches the installation method (it already does this for
socket-less Docker). The Python version pin (image ships 3.12) becomes the distro
compatibility question.

## Air, and the one legitimate road to it (existing item, new finding)

The IATA DGR remains unreadable as text. But IATA now sells the *service* rather than
only the book: [DG AutoCheck](https://www.iata.org/en/services/compliance/dg-autocheck)
validates a Shipper's Declaration against the DGR, and its
[Connect API](https://www.iata.org/en/services/compliance/dg-autocheck/dg-autocheck-connect-api/)
exists precisely to let other systems submit and retrieve checks;
[DG Digital](https://www.iata.org/en/pressroom/2026-releases/2026-03-12-01/) (launched
March 2026) digitalises the DGD end-to-end. **This reframes the air unlock:** instead
of needing Table 4.2 as data, CargoPilot could hand the declaration to IATA's own
checker through a paid, operator-supplied API key — the measured-source principle kept,
because the source is IATA itself. To investigate when air is planned: licensing
terms, cost, offline behaviour (an air-gapped installation cannot call out — the
existing outbound-connections switch already models this).

## NHM codes (existing blocker, unchanged)

Still blocked on a source that carries the six-digit codes *with* descriptions;
`scripts/probe_nhm_sources.py` measures any candidate. Nothing new found this round.

---

*Nothing in this document commits to building anything. When an item is picked up, its
section here is the starting brief; the first act of any plan is to re-verify the
external claims, which carry their dates and sources for exactly that reason.*
