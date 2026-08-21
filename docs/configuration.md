# Configuration

CargoPilot is configured through environment variables. Copy `.env.example` to `.env` and
adjust what you need — every setting has a working default, including the signing key,
which the application makes for itself.

## Two places, and which one wins

Since v1.45.0 some of these settings also appear on the **Settings** screen, in a section
only administrators see. The rule is simple:

- An environment variable is the **starting value**. An installation that never opens the
  settings screen behaves exactly as its `.env` says, on this version and on every
  version before it.
- A value **saved on the settings screen** takes precedence from then on, and takes effect
  without restarting the container.

Only the settings in the table below have a screen counterpart. Everything else — the
signing key, the data folder, the cookie flags, the proxy headers — stays environment-only,
because those are read while the application is starting and there is no screen yet.

| Environment variable | On the settings screen | Takes effect |
|---|---|---|
| `GEO_ADDRESS_API_URL` | Address API | immediately |
| `GEO_ADDRESS_TIMEOUT_SECONDS` | Timeout | immediately |
| — | Address lookup on/off | immediately |
| `CATALOG_AUTO_SYNC` | Update the catalogue at startup | next restart |
| `UPDATE_CHECK_ENABLED` | Check for updates | immediately |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session lifetime | at the next login |
| — | Offer UN cards | immediately |
| — | Default language and theme for new users | at their next sign-in |
| — | Organisation name and address | immediately |
| `SMTP_HOST` and friends | Mail server | immediately |

