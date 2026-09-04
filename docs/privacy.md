# Privacy and data storage

CargoPilot runs on your own machine or server. There is no CargoPilot cloud service, no
account with us, and no telemetry.

## What is stored

Everything persistent lives in the `/data` volume:

| Stored | Why |
|---|---|
| User accounts | Logging in |
| Catalogue reference data | Materials, profiles, locations, UN numbers |
| Catalogue sync status | So startup knows what is current |
| Equipment **you** imported | Your own library |
| Your settings | Language, theme, the details you asked to have filled in for you, and which version's release notes you have already seen |
| The installation's settings | What an administrator set for everyone |

That is the whole list.

Settings are stored per account, so they follow you to a second device rather than staying
behind in one browser. They hold what you chose to put there: your consignor name and
address, a contact, a carrier, a loading point, an emergency number — and, if you draw one,
**your signature**. That last one is worth naming explicitly, because it is the only image
CargoPilot keeps. It is saved only when you draw or upload it on the settings screen,
clearing it removes it, and it never leaves your server. If you would rather not keep one,
leave that section on "skip" and sign the printed documents with a pen.

## What is deliberately not stored

- **No shipment history.** Once you close a shipment, its package lines are gone.
- **No job database with material lists.** Nothing is written down while you work.
- **No document archive.** Exports are written to a temporary file, streamed to your
  browser and deleted immediately afterwards.
- **No operational equipment data in the repository or the Docker image.** The equipment
  library starts empty; an administrator fills it by importing a template.
- **No trips.** The groupage screen assembles several consignments into one load, judges
  them together and forgets them. There is no trip id, no history and nothing to
  retrieve; reloading the page clears it. A trip is a calculation, not a record.

This is a deliberate choice. If a job is finished, there is nothing left to leak.

## What leaves your server

Six things, and only if you let them:

**Address autocomplete** sends what you type in an address field to a Photon geocoder
(`photon.komoot.io` by default). An administrator can switch it off entirely on the
settings screen, point `GEO_ADDRESS_API_URL` at their own instance, or you can simply not
use the suggestions — typing by hand always works. The assistant's address questions go
through the very same switch.

**Catalogue sync** fetches public reference data (steel profiles, material densities) at
startup. Switch it off on the settings screen or with `CATALOG_AUTO_SYNC=false`.

**The update check** asks GitHub's public release listing whether a newer CargoPilot
exists, only while an administrator is signed in, and sends nothing but the request
itself. Switch it off on the settings screen or with `UPDATE_CHECK_ENABLED=false`;
off means CargoPilot never asks. Either way the application cannot update itself —
the answer only tells the administrator there is something to pull.

**The assistant's model download** happens once, only when an administrator clicks
*install* on the settings screen: the pinned llama.cpp build and the Qwen3 model file
are fetched into `/data/assistant` and verified against SHA-256 digests recorded in the
repository. Nothing about your shipments is ever sent — the download is the only
traffic, and after it the assistant runs entirely locally. Never installing it is the
default, and the assistant works without it.

**The in-app update** pulls the newer CargoPilot image from Docker Hub, and only
when an administrator presses the update button — which only exists where the
operator explicitly enabled applying updates (`UPDATE_APPLY_ENABLED` plus a mounted
Docker socket, see [Configuration](configuration.md#updating-from-inside-the-application)).
Off by default; nothing about your shipments travels with the pull.

**The UN card download** happens only when an administrator clicks *check* or
*download* under **Settings → UN Cards**: the server asks GitHub's public release
listing for the newest `un-cards-` release of this repository and, on download, fetches
the card package from it — never from a caller-supplied address. Every file is verified
against the SHA-256 digests in the packaged manifest before it is installed. An
installation without outbound access imports the same package as an uploaded ZIP
instead, with identical verification, so this connection is never required.

The switches sit together under **Outbound connections** in the administrator section of
the settings screen, so an air-gapped installation can be made silent from one place.

Airport, port, station, UN number and packaging lookups are all local. Nothing about
your shipment ever goes anywhere.

## What a stranger can reach

One thing, and only if you switch it on.

**The QR code on transport documents** (**Settings → QR code with UN cards on
documents**, off by default) prints a code on every document that opens a page of UN
cards. That page is the only one in CargoPilot that does not ask for a sign-in, and
deliberately so: the people it is for — the driver at the roadside, the warehouse taking
the pallet in, the responder who arrived because something went wrong — have no account
here, and a code that asks them to log in is a code that does nothing.

What the code carries is the UN numbers and the regime, and nothing else. No consignor,
no consignee, no quantity, no reference, no shipment identifier — there is no shipment to
look up, because CargoPilot stores none. The document that carries the code already
prints those same UN numbers in plain text and larger, so the code discloses nothing the
paper in the reader's hand does not already say.

The page behind it answers with two things per number: the number, and whether this
installation holds a card for it. A missing card is reported missing rather than left
out, because somebody standing at a vehicle needs to know a card is absent instead of
being handed a shorter list and left to assume it was complete. A card is never
substituted from another regime — ADR and IMDG print different obligations.

Because it is public it is also the narrowest thing in the application: it is off until
an administrator turns it on, it needs the installation's public address configured
before a single code is printed, it answers about at most thirty UN numbers per link, and
it is rate limited to thirty requests a minute per caller. With the switch off the route
answers 404 rather than 403 — an installation that has not opened this door does not owe
a stranger the information that the door exists.

There is nothing here to expire. The link addresses a UN number, not a consignment, so a
code scanned in a year answers exactly what it answered on the day it was printed.

## What this page will become

Everything above describes the one answer CargoPilot has today: sign in, and the server
keeps your account, your settings and your equipment library — never your shipments. The
[roadmap](../ROADMAP.md) turns that into a choice per installation, set at deploy time
rather than in the interface: two modes, **Open** (anyone, no account, nothing kept
about anyone) and **Organisation** (signed in, accounts and settings kept), and within
Organisation one feature, the **shipment history**, that keeps the shipments as well.
Today's behaviour is Organisation without history, which is why nothing here changes
for an existing installation. Until the modes ship, this page has one answer and it is
the one printed above.

## Older Docker images

> [!WARNING]
> Docker images older than **v1.4.0** still contain an internal form that is not intended
> for civilian use.

1. Use `v1.4.0` or newer.
2. Remove old tags on Docker Hub: GitHub → **Actions** → **Cleanup Docker Hub tags** →
   **Run workflow**, with `keep_tags`: `latest,v1.33.0,1.33.0`.
3. `docker pull jeffersonmouze/cargopilot:latest` and restart the container.

On upgrade to v1.0.0 or later, any legacy items with the source `overzicht_materieel` are
removed from an existing database automatically.
