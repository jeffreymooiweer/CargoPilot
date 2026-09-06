"""The IFTDGN notification as a file, for the export step and the bundle."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from app.services.edifact import iftdgn


def render_iftdgn(values: dict[str, Any], lines: list[dict[str, Any]],
                  dangerous_goods: list[dict[str, Any]] | None, language: str = "nl",
                  profiles: list[str] | None = None, modality: str | None = None) -> Path:
    text = iftdgn.build_interchange(values, lines, dangerous_goods,
                                    profiles=profiles, modality=modality)
    fd, name = tempfile.mkstemp(suffix=".edi")
    os.close(fd)
    out_path = Path(name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    # UNOC is ISO 8859-1. The builder has already replaced what falls
    # outside it, before the service characters were released, so this
    # encoding is strict: a character that still does not fit is a
    # programming error, not something to paper over with a "?" that the
    # syntax would read as the release character.
    out_path.write_bytes(text.encode("latin-1"))
    return out_path