The screen also carries per-user preferences — language, theme, the consignor details that
are retyped on every shipment, a saved signature. Those belong to the account rather than
to the installation, and are described in the [user guide](user-guide.md#settings).

## Essentials

| Variable | What it does | Default |
|---|---|---|
| `APP_SECRET_KEY` | Signs login sessions. Leave it empty and CargoPilot generates one on first start and keeps it in `DATA_DIR/secret_key`. | generated |
| `ADMIN_USERNAME` | Username of the first admin, created on first startup | — |
| `ADMIN_EMAIL` | Email of the first admin | — |
| `ADMIN_PASSWORD` | Password of the first admin. **Set this.** | — |
| `TZ` | Time zone used for dates on documents | `Europe/Amsterdam` |

All three `ADMIN_*` variables must be present together, or no account is created. There
is no public sign-up page.

## The signing key looks after itself

`APP_SECRET_KEY` signs the token that says you are logged in. Its default, `change-me`,
is published in this repository — so an installation that never set it would run on a key
anyone can look up, and anyone holding that key can write themselves a valid admin token.
There is no login to bypass at that point; it is already bypassed.

You do not have to do anything about that. On the first start CargoPilot generates a key,
stores it as `secret_key` in `DATA_DIR` (readable only by the owner) and uses it from then
on. It survives restarts and container recreation because it lives on the mounted volume.

Set `APP_SECRET_KEY` yourself only if you want to manage the key — to share it across
several instances, for example, or to keep it in your own secret store. A value you set
always wins, as long as it is not a published one and is at least 32 characters:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Changing the key logs everyone out.** Existing tokens were signed with the old key and
stop validating. Nothing else is lost — no shipment data hangs on it.

Changing a user's password also invalidates every session belonging to that user. Login
tokens contain a one-way fingerprint of the password hash that was current when the token
was issued. After a password change that fingerprint no longer matches and the user must
log in again on every device.

> **This used to be a refusal, and that was a mistake.** From v1.25.0 to v1.29.2
> CargoPilot stopped at startup on a published or empty key. The reasoning was sound —
> nobody reads a warning in a log — but the defaults it shipped with (`change-me` and
> `CORS_ALLOWED_ORIGINS=*`) and the Unraid template, which leaves the key blank, meant
> that every installation which had not filled both in by itself simply died on startup,
> in a container that exited too fast to read the message. Nothing was made safer; the app
> was just gone. Since v1.29.3 it makes a key instead. See the changelog for v1.29.3.

## What is reported but does not stop anything

Two settings are worth a line in the log without being worth a dead application:

| Reported | Why | What to do |
|---|---|---|
| `CORS_ALLOWED_ORIGINS=*` | The API works with cookies, and browsers refuse to combine those with a wildcard origin — so a cross-site call fails anyway | Name the address you reach CargoPilot on |
| `ADMIN_PASSWORD` set to one that appears in this project's documentation | It is not a password if it is printed in a README | Pick your own, and change it after first login |

### While developing

A fixed, known key is convenient there, so these reports only appear in production. Set
`APP_ENV` to `development`, `dev`, `local`, `test` or `testing` and they are skipped.
Anything else — including an empty value or a typo — counts as production, so a misspelled
`APP_ENV` cannot quietly switch them off. The key itself is still made safe in every
environment: development is a reason not to nag, not a reason to sign tokens with a
published string.

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
the image is used instead, and weight calculations are unaffected. The same switch sits on
the settings screen; because it is only read while the application starts, a change there
takes effect on the next restart.

## Update check

| Variable | What it does | Default |
|---|---|---|
| `UPDATE_CHECK_ENABLED` | Ask GitHub whether a newer release exists, when an administrator is signed in | `true` |
| `UPDATE_CHECK_TIMEOUT_SECONDS` | HTTP timeout for that one request | `8` |
| `UPDATE_APPLY_ENABLED` | Allow the administrator to update and restart from the settings screen (needs the Docker socket, below) | `false` |
| `UPDATE_APPLY_PULL_TIMEOUT_SECONDS` | How long the image pull may take before the update is abandoned | `600` |

The check only tells the administrator there is something to pull. Off means CargoPilot
never contacts GitHub; the switch also sits on the settings screen under **Outbound
connections** and is read per request, so flipping it needs no restart.

### Updating from inside the application

A container cannot swap its own image — unless the operator hands it the Docker API.
With both of these in the compose file (or as extra parameters on Unraid):

```yaml
environment:
  - UPDATE_APPLY_ENABLED=true
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

the settings screen's **Updating** section grows an **Update and restart** button
whenever a newer release exists. The application runs as uid 1000 while the socket
belongs to root (Unraid) or the docker group (most distributions); the container's
start script joins the app user to the socket's own group id before dropping
privileges, so no permission fiddling is needed on the host — this works since
v1.135.0, and when something else still blocks the capability, the Updating section
now names the exact reason instead of staying silent. Pressing it pulls `jeffersonmouze/cargopilot` at the
release's own tag (never `latest`, never a caller-supplied name), then hands the swap to
a short-lived helper container started from that new image: it stops the application,
renames it aside, recreates it with the identical configuration on the new image, starts
it, and only then removes the old one. If the new container will not start, the old one
is put back and the failure is reported on the settings screen — a failed update leaves
a working installation.

> [!WARNING]
> Mounting the Docker socket into a container gives that container administrator rights
> over the whole host — that is what makes the swap possible at all. It is a deliberate
> operator decision, off by default; without it, CargoPilot only ever *reports* updates
> and the manual `docker compose pull && docker compose up -d` (or Unraid's update
> button, or Watchtower) remains the way.

## Address lookup

| Variable | What it does | Default |
|---|---|---|
| `GEO_ADDRESS_API_URL` | A Photon-compatible geocoder for address autocomplete | `https://photon.komoot.io/api` |
| `GEO_ADDRESS_TIMEOUT_SECONDS` | HTTP timeout | `8` |

Point this at your own Photon instance if you would rather not call an external service.
Without it, address autocomplete simply stops offering suggestions — typing addresses by
hand always works, and airport, port and station search runs entirely offline.

This is the only request CargoPilot makes to the outside world while somebody is using it,
so the settings screen carries a switch that stops it being made at all. Turning it off is
not the same as pointing it at an unreachable address: no request leaves the server.

## Mail server

CargoPilot sends nothing until an administrator says where to send it. **Settings →
Administration → Mail server** asks for the server, the port, how the connection is
encrypted, the sign-in if the server wants one, and the sender address.

| Variable | What it does | Default |
|---|---|---|
| `SMTP_HOST` | The mail server. Empty means no mail server | empty |
| `SMTP_PORT` | Port | `587` |
| `SMTP_SECURITY` | `starttls` (port 587), `ssl` (implicit TLS, port 465) or `none` | `starttls` |
| `SMTP_USERNAME` | Sign-in, if the server asks for one | empty |
| `SMTP_PASSWORD` | The password for that sign-in | empty |
| `SMTP_FROM` | The sender address. Most relays refuse a sender they do not own | empty |
| `SMTP_FROM_NAME` | The name shown beside the sender address | empty |
| `SMTP_TIMEOUT_SECONDS` | How long to wait on the server | `15` |

A host **and** a sender in the environment switch sending on; the screen can then change
anything about it without a restart, and what is saved there takes precedence.

**The password.** It is stored on the server and never sent back to a browser: the screen
shows an empty password field and, when one is stored, says so. Leaving that field empty
when saving keeps the stored password — so the port can be corrected without retyping it.
Replacing it means typing a new one.

**Test message.** The button beside the settings sends a short message to the address you
give it, or to your own account when you leave it empty. It uses the settings **as saved**,
not the ones on screen, so save first — a test that passes on unsaved values and fails on
the saved ones would be worse than no test. Whatever the mail server answers is shown
unchanged: a refused password, an unreachable host and a rejected sender are different
problems with different fixes.

**What uses it.** Today: the test message. Mail is configuration that has to exist before
anything can be sent with it; what CargoPilot sends through it is a separate decision, made
per feature rather than assumed here.

## Application and security

| Variable | What it does | Default |
|---|---|---|
| `APP_NAME` | Name in the API title and in `GET /api/health`. **Not** the name on screen — the interface takes that from its own language files. | `CargoPilot` |
| `APP_ENV` | `production` or `development` | `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long a login stays valid | `480` (8 hours) |
| `COOKIE_SECURE` | Override the login-cookie `Secure` flag. Empty means automatic: enabled for HTTPS or trusted `X-Forwarded-Proto=https`. | automatic |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list, or `*` | `*` |
| `TRUSTED_PROXY_HEADERS` | Honour `X-Forwarded-*` headers behind a reverse proxy | `true` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

Upload limits are not configurable. An imported file is capped at 10 MB, 20,000 rows and
100 columns, and an `.xlsx` at 50 MB uncompressed — those are safety limits against a
malformed or hostile file, not a preference, and they live in
`backend/app/services/spreadsheet_io.py`.

> `MAX_PASTE_BYTES` was listed here until v1.47.0 and was read by nothing at all. The
> upload cap has always come from the constant above. A documented setting that does
> nothing is worse than an undocumented one: it invites somebody to tune it and conclude
> the app ignores them.

If you put CargoPilot behind a reverse proxy, keep `TRUSTED_PROXY_HEADERS=true` and set
`CORS_ALLOWED_ORIGINS` to your actual hostname instead of `*`. The login cookie is then
marked `Secure` when the proxy sends `X-Forwarded-Proto=https`. Set `COOKIE_SECURE=true`
when you want to force that behaviour, or `false` only for a deliberate HTTP-only setup.

User roles are restricted to `admin` and `user`. CargoPilot prevents an administrator from
disabling or demoting their own account and refuses to remove the last active administrator.
This prevents an installation from locking itself out through the user-management screen.

## Checking your setup

```bash
curl http://localhost:8080/api/health
```

```json
{
  "status": "ok",
  "app": "CargoPilot",
  "version": "1.45.0",
  "regulatory": {
    "manifest_id": "1dbeb6c1ca91cfd5",
    "editions": {
      "adr": "2025",
      "imdg": "Amendment 42-24 (2024 Edition)",
      "ems": "MSC.1/Circ.1588/Rev.3",
      "iata": "67e editie (2026)"
    },
    "expired": ["imdg_un_cards"]
  }
}
```

`regulatory` names the editions this installation actually computes with, so a bug report
can say so without guessing. `GET /api/regulatory` gives the full version, including the
source and validity period per rule set — see [Data sources](data-sources.md#which-edition-is-running).
