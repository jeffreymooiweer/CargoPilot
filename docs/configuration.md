# Configuration

CargoPilot is configured entirely through environment variables. Copy `.env.example` to
`.env` and adjust what you need — every setting has a working default except the two
marked below.

## Essentials

| Variable | What it does | Default |
|---|---|---|
| `APP_SECRET_KEY` | Signs login sessions. **Required.** CargoPilot refuses to start without your own value. | — |
| `ADMIN_USERNAME` | Username of the first admin, created on first startup | — |
| `ADMIN_EMAIL` | Email of the first admin | — |
| `ADMIN_PASSWORD` | Password of the first admin. **Set this.** | — |
| `TZ` | Time zone used for dates on documents | `Europe/Amsterdam` |

All three `ADMIN_*` variables must be present together, or no account is created. There
is no public sign-up page.

## CargoPilot refuses to start on an unsafe configuration

`APP_SECRET_KEY` signs the token that says you are logged in. Its old default,
`change-me`, is published in this repository — so an installation that never set it ran
on a key anyone could look up, and anyone holding that key can write themselves a valid
admin token. There is no login to bypass at that point; it is already bypassed.

Since v1.25.0 the application stops at startup instead, and says what to do:

```
CargoPilot start niet met deze instellingen:

  • APP_SECRET_KEY staat nog op de gepubliceerde standaardwaarde ('change-me').
    Die sleutel tekent de inlogtokens: wie hem kent kan zelf een token voor de
    beheerder maken. Zet er een eigen waarde voor in de plaats, bijvoorbeeld:
    APP_SECRET_KEY=nT8v...
```

The key it offers is freshly generated and usable as-is. You can also make one yourself:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Three things are checked, and all failures are reported at once so one restart is enough:

| Refused | Why |
|---|---|
| `APP_SECRET_KEY` empty, published (`change-me`, `dev-secret`, the placeholder from `.env.example`) or under 32 characters | The key signs login tokens |
| `CORS_ALLOWED_ORIGINS=*` | The API works with cookies, so any website could then make requests on behalf of a logged-in user. Name your own address instead |
| `ADMIN_PASSWORD` set to one that appears in this project's documentation | It is not a password if it is printed in a README |

**Changing `APP_SECRET_KEY` logs everyone out.** Existing tokens were signed with the old
key and stop validating. Nothing else is lost — no shipment data hangs on it.

### While developing

A fixed, known key is convenient there, so the check only runs in production. Set
`APP_ENV` to `development`, `dev`, `local`, `test` or `testing` and it is skipped
entirely. Anything else — including an empty value or a typo — counts as production, so
a misspelled `APP_ENV` cannot quietly switch the check off.

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
