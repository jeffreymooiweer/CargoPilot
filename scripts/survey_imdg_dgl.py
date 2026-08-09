"""Inventarisatie van de Dangerous Goods List in het 42-24-document.

Dit is de eerste van twee stappen en legt bewust niets vast. De lijst beslaat
zo'n 170 pagina's met achttien kolommen, en een parser die stilzwijgend één
kolom verkeerd leest is gevaarlijker dan helemaal geen parser: dan staan er
2.300 stoffen met een verkeerde scheidingscode in de app zonder dat iemand het
merkt. Dus eerst meten:

1. Waar begint en eindigt de lijst precies?
2. Waar liggen de kolomgrenzen? Die worden afgeleid uit de x-posities van de
   koptekst en gecontroleerd tegen de x-posities van de gegevens zelf.
3. Welke UN-nummers levert de lijst op, en hoe verhoudt zich dat tot de 2.336
   nummers die we nu uit de UN-kaarten van 41-22 kennen? Elk verschil is een
   aanwijzing: een gemiste pagina, een rij die anders is opgemaakt, of een
   echte wijziging in 42-24.

De verkenning meldde eerder dat UN 1361, 3551 en 3560 ontbraken terwijl er
gaten in de paginareeks zaten op p734 en p757. Juist die drie zijn
42-24-wijzigingen, dus dat wijst eerder op een leesfout dan op ontbrekende
gegevens; deze inventarisatie moet dat uitwijzen.

Draait via GitHub Actions, omdat de ontwikkelomgeving geen uitgaand netwerk
heeft. Wat er uiteindelijk in de repo landt zijn afgeleide gegevens, nooit de
regelgevingstekst.

Gebruik::

    python scripts/survey_imdg_dgl.py
    python scripts/survey_imdg_dgl.py --sample-pages 600,650 --pdf /tmp/imdg.pdf
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

SOURCE_URL = "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf"
UA = {"User-Agent": "CargoPilot data survey (github.com/jeffreymooiweer/CargoPilot)"}
CARD_DATA = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg" / "card_data.json"

# Een pagina van de lijst draagt deze koppen. Ze staan er niet allemaal op elke
# pagina — de lijst loopt over twee tegenover elkaar liggende pagina's — dus
# twee treffers is genoeg om een pagina als lijstpagina aan te merken.
HEADINGS = ["UN No.", "Proper shipping name", "Class or division", "Subsidiary",
            "Packing group", "Special provisions", "Limited and excepted",
            "Packagings and IBCs", "Portable tanks", "EmS", "Stowage and handling",
            "Segregation", "Properties and observations"]

# Een rij begint met een UN-nummer op een eigen tekstregel. Zonder re.MULTILINE
# matcht ^ alleen het begin van de hele paginatekst; dat heeft deze verkenning
# al twee keer op een vals-negatief gezet.
ROW_START = re.compile(r"^[ \t]*(\d{4})(?:[ \t]|$)", re.M)


def download(url: str, target: Path, timeout: int = 600) -> Path:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def known_un_numbers() -> set[str]:
    """De UN-nummers die we nu uit de kaarten van 41-22 kennen."""
    try:
        return set(json.loads(CARD_DATA.read_text(encoding="utf-8"))["entries"])
    except (OSError, ValueError, KeyError):  # pragma: no cover - seed ontbreekt
        return set()


def list_pages(document) -> list[int]:
    """Pagina's die tot de lijst zelf horen, op koptekst herkend.

    Op koppen zoeken in plaats van op rijen: de scheidingsgroeplijsten van
    3.1.4.4 beginnen ook met UN-nummers en horen hier niet bij.
    """
    pages = []
    for index in range(document.page_count):
        text = document[index].get_text()
        if sum(1 for heading in HEADINGS if heading in text) >= 2:
            pages.append(index + 1)
    return pages


def contiguous(pages: list[int]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for page in pages:
        if ranges and page == ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], page)
        else:
            ranges.append((page, page))
    return ranges


def column_positions(document, pages: list[int], limit: int = 40) -> list[tuple[float, int]]:
    """De x-posities waarop tekst begint, geteld over een aantal lijstpagina's.

    In een vaste tabelopmaak clusteren die posities rond de kolomgrenzen. Wat
    er tussen de clusters zit is doorlopende tekst binnen een kolom.
    """
    counts: Counter[float] = Counter()
    for page in pages[:limit]:
        for word in document[page - 1].get_text("words"):
            counts[round(word[0], 1)] += 1
    return sorted(counts.items())


def cluster(positions: list[tuple[float, int]], gap: float = 4.0,
            floor: int = 20) -> list[tuple[float, float, int]]:
    """Naburige x-posities samennemen tot kolomkandidaten."""
    clusters: list[list[tuple[float, int]]] = []
    for x, count in positions:
        if count < floor:
            continue
        if clusters and x - clusters[-1][-1][0] <= gap:
            clusters[-1].append((x, count))
        else:
            clusters.append([(x, count)])
    return [(c[0][0], c[-1][0], sum(n for _, n in c)) for c in clusters]


def survey(path: Path, sample_pages: list[int]) -> int:
    import fitz

    print(f"bron: {path} ({path.stat().st_size} bytes)")
    with fitz.open(path) as document:
        print(f"{document.page_count} pagina's\n")

        pages = list_pages(document)
        if not pages:
            print("Geen lijstpagina's herkend aan hun koptekst.")
            return 1
        ranges = contiguous(pages)
        print(f"== lijstpagina's: {len(pages)} ==")
        print("  " + ", ".join(f"p{a}-p{b}" if a != b else f"p{a}" for a, b in ranges))

        # Gaten binnen het bereik zijn verdacht: een lijst loopt door.
        gaps = [p for p in range(pages[0], pages[-1] + 1) if p not in set(pages)]
        print(f"  gaten binnen het bereik: {gaps or 'geen'}")
        for page in gaps[:6]:
            first = document[page - 1].get_text().strip().splitlines()[:3]
            print(f"    p{page}: {' | '.join(line.strip() for line in first)}")

        print("\n== kolomposities over de eerste 40 lijstpagina's ==")
        clusters = cluster(column_positions(document, pages))
        for start, end, count in clusters:
            print(f"  x {start:7.1f} - {end:7.1f}   {count:6d} woorden")

        for number in sample_pages:
            if not 0 < number <= document.page_count:
                continue
            print(f"\n===== p{number}: koptekst met positie =====")
            words = document[number - 1].get_text("words")
            top = [w for w in words if w[1] < 120]
            for word in sorted(top, key=lambda w: (round(w[1], 1), w[0]))[:80]:
                print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")

        # Dekking: wat de lijst oplevert tegenover wat we al hebben.
        found: dict[str, int] = {}
        rows_per_page: dict[int, int] = {}
        for page in pages:
            numbers = [m.group(1) for m in ROW_START.finditer(document[page - 1].get_text())]
            rows_per_page[page] = len(numbers)
            for un in numbers:
                found.setdefault(un, page)

        known = known_un_numbers()
        print(f"\n== dekking ==")
        print(f"  UN-nummers in de lijst : {len(found)}")
        print(f"  UN-nummers uit de kaarten (41-22): {len(known)}")
        print(f"  rijen totaal           : {sum(rows_per_page.values())}")
        if known:
            missing = sorted(known - set(found))
            extra = sorted(set(found) - known)
            print(f"  wel op kaart, niet in de lijst: {len(missing)}")
            print(f"    {missing[:40]}{' …' if len(missing) > 40 else ''}")
            print(f"  wel in de lijst, geen kaart   : {len(extra)}")
            print(f"    {extra[:40]}{' …' if len(extra) > 40 else ''}")

        # De drie die de eerdere verkenning miste, apart nagelopen: staan ze
        # ergens in het document, en zo ja hoe zijn ze daar opgemaakt?
        print("\n== de nummers die eerder ontbraken ==")
        for un in ("1361", "3551", "3552", "3556", "3560", "0514", "3553"):
            page = found.get(un)
            if page:
                print(f"  UN {un}: rij op p{page}")
                continue
            hits = [i + 1 for i in range(document.page_count)
                    if re.search(rf"\b{un}\b", document[i].get_text())]
            inside = [p for p in hits if p in set(pages)]
            print(f"  UN {un}: geen rij. Komt voor op {hits[:8]}"
                  f"{' …' if len(hits) > 8 else ''}; daarvan lijstpagina's: {inside[:8]}")
            for p in inside[:1]:
                context = document[p - 1].get_text()
                spot = context.find(un)
                print(f"      context p{p}: ...{context[max(0, spot - 120):spot + 160]!r}...")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, help="Al gedownload bestand hergebruiken")
    parser.add_argument("--sample-pages", default="600,601",
                        help="Lijstpagina's waarvan de koptekst wordt afgedrukt")
    args = parser.parse_args(argv)

    path = args.pdf or download(SOURCE_URL, Path("/tmp/imdg_42_24.pdf"))
    pages = [int(p) for p in args.sample_pages.split(",") if p.strip().isdigit()]
    return survey(path, pages)


if __name__ == "__main__":
    sys.exit(main())
