# Configuration

CargoPilot is configured entirely through environment variables. Copy `.env.example` to
`.env` and adjust what you need — every setting has a working default except the two
marked below.

## Essentials

| Variable | What it does | Default |
|---|---|---|
| `APP_SECRET_KEY` | Signs login sessions. **Set this** to a long random string in production. | `change-me` |
| `ADMIN_USERNAME` | Username of the first admin, created on first startup | — |
| `ADMIN_EMAIL` | Email of the first admin | — |
| `ADMIN_PASSWORD` | Password of the first admin. **Set this.** | — |
| `TZ` | Time zone used for dates on documents | `Europe/Amsterdam` |

All three `ADMIN_*` variables must be present together, or no account is created. There
is no public sign-up page.

## Storage

| Variable | What it does | Default |
|---|---|---|
| `DATA_DIR` | Folder for the database, templates and logs | `/data` |
| `DATABASE_URL` | SQLite database location | `sqlite:////data/cargopilot.db` |
| `PUID` / `PGID` | User and group that should own `/data` | `1000` / `1000` |

Keep `/data` on a persistent volume. It holds your users, the equipment you imported and
the catalogue sync status. Documents are never stored there.

## Reference data

| Variable | What it does | Default |
|---|---|---|
| `CATALOG_AUTO_SYNC` | Refresh material and profile catalogues from public sources at startup | `true` |
| `CATALOG_SYNC_TIMEOUT_SECONDS` | HTTP timeout per source | `20` |

Set `CATALOG_AUTO_SYNC=false` for a faster or fully offline startup. The data bundled in
the image is used instead, and weight calculations are unaffected.

## Address lookup

| Variable | What it does | Default |
|---|---|---|
| `GEO_ADDRESS_API_URL` | A Photon-compatible geocoder for address autocomplete | `https://photon.komoot.io/api` |
| `GEO_ADDRESS_TIMEOUT_SECONDS` | HTTP timeout | `8` |

Point this at your own Photon instance if you would rather not call an external service.
Without it, address autocomplete simply stops offering suggestions — typing addresses by
hand always works, and airport, port and station search runs entirely offline.

## Application and security

| Variable | What it does | Default |
|---|---|---|
| `APP_NAME` | Name shown in the interface | `CargoPilot` |
| `APP_ENV` | `production` or `development` | `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long a login stays valid | `480` (8 hours) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list, or `*` | `*` |
| `TRUSTED_PROXY_HEADERS` | Honour `X-Forwarded-*` headers behind a reverse proxy | `true` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `MAX_PASTE_BYTES` | Maximum size of a pasted import | `512000` |

If you put CargoPilot behind a reverse proxy, keep `TRUSTED_PROXY_HEADERS=true` and set
`CORS_ALLOWED_ORIGINS` to your actual hostname instead of `*`.

## Checking your setup

```bash
curl http://localhost:8080/api/health
```

```json
{ "status": "ok", "app": "CargoPilot", "version": "1.13.2" }
```
