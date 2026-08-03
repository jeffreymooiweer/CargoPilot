"""Zoeken naar een bruikbare bron voor de NHM-goederencodes.

Vak 24 van de CIM vraagt een zescijferige NHM-code (Nomenclature Harmonisée
Marchandises, de goederennomenclatuur van de UIC voor het spoor). CargoPilot
heeft daar nu een vrij tekstveld voor met de mededeling dat de code niet uit een
omschrijving af te leiden is en dat de gebruiker hem moet opzoeken. Dat klopt,
maar het is geen antwoord.

Zescijferige codes verzinnen is hier geen optie. Een verkeerde NHM-code op een
spoorvrachtbrief is geen schoonheidsfoutje: de vervoerder rekent er zijn tarief
mee en de douane leest hem. Daarom eerst meten of er een bron ís die we mogen
en kunnen gebruiken, voordat er ook maar iets wordt vastgelegd — dezelfde
volgorde die bij de Dangerous Goods List heeft gewerkt.

Wat deze verkenning van een bron wil weten:

1. Is hij bereikbaar en machinaal te lezen?
2. Draagt hij zescijferige codes met een omschrijving, of alleen hoofdstukken?
3. Hoeveel codes zijn het, en dekken ze de goederen die CargoPilot kent?
4. Onder welke voorwaarden staat hij er — de code-met-omschrijving is een
   feitelijke tabel, maar dat moet wel per bron worden vastgesteld.

Draait via GitHub Actions, omdat de ontwikkelomgeving geen uitgaand netwerk
heeft. Deze verkenning legt niets vast; zij rapporteert alleen.

Gebruik::

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

# Kandidaten, van meest naar minst waarschijnlijk bruikbaar. De NHM volgt de
# hoofdstukindeling van het geharmoniseerd systeem (HS/GN), dus een GN-bron
# levert in elk geval de vier eerste cijfers en de omschrijvingen; de laatste
# twee cijfers zijn NHM-eigen.
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

# Een NHM-code is zes cijfers. Zonder die vorm heeft een bron ons niets te
# bieden voor vak 24.
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
    # Een lijst zonder omschrijvingen is voor een gebruiker onbruikbaar; die
    # moet aan de tekst kunnen zien wát hij kiest.
    print(f"  bevat woorden naast codes: {'ja' if re.search(r'[A-Za-z]{6,}', text) else 'nee'}")
    print(f"  eerste 300 tekens: {text[:300]!r}")


def coverage_hint() -> None:
    """Waar het uiteindelijk om gaat: dekt een bron ónze goederen?

    CargoPilot kent zo'n 400 materialen. Een NHM-lijst die staal, hout, cement
    en chemie dekt is bruikbaar, ook als hij niet volledig is; een lijst die dat
    niet doet, lost het probleem niet op.
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
