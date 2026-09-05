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
    # UNOC is ISO 8859-1; a character outside it becomes a question mark
    # rather than failing the whole notification.
    out_path.write_bytes(text.encode("latin-1", "replace"))
    return out_path
