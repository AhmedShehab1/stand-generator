"""
Data layer for the stand-generator.
Uses libsql-client, which speaks the same API whether DATABASE_URL points at
a local SQLite file (dev) or a remote Turso database (prod) — same code path
either way, matching the DATABASE_URL / DATABASE_AUTH_TOKEN env var names
used in the orderak project for consistency.
"""
import json
import os
import re
import secrets
import time

import libsql_client

DATABASE_URL = os.environ.get("DATABASE_URL", "file:local.db")
DATABASE_AUTH_TOKEN = os.environ.get("DATABASE_AUTH_TOKEN")

# ---------------------------------------------------------------------------
# Theme presets — the "different flavors" idea from the very first design.
# Add more here any time; the form picks them up automatically.
# ---------------------------------------------------------------------------
THEMES = {
    "citrus": {
        "label": "Citrus (orange & green)",
        "primary": "#E8590C", "primary_dark": "#B8410A",
        "secondary": "#2F9E44", "cream": "#FFF7ED", "text_dark": "#2B2118",
    },
    "mint": {
        "label": "Mint (teal & amber)",
        "primary": "#0CA678", "primary_dark": "#087F5B",
        "secondary": "#F08C00", "cream": "#F1FBF7", "text_dark": "#122620",
    },
    "berry": {
        "label": "Berry (magenta & violet)",
        "primary": "#C2255C", "primary_dark": "#99235A",
        "secondary": "#5F3DC4", "cream": "#FDF2F6", "text_dark": "#2B1220",
    },
    "midnight": {
        "label": "Midnight (navy & gold)",
        "primary": "#1E3A5F", "primary_dark": "#12263F",
        "secondary": "#D4A017", "cream": "#F3F1EA", "text_dark": "#1A1A1A",
    },
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
  slug TEXT PRIMARY KEY,
  edit_token TEXT NOT NULL,
  name_ar TEXT NOT NULL,
  tagline_ar TEXT,
  qr_center_letter TEXT,
  theme_name TEXT NOT NULL DEFAULT 'citrus',
  instapay_handle TEXT NOT NULL,
  instapay_link TEXT,
  socials_json TEXT NOT NULL DEFAULT '{}',
  logo_b64 TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
"""


def get_client():
    if DATABASE_URL.startswith("file:"):
        return libsql_client.create_client_sync(DATABASE_URL)
    return libsql_client.create_client_sync(DATABASE_URL, auth_token=DATABASE_AUTH_TOKEN)


def init_db():
    client = get_client()
    with client:
        client.execute(SCHEMA)


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or secrets.token_hex(3)


def _unique_slug(client, base: str) -> str:
    slug = base
    n = 1
    while True:
        rs = client.execute("SELECT 1 FROM businesses WHERE slug = ?", [slug])
        if not rs.rows:
            return slug
        n += 1
        slug = f"{base}-{n}"


def create_business(data: dict) -> tuple[str, str]:
    """Returns (slug, edit_token)."""
    client = get_client()
    with client:
        slug = _unique_slug(client, slugify(data.get("slug_base") or data["name_ar"]))
        edit_token = secrets.token_urlsafe(16)
        now = int(time.time())
        client.execute(
            """
            INSERT INTO businesses
              (slug, edit_token, name_ar, tagline_ar, qr_center_letter, theme_name,
               instapay_handle, instapay_link, socials_json, logo_b64, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                slug, edit_token, data["name_ar"], data.get("tagline_ar", ""),
                data.get("qr_center_letter") or data["name_ar"][:1],
                data.get("theme_name", "citrus"),
                data["instapay_handle"], data.get("instapay_link", ""),
                json.dumps(data.get("socials", {}), ensure_ascii=False),
                data.get("logo_b64"),
                now, now,
            ],
        )
    return slug, edit_token


def get_business(slug: str) -> dict | None:
    client = get_client()
    with client:
        rs = client.execute("SELECT * FROM businesses WHERE slug = ?", [slug])
        if not rs.rows:
            return None
        row = rs.rows[0]
        return dict(zip(rs.columns, row))


def update_business(slug: str, data: dict) -> None:
    client = get_client()
    with client:
        client.execute(
            """
            UPDATE businesses SET
              name_ar = ?, tagline_ar = ?, qr_center_letter = ?, theme_name = ?,
              instapay_handle = ?, instapay_link = ?, socials_json = ?,
              logo_b64 = COALESCE(?, logo_b64), updated_at = ?
            WHERE slug = ?
            """,
            [
                data["name_ar"], data.get("tagline_ar", ""),
                data.get("qr_center_letter") or data["name_ar"][:1],
                data.get("theme_name", "citrus"),
                data["instapay_handle"], data.get("instapay_link", ""),
                json.dumps(data.get("socials", {}), ensure_ascii=False),
                data.get("logo_b64"),
                int(time.time()), slug,
            ],
        )


def business_to_config(row: dict) -> dict:
    """Reshape a flat DB row back into the nested config dict the templates expect."""
    theme = THEMES.get(row["theme_name"], THEMES["citrus"])
    raw_link = (row["instapay_link"] or "").strip()
    is_valid_url = raw_link.startswith(("https://", "http://"))
    return {
        "business": {
            "name_ar": row["name_ar"],
            "tagline_ar": row["tagline_ar"] or "",
            "qr_center_letter": row["qr_center_letter"] or row["name_ar"][:1],
        },
        "theme": theme,
        "payment": {
            "instapay_handle": row["instapay_handle"],
            "instapay_link": raw_link if is_valid_url else None,
        },
        "socials": json.loads(row["socials_json"] or "{}"),
        "branding": {"powered_by": "Powered by Stand+"},
        "logo_b64": row["logo_b64"],
    }
