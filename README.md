# stand-generator

Standalone from `orderak` on purpose (see the design discussion this came out of) —
same idea of a Turso-backed multi-tenant app, but its own repo, own database,
own deploy, so nothing here can affect orderak's live orders.

Intake form → stores one row per business in Turso → two things get generated
from it on demand:

- **`/l/<slug>`** — a live, theme-aware link-tree page (InstaPay button + social links)
- **`/stand/<slug>.pdf`** — a print-ready A5 PDF with two QR codes (InstaPay + the link-tree page)

Editing a business later updates `/l/<slug>` instantly. The printed stand's QR
never has to change — it just points at that URL.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # defaults to a local SQLite file, no Turso needed yet
python app.py             # http://localhost:5000
```

## Routes

| Route | Purpose |
|---|---|
| `GET /` | intake form |
| `POST /submit` | creates a business, redirects to `/success/<slug>` |
| `GET /success/<slug>?token=...` | shows the live link, PDF download, and the one-time edit link |
| `GET /l/<slug>` | the live link-tree page (public) |
| `GET /stand/<slug>.pdf` | generates & downloads the print-ready stand |
| `GET/POST /edit/<slug>?token=...` | edit a business — the `edit_token` in the URL is the only auth for now (see Known limitations) |

## Switching to Turso

```bash
turso db create stand-generator
turso db show stand-generator --url            # -> DATABASE_URL
turso db tokens create stand-generator         # -> DATABASE_AUTH_TOKEN
```

Set both as env vars (locally in `.env`, or as Heroku config vars below). No
code changes needed — `db.py` uses the same `libsql_client` API for a local
file and a remote Turso database; only the URL scheme differs.

## Deploying to Heroku

```bash
heroku create your-app-name
heroku config:set DATABASE_URL=libsql://your-db.turso.io
heroku config:set DATABASE_AUTH_TOKEN=<token from turso db tokens create>
git push heroku main
```

Uses Heroku's default Python runtime — no `runtime.txt` needed unless you
want to pin a specific version. `Procfile` already points gunicorn at `app.py`.

If you're on the GitHub Student Pack's Heroku credit ($13/mo for 24 months):
one Eco Dyno ($5/mo) comfortably covers this app, since Turso is external and
there's no Postgres/Redis add-on to pay for.

## Adding a theme

Add an entry to `THEMES` in `db.py` — the form picks it up automatically,
no template changes needed:

```python
"sunset": {
    "label": "Sunset (coral & plum)",
    "primary": "#E8590C", "primary_dark": "#B8410A",
    "secondary": "#5F3DC4", "cream": "#FFF7ED", "text_dark": "#2B1220",
},
```

## Known limitations (fine for one-person onboarding, worth fixing before self-serve)

- **Edit auth is just the token in the URL** — there's no login. That matches
  "I'll onboard everyone myself" for now, but if clients ever edit their own
  page, put this behind a real auth check first.
- **No image validation beyond Pillow decoding** — a client uploading a huge
  or malicious file just gets resized; there's no MIME/size allowlist yet.
- **PDF is generated fresh on every request** — fine at low volume; add a
  cache (regenerate only after edits) if this ever gets busy.
- **Single Turso database, no per-tenant isolation** — fine for your own
  managed multi-tenant product; don't reuse this schema pattern for anything
  where tenants shouldn't be able to guess each other's slugs.
