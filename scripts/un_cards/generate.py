"""Generate CargoPilot UN cards: UN####_<MODALITY>.pdf plus a report.

Usage (from the repository root):

    python scripts/un_cards/generate.py --un 1203 --out /tmp/cards
    python scripts/un_cards/generate.py --un 1203,1017,0234 --modalities ADR,ADN

Each UN number × modality yields one PDF named ``UN####_<MODALITY>.pdf`` in a
per-modality directory; a UN number with several transport entries in the
same table yields several pages inside that one PDF. A modality whose source
table this repository does not hold **fails** for that combination — the
report records the reason verbatim — because an invented card is worse than
an absent one. The report (``generation-report.json``) lists per combination:
``generated`` (with page count and SHA-256), ``failed`` (with the reason), so
a run's outcome is machine-checkable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from un_cards.render import render_card_pdf
from un_cards.sources import adn, adr, icao, imdg, rid
from un_cards.sources.base import MODALITIES, SourceUnavailable

ADAPTERS = {
    "ADR": adr.cards,
    "RID": rid.cards,
    "ADN": adn.cards,
    "IMDG": imdg.cards,
    "ICAO": icao.cards,
}


def generate(un_numbers: list[str], modalities: list[str], out_dir: Path) -> dict:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report: dict = {
        "generated_at": generated_at,
        "results": [],
        "summary": {"generated": 0, "failed": 0},
    }
    for un in un_numbers:
        un = un.strip().upper().removeprefix("UN").strip()
        for modality in modalities:
            entry: dict = {"un_number": un, "modality": modality}
            try:
                pages = ADAPTERS[modality](un)
                directory = out_dir / modality
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / f"UN{un}_{modality}.pdf"
                render_card_pdf(path, pages, generated_at)
                content = path.read_bytes()
                if not content.startswith(b"%PDF"):
                    raise RuntimeError("output is not a PDF")
                entry.update(
                    status="generated",
                    file=f"{modality}/{path.name}",
                    pages=len(pages),
                    size=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    regulation=pages[0].regulation,
                )
                report["summary"]["generated"] += 1
            except SourceUnavailable as exc:
                entry.update(status="failed", reason=str(exc))
                report["summary"]["failed"] += 1
            report["results"].append(entry)
    (out_dir / "generation-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--un", required=True,
                        help="comma-separated UN numbers, e.g. 1203,1017")
    parser.add_argument("--modalities", default=",".join(MODALITIES),
                        help="comma-separated subset of ADR,RID,ADN,IMDG,ICAO")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    modalities = [m.strip().upper() for m in args.modalities.split(",") if m.strip()]
    unknown = [m for m in modalities if m not in ADAPTERS]
    if unknown:
        parser.error(f"unknown modalities: {', '.join(unknown)}")

    args.out.mkdir(parents=True, exist_ok=True)
    report = generate(args.un.split(","), modalities, args.out)
    print(json.dumps(report["summary"], indent=2))
    for row in report["results"]:
        marker = "ok " if row["status"] == "generated" else "FAIL"
        detail = row.get("file") or row.get("reason", "")
        print(f"  [{marker}] UN{row['un_number']} {row['modality']}: {detail}")
    return 0 if report["summary"]["generated"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
