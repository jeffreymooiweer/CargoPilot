"""Processing of signatures placed by the user.

In the wizard the user can draw a signature or upload an image; it arrives with
the export request as a data URL (PNG/JPEG/WebP, base64). Here the image is
validated and normalised to a transparent PNG cropped tightly around the ink, so
that it fits neatly in the signature boxes.
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
    """Data URL → normalised PNG bytes. Raises ValueError on an invalid image."""
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
    """Make a (near-)white background transparent, so a photographed or scanned
    signature does not fall over the form's rules as a white block."""
    from PIL import ImageChops

    luminance = img.convert("L")
    ink_mask = luminance.point(lambda v: 0 if v >= _WHITE_THRESHOLD else 255)
    alpha = ImageChops.darker(img.getchannel("A"), ink_mask)
    img.putalpha(alpha)
    return img
