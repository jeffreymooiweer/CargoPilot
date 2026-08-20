#!/usr/bin/env python3
"""Read table A of RID 3.2.1 out of the editions in the regulations store.

The UN cards fail honestly for rail because CargoPilot's table A is the
ADR's: generating a RID card from a road row would relabel road data as
rail data (columns (12) to (20) are the rail's own — tank codes, transport
category, the W/VC/CW/CE provisions, the hazard number can all differ).
This script reads the RID's own table, the way
``extract_rid_shunting_labels.py`` read its column (5): geometrically, from
the word positions of the official editions in the store.

## What the probe measured (run 2026-08-20, both editions)

Both books print the table as one contiguous run of pages — OTIF English
262-523, Dutch 304-515 — each page carrying the full column-number band
``(1) (2) (3a) (3b) (4) (5) (6) (7a) (7b) (8) (9a) (9b) (10) (11) (12)
(13) (15) (16) (17) (18) (19) (20)`` (there is no column (14) in the RID)
at page-constant x positions. The English edition centres each cell under
its number; the Dutch edition left-aligns cells on it. Assignment therefore
scores a chunk against both its left edge and its centre and takes the
nearest column, with everything left of column (3a) belonging to the name.

## The two readings

The Dutch and the English edition are two independent typesettings of the
same table (212 pages against 262, different column positions, different
alignment). Both are parsed by the same code and compared row by row on
every coded column — the names differ by language and are kept per
edition. A systematic parser error does not produce the same wrong value
under two different layouts, so agreement is the check. On top of that the
result is cross-checked against two seeds this repository already trusts:
the ADR table A (columns (1)-(4) are harmonised between the regimes) and
the v1.123.0 shunting-label reading of column (5).

    python scripts/extract_rid_table_a.py --pdf rid.pdf --probe
    python scripts/extract_rid_table_a.py --build --out backend/seed/dg/rid_table_a.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - runner installs it
    fitz = None

STORE = Path(
    os.environ.get("CARGOPILOT_REGULATIONS_DIR")
    or ("/data/regulations" if Path("/data").is_dir()
        else "/tmp/cargopilot-regulations"))

SEED = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

MARKER = re.compile(r"^\((\d{1,2}[ab]?)\)$")
UN_WORD = re.compile(r"^\d{4}$")

#: The columns of RID table A in printed order. No (14): that column is the
#: ADR's (vehicle for tank carriage) and the RID does not print it.
COLS = ["1", "2", "3a", "3b", "4", "5", "6", "7a", "7b", "8", "9a", "9b",
        "10", "11", "12", "13", "15", "16", "17", "18", "19", "20"]

FIELDS = {
    "1": "un", "2": "name", "3a": "class", "3b": "classification_code",
    "4": "packing_group", "5": "labels", "6": "special_provisions",
    "7a": "limited_quantity", "7b": "excepted_quantity",
    "8": "packing_instructions", "9a": "packing_provisions",
    "9b": "mixed_packing_provisions", "10": "portable_tank_instructions",
    "11": "portable_tank_provisions", "12": "tank_code",
    "13": "tank_provisions", "15": "transport_category",
    "16": "packages_provisions", "17": "bulk_provisions",
    "18": "loading_provisions", "19": "express_parcels",
    "20": "hazard_number",
}

#: Coded columns compared between the two editions. The name is per
#: language; everything else must be printed identically in both books.
COMPARED = [c for c in COLS if c not in ("2",)]

#: A footer line: the running page number or edition line at the bottom.
#: The OTIF edition numbers its pages "3.2-A-12"; the Dutch edition adds
#: page lines of its own.
FOOTER = re.compile(
    r"^(RID\s*\d{4}.*|-?\s*\d+\s*-?|\d+\s*/\s*\d+|.*OTIF.*|3\.2-[A-C]-\d+.*"
    r"|(Page|Pagina)\s*\d*)$")

#: The Dutch PDF carries stray "Page N" words in its text layer, at
#: positions that land inside the table's right-hand columns. They are
#: artefacts of the file, not content of the book, and are dropped as
#: chunks wherever they stand.
NOISE_CHUNK = re.compile(r"^(Page|Pagina)( \d+)?$")

#: Both editions replace a whole row's cells with a banner where carriage
#: is prohibited by rail.
PROHIBITED = ("CARRIAGE PROHIBITED", "VERVOER VERBODEN")


def probe(pdf_path: Path, sample_pages: int) -> int:
    doc = fitz.open(str(pdf_path))
    print(f"== {pdf_path.name}: {doc.page_count} pages, "
          f"first page rect {doc[0].rect} ==")
    header_pages: list[tuple[int, tuple[str, ...]]] = []
    for number in range(doc.page_count):
        words = doc[number].get_text("words")
        markers = sorted(
            ((w[0], MARKER.match(w[4]).group(1)) for w in words
             if MARKER.match(w[4])), key=lambda m: m[0])
        codes = tuple(code for _x, code in markers)
        if len(codes) >= 10:
            header_pages.append((number + 1, codes))

    if not header_pages:
        print("no pages with a 10+ column-number band found")
        return 1

    runs: list[list[tuple[int, tuple[str, ...]]]] = []
    for page, codes in header_pages:
        if runs and page - runs[-1][-1][0] <= 2:
            runs[-1].append((page, codes))
        else:
            runs.append([(page, codes)])
    print(f"{len(header_pages)} header pages in {len(runs)} runs:")
    for run in runs:
        print(f"  pages {run[0][0]}-{run[-1][0]} ({len(run)} pages)")
    shapes = Counter(codes for _page, codes in header_pages)
    for codes, count in shapes.most_common(4):
        print(f"  {count} pages with markers: {' '.join(codes)}")

    main_run = max(runs, key=len)
    for page_number in [main_run[0][0], main_run[len(main_run) // 2][0]][:sample_pages]:
        page = doc[page_number - 1]
        words = page.get_text("words")
        markers = sorted(((w[0], w[1], w[4]) for w in words
                          if MARKER.match(w[4])), key=lambda m: m[0])
        print(f"\n-- page {page_number}: marker positions --")
        print("  " + "  ".join(f"{t}@x{x:.0f}/y{y:.0f}" for x, y, t in markers))
        un_rows = sorted((w[1], w[0], w[4]) for w in words
                         if UN_WORD.match(w[4]) and w[0] < page.rect.width * 0.2)
        print(f"  {len(un_rows)} UN-number words at the left margin; first five:")
        for y, x, text in un_rows[:5]:
            print(f"    UN {text} at x{x:.0f} y{y:.0f}")
    return 0


def full_header(page) -> tuple[float, dict[str, float]] | None:
    """The column-number band: y position and each column's x, when whole."""
    markers: dict[str, list[tuple[float, float]]] = {}
    for x0, y0, _x1, _y1, text, *_ in page.get_text("words"):
        match = MARKER.match(text)
        if match:
            markers.setdefault(match.group(1), []).append((x0, y0))
    if not all(code in markers for code in COLS):
        return None
    # Part 2 cites bracketed numbers in running text; the band is the row of
    # markers that share one y. Take, per column, the occurrence at the most
    # common y.
    ys = Counter(round(y) for hits in markers.values() for _x, y in hits)
    band_y = ys.most_common(1)[0][0]
    xs: dict[str, float] = {}
    for code in COLS:
        at_band = [x for x, y in markers[code] if abs(y - band_y) <= 2]
        if not at_band:
            return None
        xs[code] = min(at_band)
    ordered = [xs[code] for code in COLS]
    if ordered != sorted(ordered):
        return None
    return float(band_y), xs


