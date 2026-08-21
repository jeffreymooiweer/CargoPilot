"""Print the full text layer of stored PDFs, page by page.

The survey (survey_incoming.py) says what a document is and where its parts
sit; sometimes the next question is simply "what does it say" — a three-page
corrigenda, a title page, a single packing instruction. This prints the text
layer of every PDF whose path matches the given pattern, with page headers,
so a workflow log carries the document's own words instead of a summary.

It refuses to dump a book. Reading eight hundred pages through a log tail
helps nobody, and the page cap makes the refusal explicit instead of silent
truncation.

Usage::

    python scripts/dump_pdf_text.py ROOT PATTERN [--max-pages N]

PATTERN is matched case-insensitively against the path relative to ROOT.
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import fitz  # pymupdf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("pattern")
    parser.add_argument("--max-pages", type=int, default=40,
                        help="refuse documents longer than this")
    args = parser.parse_args()

    matches = [path for path in sorted(args.root.rglob("*.pdf"))
               if fnmatch.fnmatch(str(path.relative_to(args.root)).lower(),
                                  args.pattern.lower())]
    if not matches:
        print(f"nothing under {args.root} matches {args.pattern!r}")
        return 1
    for path in matches:
        print(f"\n{'=' * 72}\nFILE {path}")
        with fitz.open(path) as doc:
            if doc.page_count > args.max_pages:
                print(f"SKIPPED: {doc.page_count} pages is a book, not a note "
                      f"(cap {args.max_pages}; raise --max-pages deliberately)")
                continue
            for number in range(doc.page_count):
                print(f"\n----- page {number + 1} of {doc.page_count} -----")
                print(doc[number].get_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
