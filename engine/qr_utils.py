"""
Reusable QR generation for the stand engine.
Produces a themed QR (custom fill colour) with an optional circular
monogram badge in the center — the same visual trick used on the
reference stand (the small IPN mark in the middle of the InstaPay QR).
"""
import base64
import io
import os

import qrcode
import qrcode.image.pil
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H

FONT_BLACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "Cairo-Black.ttf")


def _shape_arabic(text: str) -> str:
    import arabic_reshaper
    from bidi.algorithm import get_display

    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def make_qr(
    data: str,
    fill_color: str = "#1a1a1a",
    back_color: str = "#ffffff",
    box_size: int = 10,
    border: int = 2,
    center_letter: str | None = None,
    center_bg: str = "#E8590C",
) -> Image.Image:
    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGB")

    if center_letter:
        img = _stamp_center_badge(img, center_letter, center_bg)

    return img


def _stamp_center_badge(img: Image.Image, letter: str, bg_hex: str) -> Image.Image:
    w, h = img.size
    badge_d = int(w * 0.22)
    ring_d = int(badge_d * 1.18)

    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2

    # white ring so the badge doesn't collide with QR modules
    draw.ellipse(
        [cx - ring_d // 2, cy - ring_d // 2, cx + ring_d // 2, cy + ring_d // 2],
        fill="#ffffff",
    )
    draw.ellipse(
        [cx - badge_d // 2, cy - badge_d // 2, cx + badge_d // 2, cy + badge_d // 2],
        fill=bg_hex,
    )

    font_size = int(badge_d * 0.62)
    font = ImageFont.truetype(FONT_BLACK, font_size)
    # A single isolated letter needs no joining/reshaping — and this font only
    # ships glyphs for the base Arabic block, not the legacy presentation forms
    # that arabic_reshaper produces, so we draw the raw character directly.
    bbox = draw.textbbox((0, 0), letter, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
        letter,
        font=font,
        fill="#ffffff",
    )
    return img


def to_base64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def save_png(img: Image.Image, path: str) -> str:
    img.save(path, format="PNG")
    return path
