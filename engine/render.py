"""
Thin wrapper around the templates + QR generation.
Both functions take the same nested config dict shape:
  {business, theme, payment, socials, branding, logo_b64}
"""
import os

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from .qr_utils import make_qr, to_base64_png

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(ENGINE_DIR, "..", "fonts")

env = Environment(loader=FileSystemLoader(ENGINE_DIR))


def render_linktree_html(cfg: dict) -> str:
    tpl = env.get_template("linktree_template.html.j2")
    return tpl.render(**cfg)


def render_stand_pdf_bytes(cfg: dict, linktree_url: str) -> bytes:
    instapay_qr = make_qr(
        cfg["payment"]["instapay_link"] or cfg["payment"]["instapay_handle"],
        fill_color=cfg["theme"]["primary_dark"],
        center_letter=cfg["business"]["qr_center_letter"],
        center_bg=cfg["theme"]["primary"],
    )
    linktree_qr = make_qr(
        linktree_url,
        fill_color=cfg["theme"]["text_dark"],
        center_letter=cfg["business"]["qr_center_letter"],
        center_bg=cfg["theme"]["secondary"],
    )

    tpl = env.get_template("stand_template.html.j2")
    html = tpl.render(
        **cfg,
        instapay_qr_b64=to_base64_png(instapay_qr),
        linktree_qr_b64=to_base64_png(linktree_qr),
        font_regular="file://" + os.path.join(FONTS_DIR, "Cairo-Regular.ttf"),
        font_bold="file://" + os.path.join(FONTS_DIR, "Cairo-Bold.ttf"),
        font_black="file://" + os.path.join(FONTS_DIR, "Cairo-Black.ttf"),
    )
    return HTML(string=html, base_url=ENGINE_DIR).write_pdf()
