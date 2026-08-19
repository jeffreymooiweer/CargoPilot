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

This is a deliberate choice. If a job is finished, there is nothing left to leak.

## What leaves your server

Four things, and only if you let them:

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

The switches sit together under **Outbound connections** in the administrator section of
the settings screen, so an air-gapped installation can be made silent from one place.

Airport, port, station, UN number and packaging lookups are all local. Nothing about
your shipment ever goes anywhere.

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
