"""Build the eFTI seed from Commission Delegated Regulation (EU) 2024/2024.

Regulation (EU) 2020/1056 (electronic freight transport information) obliges
the authorities of the Member States to accept freight information
electronically from 9 July 2027, through certified eFTI platforms, and its
Article 7 had the Commission establish the **eFTI common data set** and the
**eFTI data subsets** — one subset per legal provision that asks a
transport operator for information. Commission Delegated Regulation (EU)
2024/2024 of 26 July 2024 (OJ L, 20.12.2024, ELI
http://data.europa.eu/eli/reg_del/2024/2024/oj) does that in its Annex:

* Table 1, the common data set: 681 data objects in a hierarchy — 148 data
  classes (ASBIE), 409 data elements (BBIE) and 123 supplementary
  components (SC) — each with its identifier ``eFTIxxx``, name, definition,
  data type, format and code list;
* Table 2, the subsets for the EU legal acts: which element each provision
  asks for and with what status — EU01 Regulation No 11 (the road transport
  document), EU02 Directive 92/106/EEC (combined transport), EU03
  Regulation (EC) No 1072/2009 (cabotage), EU05a/b/c the ADR, RID and ADN
  transport documents under Directive 2008/68/EC, EU06 air cargo security;
* Tables 3–29, the subsets for national provisions (not taken here);
* Table 30, the code lists and the codes allowed from each;
* Table 31, the business rules the subsets refer to.

This script reads the Official Journal PDF and writes the four tables as
JSON under ``backend/seed/efti/``. The regulation is reusable under the
Commission's reuse policy (Decision 2011/833/EU); the seed carries the ELI
and the sha256 of the file it was built from.

The PDF's tables are read with PyMuPDF's table finder, which returns the
rows of a printed table page by page; a cell that wraps onto a next page
arrives as a row with no hierarchy level, and is glued back onto the row
before it. Measured on the OJ text: every row has ten cells in Table 1 and
three plus three per subset in Table 2, and no identifier occurs twice.

Usage::

    python scripts/build_efti_seed.py "/path/to/OJ_L_202402024_EN_TXT.pdf"

The PDF itself is not part of the repository; the seed is.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import fitz  # pymupdf

OUT = Path(__file__).resolve().parents[1] / "backend" / "seed" / "efti"

#: Where each table sits in the Official Journal PDF (0-based page indexes,
#: measured by the "Table N" headings). Stated here rather than searched for
#: on every run, so a different edition fails loudly instead of silently
#: reading the wrong pages.
TABLE_1 = range(6, 62)
TABLE_2 = range(62, 102)
TABLE_30 = range(770, 780)
TABLE_31 = range(780, 789)

ELI = "http://data.europa.eu/eli/reg_del/2024/2024/oj"
TITLE = ("Commission Delegated Regulation (EU) 2024/2024 of 26 July 2024 supplementing "
         "Regulation (EU) 2020/1056 by establishing the eFTI common data set and eFTI "
         "data subsets (OJ L, 20.12.2024)")


def cell(value: object) -> str:
    return (str(value or "")).replace("\xad", "").replace("\n", " ").strip()


def rows_of(doc: fitz.Document, pages: range) -> list[list[str]]:
    out: list[list[str]] = []
    for index in pages:
        for table in doc[index].find_tables().tables:
            for row in table.extract():
                out.append([cell(x) for x in row])
    return out


def table_1(doc: fitz.Document) -> list[dict]:
    keys = ("h", "type", "lang", "id", "name", "definition", "data_type", "format",
            "code_list", "allowed")
    entries: list[dict] = []
    for row in rows_of(doc, TABLE_1):
        row = (row + [""] * 10)[:10]
        if row[0] == "H*":
            continue
        if row[0].isdigit() and row[1] in ("ABIE", "ASBIE", "BBIE", "SC"):
            entry = dict(zip(keys, row))
            entry["h"] = int(entry["h"])
            entry["id"] = entry["id"].replace(" ", "")
            entries.append(entry)
        elif entries:
            # A wrapped row: glue its text onto the entry it continues.
            for key, value in zip(keys[2:], row[2:]):
                if value:
                    entries[-1][key] = (entries[-1][key] + " " + value).strip()
    return entries


def table_2(doc: fitz.Document) -> dict:
    rows: dict[str, dict] = {}
    order: list[str] = []
    for index in TABLE_2:
        for table in doc[index].find_tables().tables:
            subsets: list[tuple[int, str]] = []
            for raw in table.extract():
                cells = [cell(x) for x in raw]
                if not cells[0] and any(c.startswith("EU") for c in cells):
                    subsets = [(k, c) for k, c in enumerate(cells) if c.startswith("EU")]
                    continue
                if cells[0] == "H*" or not cells[0].isdigit() or cells[1] not in ("ABIE", "ASBIE", "BBIE", "SC"):
                    continue
                ident = cells[2].replace(" ", "")
                entry = rows.setdefault(ident, {"h": int(cells[0]), "type": cells[1]})
                if ident not in order:
                    order.append(ident)
                for k, subset in subsets:
                    status, rule, codes = (cells[k:k + 3] + ["", "", ""])[:3]
                    if status or rule or codes:
                        entry[subset] = {"status": status, "rule": rule, "codes": codes}
    return {"order": order, "rows": rows}


def table_30(doc: fitz.Document) -> dict:
    lists: dict[str, dict] = {}
    last = None
    for row in rows_of(doc, TABLE_30):
        row = (row + ["", "", ""])[:3]
        if row[0].startswith("CL-"):
            lists[row[0]] = {"name": row[1], "allowed": row[2]}
            last = row[0]
        elif last and not row[0].startswith("eFTI Code"):
            for k, key in ((1, "name"), (2, "allowed")):
                if row[k]:
                    lists[last][key] = (lists[last][key] + " " + row[k]).strip()
    return lists


def table_31(doc: fitz.Document) -> dict:
    rules: dict[str, dict] = {}
    last = None
    for row in rows_of(doc, TABLE_31):
        row = (row + ["", "", ""])[:3]
        if row[0].startswith("BR-"):
            rules[row[0]] = {"elements": [e.strip() for e in row[1].split(";") if e.strip()],
                             "rule": row[2]}
            last = row[0]
        elif last and (row[1] or row[2]):
            if row[1]:
                rules[last]["elements"] += [e.strip() for e in row[1].split(";") if e.strip()]
            if row[2]:
                rules[last]["rule"] = (rules[last]["rule"] + " " + row[2]).strip()
    return rules


def main(path: str) -> int:
    pdf = Path(path)
    doc = fitz.open(pdf)
    source = {"title": TITLE, "eli": ELI, "file": pdf.name,
              "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "pages": len(doc)}
    elements = table_1(doc)
    subsets = table_2(doc)
    lists = table_30(doc)
    rules = table_31(doc)

    ids = [e["id"] for e in elements]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    if duplicates:
        raise SystemExit(f"duplicate identifiers in Table 1: {duplicates[:5]}")
    missing = [i for i in subsets["rows"] if i not in set(ids)]
    if missing:
        raise SystemExit(f"Table 2 names identifiers Table 1 does not have: {missing[:5]}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "common_data_set.json").write_text(
        json.dumps({"source": source, "table": 1, "elements": elements}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    (OUT / "subsets.json").write_text(
        json.dumps({"source": source, "table": 2, **subsets}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    (OUT / "code_lists.json").write_text(
        json.dumps({"source": source, "table": 30, "lists": lists}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    (OUT / "business_rules.json").write_text(
        json.dumps({"source": source, "table": 31, "rules": rules}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    kinds = Counter(e["type"] for e in elements)
    print(f"Table 1: {len(elements)} objects ({dict(kinds)}); Table 2: {len(subsets['rows'])} rows; "
          f"Table 30: {len(lists)} code lists; Table 31: {len(rules)} rules -> {OUT}")
    print("subset statuses:", {s: dict(Counter(r[s]['status'] for r in subsets['rows'].values() if s in r))
                               for s in ("EU01", "EU02", "EU03", "EU05a", "EU05b", "EU05c", "EU06")})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
