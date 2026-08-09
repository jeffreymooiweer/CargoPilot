"""Looking for a usable source for the NHM goods codes.

Box 24 of the CIM asks for a six-digit NHM code (Nomenclature Harmonisée
Marchandises, the UIC's goods nomenclature for rail). CargoPilot currently has a
free text field for it with a note that the code cannot be derived from a
description and that the user has to look it up. That is true, but it is not an
answer.

Inventing six-digit codes is not an option here. A wrong NHM code on a rail
waybill is no blemish: the carrier calculates its tariff with it and customs read
it. So first measure whether there *is* a source we may and can use, before
anything is recorded — the same order that worked for the Dangerous Goods List.

What this survey wants to know about a source:

1. Is it reachable and readable by machine?
2. Does it carry six-digit codes with a description, or only chapters?
3. How many codes are there, and do they cover the goods CargoPilot knows?
4. On what terms is it published — the code-with-description is a factual table,
   but that has to be established per source.

Runs via GitHub Actions, because the development environment has no outbound
network. This survey records nothing; it only reports.

Usage::

    python scripts/probe_nhm_sources.py
    python scripts/probe_nhm_sources.py --url https://example.org/nhm.csv
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

UA = {"User-Agent": "CargoPilot data survey (github.com/jeffreymooiweer/CargoPilot)"}

# Candidates, from most to least likely to be usable. The NHM follows the chapter
# structure of the Harmonised System (HS/CN), so a CN source supplies at least the
# first four digits and the descriptions; the last two digits are NHM-specific.
CANDIDATES = [
    {
        "name": "EU RAMON — Combined Nomenclature (CN), de basis onder de NHM",
        "url": "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT/CN",
        "note": "Officiële EU-nomenclatuur, openbaar. Levert CN-codes; NHM wijkt "
                "op de laatste twee cijfers af.",
    },
    {
        "name": "UIC NHM — de nomenclatuur zelf",
        "url": "https://uic.org/freight/rail-freight-nomenclature",
        "note": "De bron die telt. Waarschijnlijk geen open gegevensbestand; "
                "dit meet of er iets machinaal leesbaars achter zit.",
    },
    {
        "name": "Eurostat SDMX — goederennomenclatuur voor vervoerstatistiek",
        "url": "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT/NST07",
        "note": "NST/R-hoofdgroepen, grover dan NHM maar wel open en "
                "eenduidig — bruikbaar als vangnet, niet als vervanging.",
    },
]

# An NHM code is six digits. Without that shape a source has nothing to offer us
# for box 24.
NHM_CODE = re.compile(r"\b\d{6}\b")


def fetch(url: str, timeout: int = 60) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        return error.code, error.read()[:2000], error.headers.get("Content-Type", "")
    except Exception as error:  # pragma: no cover - netwerk
        return 0, str(error).encode(), ""


def describe(name: str, url: str, note: str) -> None:
    print(f"\n===== {name} =====")
    print(f"  {url}")
    print(f"  {note}")

    status, body, content_type = fetch(url)
    print(f"  status {status}, {len(body)} bytes, type {content_type or '—'}")
    if status != 200 or not body:
        print("  → niet bruikbaar langs deze weg.")
        return

    text = body.decode("utf-8", errors="replace")
    codes = sorted(set(NHM_CODE.findall(text)))
    print(f"  zescijferige codes gevonden: {len(codes)}")
    if codes:
        print(f"    voorbeeld: {codes[:8]}")
    # A list without descriptions is unusable for a user; they have to be able to
    # see from the text *what* they are choosing.
    print(f"  bevat woorden naast codes: {'ja' if re.search(r'[A-Za-z]{6,}', text) else 'nee'}")
    print(f"  eerste 300 tekens: {text[:300]!r}")


def coverage_hint() -> None:
    """What it ultimately comes down to: does a source cover *our* goods?

    CargoPilot knows some 400 materials. An NHM list covering steel, timber,
    cement and chemicals is usable, even if it is not complete; a list that does
    not do that does not solve the problem.
    """
    seed = Path(__file__).resolve().parents[1] / "backend" / "seed" / "materials.json"
    try:
        materials = json.loads(seed.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("\n(materials.json niet gevonden; dekkingsvraag overgeslagen)")
        return
    names = materials if isinstance(materials, list) else materials.get("entries", [])
    print(f"\n===== waartegen een bron moet worden afgezet =====")
    print(f"  materialen in CargoPilot: {len(names)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Eén eigen bron beproeven in plaats van de lijst")
    args = parser.parse_args(argv)

    if args.url:
        describe("opgegeven bron", args.url, "handmatig meegegeven")
    else:
        for candidate in CANDIDATES:
            describe(candidate["name"], candidate["url"], candidate["note"])

    coverage_hint()
    print("\nDeze verkenning legt niets vast. Zolang er geen bron is die "
          "zescijferige codes mét omschrijving levert, blijft vak 24 een "
          "vrij tekstveld met een vormcontrole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
