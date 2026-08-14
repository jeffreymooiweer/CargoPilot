#!/usr/bin/env python3
"""Cut every registered model of 5.4.3 and report what came out.

The page ranges in ``backend/seed/dg/sources.json`` were measured on the
editions, and the application cuts them at run time — but the development
container holds almost none of those editions, so the one place where the whole
path can actually be walked is a runner with the store restored from the cache.

This walks it: for every model the register knows, it asks the application's own
service for the file and prints how many pages came back and the first line of
each, so that a range which starts a page too late (the model's title gone) or
ends a page too early (the equipment list gone) is visible rather than assumed.

    python scripts/check_instruction_models.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services import regulations  # noqa: E402


#: The model's own title, in every language an edition here is printed in. A
#: page is identified by what it *contains*, not by what comes out of it first:
#: pypdf returns a page's text in the order the content stream draws it, and on
#: a page that is one full-width table that order is not the reading order.
TITLE = re.compile(
    r"INSTRUCTIONS? IN WRITING|CONSIGNES ÉCRITES|SCHRIFTELIJKE INSTRUCTIES"
    r"|SCHRIFTLICHE WEISUNGEN", re.IGNORECASE)
#: What must not be inside the model: the sections around it.
NEIGHBOURS = re.compile(r"5\.4\.3\.5|5\.4\.4|5\.4\.2\b")


def marks(page) -> str:
    text = page.extract_text() or ""
    found = [name for name, pattern in
             (("TITLE", TITLE), ("neighbour", NEIGHBOURS)) if pattern.search(text)]
    return f"[{','.join(found) or '—'}, {len(text)} chars]"


def first_lines(page, count: int = 2) -> str:
    lines = [line.strip() for line in page.extract_text().strip().split("\n")
             if line.strip()
             and not re.fullmatch(r"-\s*[\dxvi.\-]+\s*-", line.strip())
             and not line.strip().startswith(("Copyright", "©"))]
    return " / ".join(line[:60] for line in lines[:count])


def main() -> int:
    from pypdf import PdfReader

    missing = 0
    for doc in regulations.instruction_documents():
        model = doc["model_of"]
        status = regulations.instruction_status(model["regime"], model["language"])
        head = f"{doc['id']:24s}"
        if not status["available"]:
            print(f"{head} missing — needs {status['needs']}")
            missing += 1
            continue
        path = regulations.instructions_pdf(model["regime"], model["language"])
        reader = PdfReader(str(path))
        print(f"{head} {len(reader.pages)} pages from {status.get('source')}"
              f" ({status.get('from_document', '')})")
        for number, page in enumerate(reader.pages, start=1):
            print(f"    p{number}: {marks(page)} {first_lines(page, 1)}")
        # And the neighbourhood in the source, numbered as the cutter numbers
        # it. The page ranges were measured with a different library, and two
        # libraries counting from different ends is exactly the kind of thing
        # that puts a model's title outside its own range.
        cut = doc.get("cut_from")
        if cut:
            source = regulations.locate(cut["document"])
            first, last = cut["pages"]
            pages = PdfReader(str(source)).pages
            for number in range(max(1, first - 2), min(len(pages), last + 2) + 1):
                mark = "IN " if first <= number <= last else "   "
                page = pages[number - 1]
                print(f"      {mark}source p{number}: {marks(page)} "
                      f"{first_lines(page, 1)}")
    print(f"{missing} model(s) this store cannot produce")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
