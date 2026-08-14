#!/usr/bin/env python3
"""Find the four-page model of the instructions in writing inside a volume.

ADR 5.4.3.4 and ADN 5.4.3.4 do not describe the instructions in writing, they
*print* them: "the instructions in writing shall correspond in form and content
to the following four-page model". So the document a driver or a boatmaster has
to carry is a reproduction of those pages, and the honest way for CargoPilot to
hand one over is to serve the pages themselves rather than a paraphrase of them.

The publishers do not offer those four pages as a standalone file that this
project can reach — unece.org answers a runner behind Cloudflare with 403 for
its pages, the web archive with 498 — but the volumes are in the document store
already. This reports where the model sits in a volume, so a page range can be
*measured* into ``backend/seed/dg/sources.json`` instead of guessed at, and the
application can cut those pages out of the operator's own copy.

    python scripts/find_instructions_pages.py store/adn.pdf [more.pdf ...]

What it prints per volume: the pages that carry 5.4.3, the page the model
starts on (the model opens with a title that names the regime, and its pages
are the ones carrying the label pictograms as images), the page 5.4.4 starts
on, and the first line of every page in between — enough to see whether the
range is clean or whether the last page of the model shares a sheet with what
follows it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# The model's own title, in the three languages the volumes are published in
# and in the Dutch edition. It is the first line of page one of the model.
TITLE = re.compile(
    r"INSTRUCTIONS? IN WRITING|CONSIGNES ÉCRITES|SCHRIFTELIJKE INSTRUCTIES"
    r"|SCHRIFTLICHE WEISUNGEN", re.IGNORECASE)
SECTION = re.compile(r"^\s*5\.4\.([34])\b", re.MULTILINE)


def look(path: Path) -> None:
    import fitz

    with fitz.open(path) as document:
        print(f"=== {path.name}: {document.page_count} pages")
        first_543 = last_543 = first_544 = None
        titles: list[int] = []
        for index in range(document.page_count):
            text = document[index].get_text("text")
            for found in SECTION.finditer(text):
                if found.group(1) == "3":
                    first_543 = index if first_543 is None else first_543
                    last_543 = index
                elif first_543 is not None and first_544 is None:
                    first_544 = index
            if first_543 is not None and TITLE.search(text):
                titles.append(index)
            if first_544 is not None and index > first_544 + 2:
                break
        print(f"  5.4.3 from page {first_543} to {last_543}, "
              f"5.4.4 starts on page {first_544}")
        print(f"  pages whose text carries the model's title: {titles[:6]}")
        if first_543 is None:
            return
        stop = (first_544 + 1) if first_544 is not None else last_543 + 1
        for index in range(first_543, min(stop + 1, document.page_count)):
            page = document[index]
            lines = [line.strip() for line in
                     page.get_text("text").strip().split("\n") if line.strip()]
            print(f"  p{index}: images {len(page.get_images())}, "
                  f"first {lines[0][:60]!r}, last {lines[-1][:40]!r}")


def main() -> int:
    if len(sys.argv) < 2:
        print("give one or more PDF paths", file=sys.stderr)
        return 2
    for name in sys.argv[1:]:
        path = Path(name)
        if not path.is_file():
            print(f"=== {path}: not in the store")
            continue
        look(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
