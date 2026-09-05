"""Build the NHM seed from the UIC correspondence table "NST 2007 - NHM 2025".

Box 24 of the CIM consignment note asks for the NHM code (Nomenclature
Harmonisée Marchandises, the UIC's goods nomenclature for rail) in six
digits. The table the UIC publishes to relate the NHM to Eurostat's NST 2007
transport statistics carries every NHM 2025 position with its English and
French label, and the NHM's first six digits are the Harmonized System
subheading. That table is the source; this script turns it into
``backend/seed/nhm.json``, one entry per six-digit code.

How a six-digit code gets its label, measured on the 2025 table:

* 1,829 codes have a row of their own at six digits;
* 3,810 codes appear only as eight-digit positions, the one ending in
  ``00`` being the subheading itself — that row's label is taken;
* one code (070200, tomatoes) appears only as three eight-digit positions
  and none ending in ``00``; the four-digit heading's label is taken;
* 28 railway-specific positions in chapter 99 (groupage freight, empty
  wagons, loaded semi-trailers …) are eight digits ending in ``00`` and are
  kept at six.

Each entry also carries the NST 2007 group (81 positions) the table maps
the code to, for the statistics an installation with a history may want
one day.

Usage::

    python scripts/build_nhm_seed.py "/path/to/NST 2007 - NHM 2025.xlsx"

The workbook itself is not part of the repository; the seed is.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

OUT = Path(__file__).resolve().parents[1] / "backend" / "seed" / "nhm.json"


def digits(value: object) -> str:
    return re.sub(r"\D", "", str(value or ""))


def main(path: str) -> int:
    ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header, body = rows[0], rows[1:]
    assert header[0] == "NHM_2025_Code" and header[3] == "Label NHM_2025 (EN)", header

    six: dict[str, dict] = {}
    eight: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    four: dict[str, dict] = {}
    for row in body:
        code = digits(row[2])
        entry = {"en": (row[3] or "").strip(), "fr": (row[4] or "").strip(),
                 "nst": (str(row[8]) if row[8] else "")}
        if len(code) == 6:
            six[code] = entry
        elif len(code) == 8:
            eight[code[:6]].append((code, entry))
        elif len(code) == 4:
            four[code] = entry

    out = []
    for code in sorted(set(six) | set(eight)):
        if code in six and six[code]["en"]:
            entry = six[code]
        else:
            completion = [e for c, e in eight[code] if c.endswith("00") and e["en"]]
            if completion:
                entry = completion[0]
            elif four.get(code[:4], {}).get("en"):
                entry = {**four[code[:4]], "nst": eight[code][0][1]["nst"]}
            else:
                raise SystemExit(f"no label for {code}")
        out.append({"code": code, "en": entry["en"], "fr": entry["fr"], "nst": entry["nst"]})

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"{len(out)} codes written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