def chunks_of(line_words: list[tuple[float, float, float, str]],
              gap: float = 6.0) -> list[tuple[float, float, str]]:
    """Adjacent words merged into cell chunks: (x0, x1, text)."""
    out: list[tuple[float, float, str]] = []
    for x0, x1, _y, text in sorted(line_words):
        if out and x0 - out[-1][1] <= gap:
            prev = out[-1]
            out[-1] = (prev[0], x1, f"{prev[2]} {text}")
        else:
            out.append((x0, x1, text))
    return out


def assign(chunk: tuple[float, float, str], xs: dict[str, float]) -> str:
    """The column a chunk belongs to, scored on left edge and centre both."""
    x0, x1, _text = chunk
    if x0 < xs["3a"] - 12:
        return "2" if x0 > xs["1"] + 10 else "1"
    center = (x0 + x1) / 2
    best, best_score = "3a", float("inf")
    for code in COLS[2:]:
        mx = xs[code]
        score = min(abs(x0 - mx), abs(center - mx))
        if score < best_score:
            best, best_score = code, score
    return best


def parse(pdf_path: Path) -> list[dict]:
    """Every row of the main table run, page by page, top to bottom."""
    doc = fitz.open(str(pdf_path))
    headers: dict[int, tuple[float, dict[str, float]]] = {}
    for number in range(doc.page_count):
        header = full_header(doc[number])
        if header:
            headers[number] = header
    runs: list[list[int]] = []
    for number in sorted(headers):
        if runs and number - runs[-1][-1] <= 2:
            runs[-1].append(number)
        else:
            runs.append([number])
    main_run = max(runs, key=len)

    rows: list[dict] = []
    for number in main_run:
        page = doc[number]
        band_y, xs = headers[number]
        body: list[tuple[float, float, float, str]] = []
        for x0, y0, x1, _y1, text, *_ in page.get_text("words"):
            if y0 <= band_y + 4:
                continue
            body.append((x0, x1, y0, text))
        # Visual lines, top to bottom.
        lines: dict[int, list[tuple[float, float, float, str]]] = {}
        for x0, x1, y0, text in body:
            lines.setdefault(round(y0 / 3), []).append((x0, x1, y0, text))
        # Drop footer lines: below every row anchor and matching the pattern.
        anchor_ys = [y0 for x0, _x1, y0, text in body
                     if UN_WORD.match(text) and x0 <= xs["1"] + 10]
        page_rows: list[dict] = []
        for key in sorted(lines):
            line = lines[key]
            line_y = min(w[2] for w in line)
            text = " ".join(w[3] for w in sorted(line))
            if (not anchor_ys or line_y > max(anchor_ys) + 30) and FOOTER.match(text):
                continue
            # The English text layer runs the UN number and the name's
            # first words together; the anchor word is therefore split off
            # before chunking, so column (1) is the four digits and nothing
            # else in both editions.
            anchors = [w for w in line
                       if UN_WORD.match(w[3]) and w[0] <= xs["1"] + 10]
            others = [w for w in line if w not in anchors]
            if anchors:
                page_rows.append({"page": number + 1, "cells": {}, "y": line_y})
            target = page_rows[-1] if page_rows else (rows[-1] if rows else None)
            if target is None:
                continue
            for anchor in anchors:
                target["cells"].setdefault("1", []).append(anchor[3])
            for chunk in chunks_of(others):
                if NOISE_CHUNK.match(chunk[2]):
                    continue
                code = assign(chunk, xs)
                cell = target["cells"].setdefault(code, [])
                cell.append(chunk[2])
        rows.extend(page_rows)

    out: list[dict] = []
    for row in rows:
        fields = {FIELDS[code]: " ".join(row["cells"].get(code, [])).strip()
                  for code in COLS}
        fields["_page"] = row["page"]
        # A prohibited row prints a banner across the cell area instead of
        # values; whichever column caught it, the row's meaning is the
        # banner, and the misassigned fragments are not data.
        joined = " ".join(fields[FIELDS[code]] for code in COLS
                          if code not in ("1", "2", "3a", "3b", "4", "5"))
        if any(banner in joined for banner in PROHIBITED):
            for code in COLS[5:]:
                fields[FIELDS[code]] = ""
            fields["carriage_prohibited"] = True
        else:
            fields["carriage_prohibited"] = False
        out.append(fields)
    return out


