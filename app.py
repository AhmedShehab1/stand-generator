import base64
import io
import json
import re
from dotenv import load_dotenv

from flask import Flask, request, render_template, redirect, url_for, send_file, abort
from PIL import Image

from db import init_db, create_business, update_business, get_business, business_to_config, THEMES
from engine.render import render_linktree_html, render_stand_pdf_bytes

load_dotenv()

app = Flask(__name__)
init_db()


@app.route("/health")
def health():
    return {"status": "ok"}, 200

MAX_LOGO_DIM = 320  # px, kept small since it only ever renders at a few cm


def _read_logo(file_storage) -> str | None:
    """Reads an uploaded image, downsizes it, returns base64 PNG (no data: prefix)."""
    if not file_storage or not file_storage.filename:
        return None
    img = Image.open(file_storage.stream).convert("RGBA")
    img.thumbnail((MAX_LOGO_DIM, MAX_LOGO_DIM))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _socials_from_form(form) -> dict:
    socials = {}
    for key in ("facebook", "instagram", "tiktok"):
        val = (form.get(key) or "").strip()
        if val:
            socials[key] = val
    phone = re.sub(r"[^0-9]", "", form.get("whatsapp_number", ""))
    if phone:
        socials["whatsapp"] = f"https://wa.me/{phone}"
    return socials


def _business_data_from_form(form, files) -> dict:
    return {
        "name_ar": form["name_ar"].strip(),
        "tagline_ar": (form.get("tagline_ar") or "").strip(),
        "slug_base": (form.get("name_en") or form.get("name_ar")).strip(),
        "theme_name": form.get("theme_name", "citrus"),
        "instapay_handle": form["instapay_handle"].strip(),
        "instapay_link": (form.get("instapay_link") or "").strip(),
        "socials": _socials_from_form(form),
        "logo_b64": _read_logo(files.get("logo")),
    }


@app.route("/")
def index():
    return render_template("form.html", themes=THEMES, mode="create", business=None, token=None, socials={})


@app.route("/submit", methods=["POST"])
def submit():
    data = _business_data_from_form(request.form, request.files)
    slug, edit_token = create_business(data)
    return redirect(url_for("success", slug=slug, token=edit_token))


@app.route("/success/<slug>")
def success(slug):
    row = get_business(slug)
    if not row:
        abort(404)
    token = request.args.get("token", "")
    base = request.host_url.rstrip("/")
    return render_template(
        "success.html",
        row=row,
        linktree_url=f"{base}/l/{slug}",
        stand_url=f"{base}/stand/{slug}.pdf",
        edit_url=f"{base}/edit/{slug}?token={token}" if token else None,
    )


@app.route("/l/<slug>")
def linktree(slug):
    row = get_business(slug)
    if not row:
        abort(404)
    cfg = business_to_config(row)
    return render_linktree_html(cfg)


@app.route("/stand/<slug>.pdf")
def stand_pdf(slug):
    row = get_business(slug)
    if not row:
        abort(404)
    cfg = business_to_config(row)
    linktree_url = f"{request.host_url.rstrip('/')}/l/{slug}"
    pdf_bytes = render_stand_pdf_bytes(cfg, linktree_url)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{slug}-stand.pdf",
    )


@app.route("/edit/<slug>", methods=["GET", "POST"])
def edit(slug):
    row = get_business(slug)
    if not row:
        abort(404)
    token = request.args.get("token") or request.form.get("token", "")
    if token != row["edit_token"]:
        abort(403)

    if request.method == "POST":
        data = _business_data_from_form(request.form, request.files)
        if not data["logo_b64"]:
            data["logo_b64"] = None  # keep existing logo (COALESCE in update_business)
        update_business(slug, data)
        return redirect(url_for("success", slug=slug, token=token))

    return render_template(
        "form.html", themes=THEMES, mode="edit", business=row, token=token,
        socials=json.loads(row["socials_json"] or "{}"),
    )


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
