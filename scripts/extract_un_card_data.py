#!/usr/bin/env python3
"""Read the per-substance data out of the UN cards into a seed file.

The cards in `un_cards/` are laid out as label/value pairs, which makes them a
usable source for the fields CargoPilot has been missing per substance:

  marine pollutant   column 4 of the Dangerous Goods List
  stowage codes      SW…, column 16a
  segregation codes  SG…, column 16b — until now the app knew only the
                     segregation *groups* and had to point at the DGL itself
  bulk carriage      whether the substance may travel in bulk
  tank type          the IMO tank instruction, where one applies

The EmS code is read too, but only to cross-check `ems.json`, which comes from
the official EmS Guide and stays the authority. A disagreement between two
independent sources is worth knowing about.

    python scripts/extract_un_card_data.py --out backend/seed/dg/card_data.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

REPO = Path(__file__).resolve().parents[1]
CARDS = REPO / "un_cards"
EMS_DATABASE = REPO / "backend" / "seed" / "dg" / "ems.json"

CARD_NAME = re.compile(r"^un_(\d{4})(?:-(\d+))?\.pdf$", re.IGNORECASE)

# Codes as the cards print them: "(SW1)", "(SG27)", "(SGG9". The trailing
# bracket is optional because a list can run "…(SG35). Stow …".
STOWAGE_CODE = re.compile(r"\bSW(\d{1,2})\b")
SEGREGATION_CODE = re.compile(r"\bSG(\d{1,2})\b")
SEGREGATION_GROUP = re.compile(r"\bSGG(\d{1,2}a?)\b")

# Every label that starts a section, in the order the cards use them. Section
# text runs from one label to the next.
SECTIONS = [
    "UN number", "Shipping name", "Class", "Packing group", "Hazard labels",
    "Marine pollutant", "EmS", "Marking", "Tank provisions:", "Transport in bulk",
    "Orange panel", "Stowage and segregation", "Limited quantities (LQ)",
    "Excepted quantities (EQ)", "Packaging", "Mixed packaging", "Remarks",
    "Properties and", "observations", "Stowage", "Segregation",
    "Placarding of the", "transport unit", "Foodstuff", "IMDG - UN card",
]


def lines_of(path: Path) -> list[str]:
    with fitz.open(path) as pdf:
        text = pdf[0].get_text()
    return [line.strip() for line in text.split("\n") if line.strip()]


def value_after(lines: list[str], label: str) -> str:
    """The single value printed under a label."""
    try:
        index = lines.index(label)
    except ValueError:
        return ""
    if index + 1 >= len(lines):
        return ""
    following = lines[index + 1]
    return "" if following in SECTIONS else following


def section_text(lines: list[str], label: str, until: str) -> str:
    """The paragraph between two section labels."""
    try:
        start = lines.index(label)
    except ValueError:
        return ""
    try:
        end = lines.index(until, start + 1)
    except ValueError:
        end = len(lines)
    return " ".join(lines[start + 1:end]).strip()


def prefixed(value: str) -> str:
    """Normalise a free-text yes/no/maybe answer."""
    lowered = value.strip().lower()
    if lowered.startswith("yes"):
        return "yes"
    if lowered.startswith("no"):
        return "no"
    if lowered.startswith("maybe"):
        return "maybe"
    return ""


def parse_card(path: Path) -> dict[str, object] | None:
    lines = lines_of(path)
    if "UN number" not in lines:
        return None

    stowage = section_text(lines, "Stowage", "Segregation")
    segregation = section_text(lines, "Segregation", "Placarding of the")

    record: dict[str, object] = {
        "un": value_after(lines, "UN number").zfill(4),
        "name": value_after(lines, "Shipping name"),
        "class": value_after(lines, "Class"),
        "marine_pollutant": prefixed(value_after(lines, "Marine pollutant")),
        "ems": value_after(lines, "EmS"),
        "bulk": value_after(lines, "Transport in bulk").strip().lower(),
        "stowage_codes": sorted({f"SW{n}" for n in STOWAGE_CODE.findall(stowage)},
                                key=lambda c: int(c[2:])),
        "segregation_codes": sorted({f"SG{n}" for n in SEGREGATION_CODE.findall(segregation)},
                                    key=lambda c: int(c[2:])),
        "segregation_groups": sorted({f"SGG{n}" for n in SEGREGATION_GROUP.findall(segregation)},
                                     key=lambda c: (int(c[3:].rstrip("a")), c)),
        "stowage_text": stowage,
        "segregation_text": segregation,
    }
    tank = value_after(lines, "Tank provisions:")
    if tank and tank != "–":
        record["tank_provisions"] = tank
    return record


def merge(records: list[dict[str, object]]) -> dict[str, object]:
    """Fold the cards of one UN number into a single entry.

    Where the variants agree, one value. Where they differ — a substance whose
    packing groups are stowed differently — keep every value rather than pick
    one, the same rule the rest of the app follows.
    """
    merged: dict[str, object] = {}
    for field in ("marine_pollutant", "ems", "bulk", "class"):
        values = [r[field] for r in records if r.get(field)]
        unique = list(dict.fromkeys(values))
        if len(unique) == 1:
            merged[field] = unique[0]
        elif unique:
            merged[field] = unique  # genuinely differs per variant
    for field in ("stowage_codes", "segregation_codes", "segregation_groups"):
        codes: list[str] = []
        for record in records:
            for code in record[field]:  # type: ignore[index]
                if code not in codes:
                    codes.append(code)
        if codes:
            merged[field] = codes
    for field in ("stowage_text", "segregation_text"):
        texts = list(dict.fromkeys(str(r.get(field) or "") for r in records if r.get(field)))
        if texts:
            merged[field] = texts[0] if len(texts) == 1 else texts
    names = list(dict.fromkeys(r["name"] for r in records if r.get("name")))
    if names:
        merged["name"] = names[0]
    merged["cards"] = len(records)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cards", default=str(CARDS))
    parser.add_argument("--out", default="backend/seed/dg/card_data.json")
    args = parser.parse_args()

    directory = Path(args.cards)
    files = sorted(p for p in directory.glob("un_*.pdf") if CARD_NAME.match(p.name))
    if not files:
        print(f"No cards in {directory}", file=sys.stderr)
        return 1

    by_un: dict[str, list[dict[str, object]]] = {}
    failed: list[str] = []
    for path in files:
        try:
            record = parse_card(path)
        except Exception as exc:  # noqa: BLE001 - one bad card must not stop 2849
            failed.append(f"{path.name}: {type(exc).__name__}: {exc}")
            continue
        if record is None:
            failed.append(f"{path.name}: no UN number field")
            continue
        filename_un = CARD_NAME.match(path.name).group(1)  # type: ignore[union-attr]
        if record["un"] != filename_un:
            failed.append(f"{path.name}: card says UN {record['un']}")
            continue
        by_un.setdefault(filename_un, []).append(record)

    entries = {un: merge(records) for un, records in sorted(by_un.items())}

    # Cross-check the EmS codes against the official EmS Guide.
    ems_source = json.loads(EMS_DATABASE.read_text(encoding="utf-8"))["entries"]
    agree = differ = only_card = 0
    disagreements: list[str] = []
    for un, entry in entries.items():
        card_ems = entry.get("ems")
        if not isinstance(card_ems, str) or not card_ems:
            continue
        official = ems_source.get(un)
        if not isinstance(official, dict) or "fire" not in official:
            only_card += 1
            continue
        expected = f"{official['fire']}, {official['spillage']}"
        def canonical(value: str) -> str:
            return re.sub(r"[^A-Z]", "", value.upper())

        if canonical(card_ems) == canonical(expected):
            agree += 1
        else:
            differ += 1
            if len(disagreements) < 20:
                disagreements.append(f"UN {un}: card {card_ems!r} vs guide {expected!r}")

    counts = Counter()
    for entry in entries.values():
        counts["marine_pollutant_yes"] += entry.get("marine_pollutant") == "yes"
        counts["with_stowage_codes"] += bool(entry.get("stowage_codes"))
        counts["with_segregation_codes"] += bool(entry.get("segregation_codes"))
        counts["with_segregation_groups"] += bool(entry.get("segregation_groups"))
        # Bulk carriage is spelled as a BK instruction ("bk2", "bk2 / bk3");
        # anything else on these cards is "not allowed".
        counts["bulk_allowed"] += "bk" in str(entry.get("bulk", ""))

    summary = {
        "cards_read": len(files) - len(failed),
        "un_numbers": len(entries),
        "failed": len(failed),
        "ems_cross_check": {"agree": agree, "differ": differ, "not_in_guide": only_card},
        **counts,
    }
    print(json.dumps(summary, indent=2))
    if failed:
        print("\nfailed:", *failed[:20], sep="\n  ")
    if disagreements:
        print("\nEmS disagreements (guide wins):", *disagreements, sep="\n  ")

    payload = {
        "_comment": (
            "Per-substance data read from the UN cards in un_cards/ by "
            "scripts/extract_un_card_data.py. Marine pollutant, stowage (SW) and "
            "segregation (SG) codes, bulk carriage. The EmS code here is not used: "
            "ems.json, from the official EmS Guide, is the authority."
        ),
        "source": "Cantell IMDG UN cards, 2023 edition (IMDG 41-22)",
        "summary": summary,
        "entries": entries,
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
