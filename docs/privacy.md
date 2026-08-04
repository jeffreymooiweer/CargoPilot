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

That is the whole list.

## What is deliberately not stored

- **No shipment history.** Once you close a shipment, its package lines are gone.
- **No job database with material lists.** Nothing is written down while you work.
- **No document archive.** Exports are written to a temporary file, streamed to your
  browser and deleted immediately afterwards.
- **No operational equipment data in the repository or the Docker image.** The equipment
  library starts empty; an administrator fills it by importing a template.

This is a deliberate choice. If a job is finished, there is nothing left to leak.

## What leaves your server

Two things, and only if you let them:

**Address autocomplete** sends what you type in an address field to a Photon geocoder
(`photon.komoot.io` by default). Point `GEO_ADDRESS_API_URL` at your own instance, or
simply do not use the suggestions — typing by hand always works.

**Catalogue sync** fetches public reference data (steel profiles, material densities) at
startup. Set `CATALOG_AUTO_SYNC=false` to switch it off.

Airport, port, station, UN number and packaging lookups are all local. Nothing about
your shipment ever goes anywhere.

## Older Docker images

> [!WARNING]
> Docker images older than **v1.4.0** still contain an internal form that is not intended
> for civilian use.

1. Use `v1.4.0` or newer.
2. Remove old tags on Docker Hub: GitHub → **Actions** → **Cleanup Docker Hub tags** →
   **Run workflow**, with `keep_tags`: `latest,v1.29.3,1.29.3`.
3. `docker pull jeffersonmouze/cargopilot:latest` and restart the container.

On upgrade to v1.0.0 or later, any legacy items with the source `overzicht_materieel` are
removed from an existing database automatically.
