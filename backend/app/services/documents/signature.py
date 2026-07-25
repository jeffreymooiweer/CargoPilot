"""Verwerking van door de gebruiker geplaatste handtekeningen.

De gebruiker kan in de wizard een handtekening tekenen of een afbeelding uploaden;
die komt als data-URL (PNG/JPEG/WebP, base64) mee in de exportaanvraag. Hier wordt
de afbeelding gevalideerd en genormaliseerd naar een transparante PNG die strak om
de inkt is bijgesneden, zodat hij netjes in de handtekeningvakken past.
"""
from __future__ import annotations

import base64
import io

from PIL import Image

MAX_DATA_URL_BYTES = 4_000_000
MAX_DECODED_BYTES = 3_000_000
MAX_DIMENSION = 1600
_ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
_WHITE_THRESHOLD = 242


def decode_signature_image(data_url: str) -> bytes:
    """Data-URL → genormaliseerde PNG-bytes. Raise ValueError bij ongeldig beeld."""
    if len(data_url) > MAX_DATA_URL_BYTES:
        raise ValueError("signature_too_large")
    header, sep, b64 = data_url.partition(",")
    if not sep or not header.startswith("data:") or ";base64" not in header:
        raise ValueError("signature_invalid_format")
    mime = header[5:].split(";", 1)[0].strip().lower()
    if mime not in _ALLOWED_MIME:
        raise ValueError("signature_invalid_format")
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as exc:
        raise ValueError("signature_invalid_format") from exc
    if len(raw) > MAX_DECODED_BYTES:
        raise ValueError("signature_too_large")

    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception as exc:
        raise ValueError("signature_invalid_format") from exc

    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    img = _white_to_transparent(img)

    bbox = img.getbbox()
    if bbox is None:
        raise ValueError("signature_empty")
    img = img.crop(bbox)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _white_to_transparent(img: Image.Image) -> Image.Image:
    """Maak (bijna-)witte achtergrond transparant, zodat een gefotografeerde of
    gescande handtekening niet als wit blok over de formulierlijnen valt."""
    from PIL import ImageChops

    luminance = img.convert("L")
    ink_mask = luminance.point(lambda v: 0 if v >= _WHITE_THRESHOLD else 255)
    alpha = ImageChops.darker(img.getchannel("A"), ink_mask)
    img.putalpha(alpha)
    return img
