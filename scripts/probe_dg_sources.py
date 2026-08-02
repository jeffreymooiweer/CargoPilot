"""Verkenning van openbare bronnen voor gevaarlijke-stoffengegevens.

Dit script haalt niets binnen dat in de repo terechtkomt. Het kijkt of een bron
bestaat, hoe groot zij is en of zij machinaal te lezen valt, en zet die uitkomst
op de uitvoer. Bedoeld om via GitHub Actions te draaien, omdat de
ontwikkelomgeving geen uitgaand netwerk heeft.

Twee vragen:

1. Publiceert Cantell een kaartenset van een nieuwere IMDG-editie dan
   ``imdg_2023``? Die set is de bron van ``backend/seed/dg/card_data.json``
   (Amendment 41-22). Een 42-24-set zou de hele stof-specifieke laag in één keer
   bijwerken, langs dezelfde weg die we al gebruiken.
2. Is de Dangerous Goods List van de UN-modelvoorschriften Rev.23 te parsen?
   UNECE publiceert die uitgave gratis en IMDG 42-24 is ermee geharmoniseerd,
   dus zij dekt elke kolom die niet IMDG-eigen is: klasse, verpakkingsgroep,
   etiketten, bijzondere bepalingen, LQ/EQ en verpakkingsinstructies. Wat zij
   niet dekt is even belangrijk om te weten: EmS, stuwagecategorie, de SW- en
   SG-codes en de scheidingsgroepen staan alleen in de IMDG-code zelf.

3. Wat staat er in het amendementsdocument dat CEPA — de werkgeversorganisatie
   van de haven van Antwerpen — openbaar op haar eigen site publiceert? Dit
   script stelt alleen vast wát het is: uitgever, omvang, welke hoofdstukken.
   Of het om de volledige codetekst gaat of om een wijzigingsoverzicht maakt
   voor ons uit, want alleen feitelijke gegevens komen in de repo terecht en
   nooit de regelgevingstekst zelf.

Gebruik::

    python scripts/probe_dg_sources.py cantell
    python scripts/probe_dg_sources.py model-regs --sample-pages 60,61,120
    python scripts/probe_dg_sources.py cepa
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CANTELL = "https://www.cantell.dk/image/catalog/Stofliste"
UNECE = "https://unece.org/sites/default/files/2023-08"
VOL1 = f"{UNECE}/ST-SG-AC10-1r23e_Vol1_WEB.pdf"
VOL2 = f"{UNECE}/ST-SG-AC10-1r23e_Vol2_WEB.pdf"
CEPA = "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf"

# Wat er op cepa.be staat is MSC 108/20/Add.2, annex 8: de volledige
# geconsolideerde tekst van Amendment 42-24, 954 pagina's. Uit de inhoudsopgave
# volgen de codepagina's hieronder. De PDF telt door over het voorwerk heen, dus
# het echte paginanummer ligt een stuk of twaalf hoger; find_page_offset() meet
# dat in plaats van het te gokken.
CODE_PAGES = {
    "7.1.3 Stowage categories": 476,
    "7.1.5 Stowage codes": 482,
    "7.1.6 Handling codes": 483,
    "7.2.4 Segregation table": 485,
    "7.2.5 Segregation groups": 486,
    "7.2.6 Special segregation provisions and exemptions": 486,
    "7.2.7 Segregation of goods of class 1": 489,
    "7.2.8 Segregation codes": 490,
    "Appendix 2 (Dangerous Goods List)": 564,
}

# De secties die we willen kunnen controleren. 7.2.4, 7.2.6.3 en 7.2.7.1.4
# dragen de scheidingstabellen; 3.1.4.4 de scheidingsgroepen; 7.1.5 de
# stuwagecodes en 7.1.6 de behandelingscodes, die we per stof wel hebben maar
# zonder hun omschrijving.
SECTIONS_OF_INTEREST = ["3.1.4.4", "3.2.1", "3.3.1", "7.1.3", "7.1.5", "7.1.6",
                        "7.2.3.1", "7.2.4", "7.2.5", "7.2.6.3", "7.2.7.1.4", "7.2.8"]

# De vermeldingen die Amendment 42-24 toevoegt. Staan ze in Rev.23, dan is de
# gratis uitgave genoeg voor alles behalve de IMDG-eigen kolommen.
NEW_UN_NUMBERS = ["0514", "3551", "3552", "3553", "3554",
                  "3555", "3556", "3557", "3558", "3559", "3560"]

# Bijzondere bepalingen onder 900 komen uit de modelvoorschriften; die tekst
# ontbreekt nu aan onze kant. De 9xx-reeks is IMDG-eigen en staat er niet in.
NEW_SPECIAL_PROVISIONS = ["375", "400", "401", "402", "403",
                          "404", "405", "406", "407", "408", "409"]

UA = {"User-Agent": "CargoPilot source probe (github.com/jeffreymooiweer/CargoPilot)"}


def head(url: str, timeout: int = 25) -> tuple[int, int]:
    """(statuscode, aantal bytes). Een fout is een uitkomst, geen uitzondering."""
    request = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, len(response.read())
    except urllib.error.HTTPError as error:
        return error.code, 0
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, 0


def exists(url: str) -> bool:
    status, size = head(url)
    return status == 200 and size > 2000


def download(url: str, target: Path, timeout: int = 180) -> Path:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def card_url(collection: str, year: int, part: int) -> str:
    prefix = "IMDG_EN/imdg" if collection == "imdg" else "ADR_EN/adr"
    return f"{CANTELL}/{prefix}_{year}_-_en_part{part}.pdf"


def count_parts(collection: str, year: int, ceiling: int = 8192) -> int:
    """Hoeveel parts de set telt, via verdubbelen en dan binair zoeken.

    Sneller en beleefder dan duizenden losse verzoeken; de set van 2023 telde
    er 2.849, dus lineair aflopen is geen optie.
    """
    low = 1
    while low * 2 <= ceiling and exists(card_url(collection, year, low * 2)):
        low *= 2
    high = min(low * 2, ceiling + 1)
    while high - low > 1:
        middle = (low + high) // 2
        if exists(card_url(collection, year, middle)):
            low = middle
        else:
            high = middle
    return low


def probe_cantell() -> int:
    """Welke kaartensets Cantell publiceert, en hoe groot de nieuwste is."""
    print("== Cantell ==")
    available: list[tuple[str, int]] = []
    for collection, year in [("imdg", y) for y in (2027, 2026, 2025, 2024, 2023)] + \
                            [("adr", y) for y in (2027, 2025, 2023)]:
        url = card_url(collection, year, 1)
        status, size = head(url)
        verdict = f"BESTAAT ({size} bytes)" if status == 200 and size > 2000 \
            else f"afwezig (HTTP {status})"
        print(f"  {collection}_{year:<6} {verdict}")
        if status == 200 and size > 2000:
            available.append((collection, year))

    newest_imdg = next((y for c, y in available if c == "imdg"), None)
    if newest_imdg is None:
        print("\nGeen enkele IMDG-set bereikbaar.")
        return 1

    print(f"\nNieuwste IMDG-set: imdg_{newest_imdg}")
    if newest_imdg <= 2023:
        print("Dat is de editie die we al verwerkt hebben (Amendment 41-22).")
        print("Er is langs deze weg niets nieuws te halen.")
    else:
        parts = count_parts("imdg", newest_imdg)
        print(f"Omvang: ongeveer {parts} parts.")
        print("Dit is een nieuwere editie — de bestaande pijplijn van")
        print("scripts/fetch_un_cards.py kan haar rechtstreeks verwerken.")

    print(f"\n-- eerste kaart van imdg_{newest_imdg} --")
    print(read_pdf_text(card_url("imdg", newest_imdg, 1), Path("/tmp/card.pdf"))[:2000])
    return 0


def read_pdf_text(url: str, target: Path, page: int = 0) -> str:
    import fitz

    download(url, target)
    with fitz.open(target) as document:
        return document[page].get_text()


def probe_model_regulations(sample_pages: list[int]) -> int:
    """Of de Dangerous Goods List van Rev.23 machinaal te lezen is."""
    import fitz

    print("== UN-modelvoorschriften Rev.23, deel II (Dangerous Goods List) ==")
    path = download(VOL2, Path("/tmp/vol2.pdf"))
    print(f"  {path.stat().st_size} bytes")

    with fitz.open(path) as document:
        print(f"  {document.page_count} pagina's")

        for index in range(min(80, document.page_count)):
            if re.search(r"DANGEROUS GOODS LIST", document[index].get_text(), re.I):
                print(f"  'DANGEROUS GOODS LIST' voor het eerst op pagina {index + 1}")
                break

        found: dict[str, int] = {}
        for index in range(document.page_count):
            text = document[index].get_text()
            for un in NEW_UN_NUMBERS:
                if un not in found and re.search(rf"\b{un}\b", text):
                    found[un] = index + 1
        print(f"  nieuwe UN-nummers gevonden: {found}")
        missing = [un for un in NEW_UN_NUMBERS if un not in found]
        print(f"  ontbreekt: {missing or 'niets'}")

        for number in sample_pages:
            index = number - 1
            if not 0 <= index < document.page_count:
                continue
            page = document[index]
            print(f"\n===== PAGINA {number}: platte tekst =====")
            print(page.get_text())
            print(f"===== PAGINA {number}: woorden met x-positie (eerste 150) =====")
            for word in page.get_text("words")[:150]:
                print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")

    print("\n== Deel I (bijzondere bepalingen) ==")
    path = download(VOL1, Path("/tmp/vol1.pdf"))
    print(f"  {path.stat().st_size} bytes")
    with fitz.open(path) as document:
        print(f"  {document.page_count} pagina's")
        pending = list(NEW_SPECIAL_PROVISIONS)
        for index in range(document.page_count):
            text = document[index].get_text()
            for provision in list(pending):
                match = re.search(rf"^\s*{provision}\s+[A-Z(\"].{{0,700}}", text, re.M | re.S)
                if match:
                    print(f"\n--- SP{provision}, pagina {index + 1} ---")
                    print(match.group(0).strip())
                    pending.remove(provision)
        print(f"\n  niet teruggevonden: {pending or 'niets'}")
    return 0


def find_page_offset(document) -> int:
    """Verschil tussen het paginanummer in de voettekst en de index in de PDF.

    De inhoudsopgave verwijst naar codepagina's; PyMuPDF telt vanaf nul over het
    voorwerk heen. Meten is beter dan gokken: dit leest het nummer uit de
    voettekst van een stuk of wat pagina's in het midden en neemt het verschil
    dat het vaakst voorkomt.
    """
    from collections import Counter

    votes: Counter[int] = Counter()
    for index in range(200, min(document.page_count, 800), 17):
        lines = [line.strip() for line in document[index].get_text().splitlines() if line.strip()]
        # Het paginanummer staat op de eerste of laatste regel, los.
        for line in (lines[:2] + lines[-2:]) if lines else []:
            if line.isdigit() and 1 <= int(line) <= document.page_count:
                votes[index + 1 - int(line)] += 1
    return votes.most_common(1)[0][0] if votes else 0


def probe_cepa() -> int:
    """Vaststellen wát het amendementsdocument op cepa.be is, en waar wat staat.

    Niet: de tekst overnemen. Wel: uitgever, omvang, de paginaverschuiving en
    een voorbeeld van elke sectie die wij nodig hebben, zodat de parsers ertegen
    geschreven kunnen worden. Alleen feitelijke gegevens komen uiteindelijk in
    de repo; de regelgevingstekst zelf niet.
    """
    import fitz

    print("== cepa.be — IMDG_Code-amdt_42_24.pdf ==")
    try:
        path = download(CEPA, Path("/tmp/cepa.pdf"), timeout=600)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as error:
        print(f"  niet bereikbaar: {error}")
        return 1
    print(f"  {path.stat().st_size} bytes")

    with fitz.open(path) as document:
        print(f"  {document.page_count} pagina's")
        print(f"  metadata: {document.metadata}")

        print("\n--- eerste pagina ---")
        print(document[0].get_text()[:2000])

        toc = document.get_toc()
        print(f"\n--- ingebedde inhoudsopgave: {len(toc)} regels ---")
        for level, title, page in toc[:120]:
            print(f"{'  ' * (level - 1)}{title}  -> p{page}")

        offset = find_page_offset(document)
        print(f"\n--- paginaverschuiving: PDF-pagina = codepagina + {offset} ---")

        print("\n--- de secties die wij nodig hebben ---")
        for label, code_page in CODE_PAGES.items():
            index = code_page + offset - 1
            marker = "?" if not 0 <= index < document.page_count else ""
            print(f"  {label:<52} codepagina {code_page} -> PDF {index + 1}{marker}")

        print("\n--- waar komen de secties voor in de tekst? ---")
        located: dict[str, list[int]] = {}
        for index in range(document.page_count):
            text = document[index].get_text()
            for section in SECTIONS_OF_INTEREST:
                if re.search(rf"(?<![\d.]){re.escape(section)}(?![\d])", text):
                    located.setdefault(section, []).append(index + 1)
        for section in SECTIONS_OF_INTEREST:
            pages = located.get(section, [])
            summary = f"{len(pages)}x, eerst PDF p{pages[0]}" if pages else "niet gevonden"
            print(f"  {section:<12} {summary}")

        # Doorlopende codetekst of een wijzigingsoverzicht? Een amendement
        # schrijft in opdrachten; een geconsolideerde tekst niet.
        joined = " ".join(document[i].get_text() for i in range(min(40, document.page_count)))
        directives = sum(len(re.findall(rf"\b{verb}\b", joined, re.I))
                         for verb in ("replace", "insert", "delete", "amend"))
        print(f"\n  wijzigingsopdrachten in de eerste 40 pagina's: {directives}")
        print("  -> waarschijnlijk een amendementstekst" if directives > 60
              else "  -> waarschijnlijk doorlopende, geconsolideerde codetekst")

        # De stuwage- en scheidingscodes zijn de grootste winst en het makkelijkst
        # te parsen: genummerde lijsten. Volledig afdrukken zodat de parser
        # tegen de echte opmaak geschreven kan worden.
        for label in ("7.1.3 Stowage categories", "7.1.5 Stowage codes",
                      "7.1.6 Handling codes", "7.2.8 Segregation codes"):
            start = CODE_PAGES[label] + offset - 1
            print(f"\n===== {label} — PDF p{start + 1} t/m p{start + 4} =====")
            for index in range(start, min(start + 4, document.page_count)):
                print(f"--- PDF p{index + 1} ---")
                print(document[index].get_text())

        # De scheidingstabel is een raster: woorden met positie, anders is de
        # kolomindeling niet terug te vinden.
        start = CODE_PAGES["7.2.4 Segregation table"] + offset - 1
        print(f"\n===== 7.2.4 Segregation table — PDF p{start + 1}, woorden met positie =====")
        if 0 <= start < document.page_count:
            for word in document[start].get_text("words"):
                print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")

        # Appendix 2 is de Dangerous Goods List: de hoofdprijs, en het lastigst.
        start = CODE_PAGES["Appendix 2 (Dangerous Goods List)"] + offset - 1
        print(f"\n===== Appendix 2 — PDF p{start + 1} en p{start + 3}, woorden met positie =====")
        for index in (start, start + 2):
            if 0 <= index < document.page_count:
                print(f"--- PDF p{index + 1} ---")
                for word in document[index].get_text("words")[:250]:
                    print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=["cantell", "model-regs", "cepa", "all"])
    parser.add_argument("--sample-pages", default="60,61,120",
                        help="Pagina's van de DGL die als voorbeeld op de uitvoer komen")
    args = parser.parse_args(argv)

    pages = [int(p) for p in args.sample_pages.split(",") if p.strip().isdigit()]
    status = 0
    if args.source in {"cantell", "all"}:
        status |= probe_cantell()
    if args.source in {"model-regs", "all"}:
        status |= probe_model_regulations(pages)
    if args.source in {"cepa", "all"}:
        status |= probe_cepa()
    return status


if __name__ == "__main__":
    sys.exit(main())
