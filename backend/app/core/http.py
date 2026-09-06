"""Small pieces of HTTP that more than one route needs."""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote


def attachment(filename: str) -> str:
    """A ``Content-Disposition`` value that any name survives.

    A header is ISO 8859-1; a shipment reference with a character outside
    it (an emoji, a Cyrillic letter) used to turn the whole download into
    a 500 when it was written into the header as it was. RFC 6266 has the
    answer: an ASCII fallback in ``filename`` and the real name, percent
    encoded, in ``filename*``. A browser that reads the second uses it;
    one that does not still gets a file with a sensible name.
    """
    clean = re.sub(r"[\r\n\"\\;]", "_", str(filename or "")).strip() or "download"
    fallback = unicodedata.normalize("NFKD", clean).encode("ascii", "ignore").decode("ascii")
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", fallback).strip(" ._") or "download"
    if fallback == clean:
        return f'attachment; filename="{clean}"'
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(clean, safe='')}"
