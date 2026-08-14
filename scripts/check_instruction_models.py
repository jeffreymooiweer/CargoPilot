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
            print(f"    p{number}: {first_lines(page)}")
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
                print(f"      {mark}source p{number}: {first_lines(pages[number - 1])}")
    print(f"{missing} model(s) this store cannot produce")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