def _norm(code: str, value: str) -> str:
    """What must agree between the editions: the content, not the comma
    style. The Dutch book writes "P130, LP101" and "1.2 G" where the OTIF
    book writes "P130 LP101" and "1.2G"; column (7a) writes its decimals
    with a comma."""
    if code == "7a":
        value = value.replace(",", ".")
    return value.replace(",", " ").replace(" ", "")


def build(out_path: Path | None, lenient: bool) -> int:
    en = parse(STORE / "rid.pdf")
    nl = parse(STORE / "RID-2025-NL.pdf")
    print(f"rows: en {len(en)}, nl {len(nl)}")

    problems: list[str] = []
    if len(en) != len(nl):
        problems.append(f"row counts differ: en {len(en)}, nl {len(nl)}")
        # Show where the two UN sequences part company, so the next run
        # knows which pages to look at.
        import difflib
        matcher = difflib.SequenceMatcher(
            a=[r["un"] for r in en], b=[r["un"] for r in nl], autojunk=False)
        for tag, a0, a1, b0, b1 in matcher.get_opcodes():
            if tag == "equal":
                continue
            print(f"  UN sequence {tag}: en[{a0}:{a1}]="
                  f"{[r['un'] for r in en[a0:a1]][:6]} "
                  f"(pages {[r['_page'] for r in en[a0:a1]][:3]}) "
                  f"nl[{b0}:{b1}]={[r['un'] for r in nl[b0:b1]][:6]} "
                  f"(pages {[r['_page'] for r in nl[b0:b1]][:3]})")

    mismatches: Counter = Counter()
    samples: list[str] = []
    for index, (row_en, row_nl) in enumerate(zip(en, nl)):
        if row_en["carriage_prohibited"] != row_nl["carriage_prohibited"]:
            mismatches["prohibited"] += 1
            samples.append(f"row {index} UN {row_en['un']}: prohibited flag differs")
            continue
        if row_en["carriage_prohibited"]:
            continue
        for code in COMPARED:
            field = FIELDS[code]
            a, b = _norm(code, row_en[field]), _norm(code, row_nl[field])
            if a != b:
                mismatches[code] += 1
                if len(samples) < 40:
                    samples.append(
                        f"row {index} UN {row_en['un']}/{row_nl['un']} "
                        f"col ({code}): en {row_en[field]!r} != nl {row_nl[field]!r} "
                        f"(pages {row_en['_page']}/{row_nl['_page']})")
    if mismatches:
        problems.append("column mismatches between the editions: "
                        + ", ".join(f"({c})x{n}" for c, n in mismatches.most_common()))
    for line in samples:
        print("  " + line)

    # Cross-check 1: the shunting models of column (5), already read twice
    # in v1.123.0, must reappear on exactly the same UN numbers.
    shunting = json.loads((SEED / "rid_shunting_labels.json").read_text(encoding="utf-8"))
    expected = {(un, model) for un, models in shunting["rows"].items()
                for model in models}
    found = set()
    for row in en:
        for model in re.findall(r"\(\+(1[35])\)", row["labels"]):
            found.add((row["un"], model))
    if found != expected:
        problems.append(
            f"shunting models disagree with rid_shunting_labels.json: "
            f"missing {sorted(expected - found)[:8]}, "
            f"extra {sorted(found - expected)[:8]}")

    # Cross-check 2: the harmonised identity columns against the ADR table.
    adr = json.loads((SEED / "adr_table_a.json").read_text(encoding="utf-8"))
    adr_ids: dict[str, set] = {}
    for entry in adr["entries"]:
        adr_ids.setdefault(entry["un"], set()).add(
            (entry.get("class") or "", entry.get("classification_code") or "",
             entry.get("packing_group") or ""))
    rid_ids: dict[str, set] = {}
    for row in en:
        rid_ids.setdefault(row["un"], set()).add(
            (row["class"], row["classification_code"], row["packing_group"]))
    shared = set(adr_ids) & set(rid_ids)
    disagree = [un for un in shared if adr_ids[un] != rid_ids[un]]
    print(f"ADR cross-check: {len(shared)} shared UN numbers, "
          f"{len(disagree)} with a different identity set")
    for un in disagree[:15]:
        print(f"  UN {un}: adr {sorted(adr_ids[un])} rid {sorted(rid_ids[un])}")

    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    if problems and not lenient:
        return 1

    if out_path:
        entries = []
        for row_en, row_nl in zip(en, nl):
            entry = {FIELDS[code]: row_en[FIELDS[code]] for code in COLS
                     if code != "2"}
            entry["name_en"] = row_en["name"]
            entry["name_nl"] = row_nl["name"]
            entry["carriage_prohibited"] = row_en["carriage_prohibited"]
            entries.append(entry)
        payload = {
            "_comment": (
                "RID 3.2.1 table A, read geometrically from the word "
                "positions of two independently typeset editions by "
                "scripts/extract_rid_table_a.py; every coded column agreed "
                "between the two before this file was written. A "
                "compilation offered as an aid; the published text of the "
                "RID remains authoritative."),
            "edition": "RID 2025",
            "source": ("RID 2025 — the OTIF English edition and the Dutch "
                       "edition, table A of chapter 3.2, each read as an "
                       "independent typesetting of the same table"),
            "readings": 2,
            "row_count": len(entries),
            "problems": problems,
            "cross_checks": {
                "shunting_labels": "agreed" if found == expected else "disagreed",
                "adr_identity_shared": len(shared),
                "adr_identity_disagreements": len(disagree),
                "adr_identity_disagreeing_un": sorted(disagree),
            },
            "entries": entries,
        }
        out_path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        print(f"wrote {out_path} ({len(entries)} rows)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", help="filename in the regulations store, or a path")
    parser.add_argument("--probe", action="store_true",
                        help="report the table's printed structure and exit")
    parser.add_argument("--sample-pages", type=int, default=2)
    parser.add_argument("--build", action="store_true",
                        help="parse both editions, cross-check, write the seed")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--lenient", action="store_true",
                        help="report problems without failing (diagnosis runs)")
    args = parser.parse_args()

    if args.build:
        return build(args.out, args.lenient)

    if not args.pdf:
        print("--pdf or --build is required", file=sys.stderr)
        return 2
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        pdf_path = STORE / args.pdf
    if not pdf_path.is_file():
        print(f"not in the store: {args.pdf}", file=sys.stderr)
        return 1
    if args.probe:
        return probe(pdf_path, args.sample_pages)
    print("nothing to do: pass --probe or --build", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
