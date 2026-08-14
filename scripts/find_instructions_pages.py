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
        # The table of contents names 5.4.3 and 5.4.4 on one page and would
        # end the search in the front matter, so every candidate is collected
        # and the *last* run is the body. The model's own title decides where
        # it starts: a page that carries it and the pictograms is a model page.
        heads_543: list[int] = []
        heads_544: list[int] = []
        titles: list[int] = []
        for index in range(document.page_count):
            text = document[index].get_text("text")
            for found in SECTION.finditer(text):
                (heads_543 if found.group(1) == "3" else heads_544).append(index)
            if TITLE.search(text):
                titles.append(index)
        print(f"  pages naming 5.4.3: {heads_543[:8]}")
        print(f"  pages naming 5.4.4: {heads_544[:8]}")
        print(f"  pages carrying the model's title: {titles[:8]}")
        body_titles = [i for i in titles if i > 20]
        if not body_titles:
            return
        first_543 = body_titles[0]
        first_544 = next((i for i in heads_544 if i > first_543), None)
        stop = (first_544 + 1) if first_544 is not None else first_543 + 6
        for index in range(max(0, first_543 - 1), min(stop + 1, document.page_count)):
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
