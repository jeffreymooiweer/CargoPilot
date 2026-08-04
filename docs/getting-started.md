# Getting started

CargoPilot ships as a single Docker image containing both the backend and the web
interface. There is no separate database to install — it uses a SQLite file on disk.

- [Docker Compose](#docker-compose)
- [Unraid](#unraid)
- [The first admin account](#the-first-admin-account)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)

## Docker Compose

```bash
git clone https://github.com/jeffreymooiweer/CargoPilot.git
cd CargoPilot
cp .env.example .env
```

Open `.env` and set at least these two:

| Setting | What to put there |
|---|---|
| `APP_SECRET_KEY` | Optional. Signs login sessions. Leave it empty and CargoPilot makes one on first start and keeps it in `DATA_DIR/secret_key`; set it only if you want to manage the key yourself. |
| `ADMIN_PASSWORD` | The password for your first admin account. |

A quick way to generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then start it:

```bash
docker compose up -d --build
```

Open <http://localhost:8080>.

Every other setting has a sensible default. If you want to change one, see
[Configuration](configuration.md).

## Unraid

1. Install from **Community Applications**, or add the template `unraid/CargoPilot.xml`
   manually.
2. Map the volume `/mnt/user/appdata/cargopilot` → `/data`.
3. Use the image `jeffersonmouze/cargopilot:latest`, or pin a specific version such as
   `jeffersonmouze/cargopilot:v1.13.2`.
4. Fill in `APP_SECRET_KEY` and the `ADMIN_*` variables.
5. Pick a WebUI port, for example `http://<server-ip>:9935`.

**File permissions.** On startup the container sets the owner of `/data` to `PUID`/`PGID`
(both default to `1000`). If your Unraid share uses different IDs, set them as
environment variables.

## The first admin account

There is no public sign-up page. The first administrator is created on first startup,
and only if all three of these are set:

- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Log in with those credentials. You can create more users from inside the app afterwards.

If you forget the password, stop the container, set `ADMIN_PASSWORD` to something new
and delete `cargopilot.db` from your data folder — note that this also removes any
equipment you imported.

## Updating

```bash
docker compose pull
docker compose up -d
```

On Unraid, click **Check for updates** or use the Docker tab as usual.

Your data lives in the `/data` volume and survives updates. New reference data (goods,
locations, UN numbers) is picked up automatically the next time the catalogue syncs,
which happens at startup.

> [!IMPORTANT]
> Docker images older than **v1.4.0** still contain an internal form that is not meant
> for civilian use. Use `v1.4.0` or newer. To clean up old tags on Docker Hub, go to
> GitHub → **Actions** → **Cleanup Docker Hub tags** → **Run workflow** and pass
> `keep_tags`: `latest,v1.13.2,1.13.2`.

## Troubleshooting

**The page loads but I cannot log in.**
The admin account is only created when `ADMIN_USERNAME`, `ADMIN_EMAIL` *and*
`ADMIN_PASSWORD` are all present at first startup. Check the container logs — the
bootstrap step reports what it did.

**Startup is slow, or hangs on a network call.**
CargoPilot refreshes its reference catalogues from public sources at startup. Set
`CATALOG_AUTO_SYNC=false` to skip that. The bundled data in the image is used instead,
and weight calculations are unaffected.

**Address search does not return anything.**
Address autocomplete calls an external geocoder (`photon.komoot.io` by default), so it
needs internet access. Airport, port and station search works fully offline. You can
always type an address by hand.

**Permission errors on `/data`.**
Set `PUID` and `PGID` to match the owner of your host folder.
