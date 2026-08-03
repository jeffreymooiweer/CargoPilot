"""De Dangerous Goods List van IMDG-code Amendment 42-24 uitlezen.

De lijst staat op ongeveer 170 liggende pagina's van 1180 punten breed, met
achttien kolommen in een vast raster. De inventarisatie
(scripts/survey_imdg_dgl.py) stelde vast dat zij alle 2.336 UN-nummers bevat
die we nu uit de kaarten van 41-22 kennen, plus de elf die 42-24 toevoegt.

Deze stap zet dat om in gegevens. Het gevaar bij zo'n tabel is niet dat de
parser omvalt maar dat hij stilzwijgend één kolom verschuift: dan staan er
2.300 stoffen met een verkeerde scheidingscode in de app en ziet niemand het.
Daarom controleert dit script zichzelf tegen wat we al langs twee andere wegen
weten — klasse en verpakkingsgroep uit ADR Tabel A, EmS uit de EmS Guide — en
weigert het weg te schrijven als er te veel afwijkt.

Gebruik::

    python scripts/extract_imdg_dgl.py --out backend/seed/dg/imdg_dgl.json
    python scripts/extract_imdg_dgl.py --dry-run --pages 600,601,627
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

SOURCE_URL = "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf"
SOURCE_NAME = ("IMO-resolutie MSC.556(108), aangenomen 23 mei 2024 — IMDG-code "
               "Amendment 42-24, hoofdstuk 3.2 Dangerous Goods List")
UA = {"User-Agent": "CargoPilot data extraction (github.com/jeffreymooiweer/CargoPilot)"}

SEED = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg"

# De kolommen dragen in de koptekst hun nummer uit de code: "(1)" boven het
# UN-nummer, "(16b)" boven de scheiding. Die nummerband staat op elke
# lijstpagina, precies boven de kolom die zij benoemt, en is daarmee de enige
# bron die de gemeten celranden een náám kan geven zonder te tellen.
#
# Tellen ging namelijk mis. Een tabel met gemeten x-posities veronderstelde
# negentien kolommen; de getekende randen leveren er eenentwintig, want de
# lijst staat als spread op één liggend vel en de goot tussen beide helften
# telt als cel mee, en kolom (12) was over het hoofd gezien. De uitlijning
# klopte daardoor nergens, de parser viel terug op het midden tussen twee
# koppen, en de vervoersnaam — die op x 68 begint, net links van die schatting
# — belandde met haar eerste woord van elke regel in de UN-kolom:
# "1354 TRINITROBENZENE, with by G".
COLUMN_NAMES: dict[str, str] = {
    "1": "un_number",
    "2": "proper_shipping_name",
    "3": "class",
    "4": "subsidiary_hazards",
    "5": "packing_group",
    "6": "special_provisions",
    "7a": "limited_quantity",
    "7b": "excepted_quantity",
    "8": "packing_instructions",
    "9": "packing_provisions",
    "10": "ibc_instructions",
    "11": "ibc_provisions",
    "12": "imo_tank_instructions",
    "13": "tank_instructions",
    "14": "tank_provisions",
    "15": "ems",
    "16a": "stowage_and_handling",
    "16b": "segregation",
    "17": "properties_and_observations",
    "18": "_un_number_repeat",
}

# Zonder deze kolommen is een pagina niet als lijstpagina gelezen en wordt zij
# liever overgeslagen dan half vastgelegd.
REQUIRED_COLUMNS = frozenset({
    "un_number", "proper_shipping_name", "class", "packing_group",
    "special_provisions", "ems", "stowage_and_handling", "segregation",
    "properties_and_observations",
})

# De nummerband ligt tussen de koppen en de gegevens. Eronder, op y 140.5,
# staan de verwijzingen naar de secties die elke kolom regelen; die dragen geen
# haakjes en komen dus niet als nummer binnen.
MARKER_BAND = (120.0, 150.0)
MARKER = re.compile(r"^\((\d{1,2}[ab]?)\)$")

# Twee of meer koppen maken een pagina tot lijstpagina. De scheidingsgroep-
# lijsten van 3.1.4.4 beginnen ook met UN-nummers en horen er niet bij.
HEADINGS = ["UN No.", "Proper shipping name", "Class or division", "Subsidiary",
            "Packing group", "Special provisions", "Limited and excepted",
            "Portable tanks", "EmS", "Stowage and handling", "Segregation",
            "Properties and observations"]

# Alles boven deze y is koptekst, alles eronder voettekst. De grens ligt onder
# twee banden die er op het oog bij horen maar geen gegevens zijn: de
# kolomnummers "(1) (2) (3) …" op y 131.7 en de verwijzingen naar de secties
# die elke kolom regelen ("3.1.2", "2.0.1.3", "7.2–7.7") op y 140.5.
BODY_TOP, BODY_BOTTOM = 150.0, 795.0

# Terugval wanneer een pagina geen horizontale randen levert: woorden binnen
# deze afstand in y horen dan tot dezelfde tekstregel. Als maat voor een
# tabelrij is dat te grof — het plakte UN 0291 en UN 0292 tot één vermelding —
# dus de rijbanden komen bij voorkeur van de getekende randen.
LINE_TOLERANCE = 3.0

# Een vermelding die 42-24 heeft gewijzigd draagt een driehoekje vóór het
# UN-nummer, en PyMuPDF levert dat als één woord: "△1361". Werd dat niet
# herkend, dan gold de rij als vervolgregel en schoof zij bij de stof erboven
# naar binnen — UN 1360 kreeg zo "4.3 4.2 4.2 4.2" als klasse en de EmS-codes
# van vier stoffen achter elkaar. Het teken is bovendien zelf een gegeven: het
# wijst precies de vermeldingen aan die het amendement heeft aangeraakt.
UN_CELL = re.compile(r"^([^\w\s]?)\s*(\d{4})$")

# Hetzelfde, maar op één woord: waar in de eerste kolom een rij begint.
UN_WORD = re.compile(r"^[^\w\s]?\d{4}$")

# Een cel die met een UN-nummer begint maar doorloopt, betekent dat de tekst
# over de kolomgrens heen is gelezen. Dat mag niet stilzwijgend passeren.
UN_OVERFLOW = re.compile(r"^[^\w\s]?\s*(\d{4})\s+\S")


def download(url: str, target: Path, timeout: int = 600) -> Path:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def find_rules(page, tolerance: float = 2.5) -> list[float]:
    """De x-posities van de verticale celranden van de tabel.

    De lijst trekt geen doorlopende kolomlijn over de pagina maar omrandt elk
    rijblok apart; de hoogste verticaal is een punt of tachtig hoog. Eisen dat
    een lijn de halve pagina beslaat levert er dus nul op — dat was de eerste
    poging. Wat de kolomgrenzen verraadt is dat dezelfde x steeds terugkomt:
    een echte grens draagt tientallen randjes onder elkaar, een toevallige
    streep één.
    """
    counts: dict[float, int] = {}
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.width <= 2.0 and rect.height >= 10.0:
            key = round((rect.x0 + rect.x1) / 2, 1)
            counts[key] = counts.get(key, 0) + 1
    # Een grens komt door de hele tabel terug; een enkele streep niet.
    return _recurring(counts, tolerance)


def column_markers(page) -> list[tuple[float, str]]:
    """De kolomnummers uit de koptekst, met het midden waarboven ze staan."""
    found: list[tuple[float, str]] = []
    for x0, y0, x1, _y1, word, *_ in page.get_text("words"):
        if not MARKER_BAND[0] <= y0 < MARKER_BAND[1]:
            continue
        match = MARKER.match(word.strip())
        if match:
            found.append(((x0 + x1) / 2, match.group(1)))
    return sorted(found)


def boundaries(rules: list[float], markers: list[tuple[float, str]]
               ) -> list[tuple[str, float, float]]:
    """(naam, linkergrens, rechtergrens) per cel van het getekende raster.

    De randen komen uit de tekening en zijn dus exact; de namen komen uit de
    nummerband erboven. Valt er geen nummer in een cel, dan is dat de goot
    tussen beide helften van de spread en blijft de cel naamloos. Vallen er
    twéé in, dan sluiten randen en nummerband niet op elkaar aan en is de hele
    indeling onbruikbaar — dan liever niets dan een raster dat er alleen
    precies uitziet.
    """
    if len(rules) < 2 or not markers:
        return []

    cells: list[tuple[str, float, float]] = []
    for left, right in zip(rules, rules[1:]):
        inside = [label for x, label in markers if left <= x < right]
        if len(inside) == 1:
            name = COLUMN_NAMES.get(inside[0], f"_column_{inside[0]}")
        else:
            name = f"_unnamed_{left:.0f}"
        cells.append((name, left, right))

    names = [name for name, _, _ in cells]
    if len(set(names)) != len(names):
        return []
    if not REQUIRED_COLUMNS.issubset(names):
        return []
    return cells


def find_row_rules(page, tolerance: float = 2.5, coverage: float = 0.4) -> list[float]:
    """De y-posities waar de ene rij eindigt en de volgende begint.

    De verticale celranden dragen dit al: elk segment is een punt of tachtig
    hoog en loopt precies over één rijband, en er staan er achttien naast
    elkaar — één per kolom. Hun boven- en onderkant zijn dus de rijgrenzen, en
    een grens die achttien keer terugkomt is er een. Die y-waarden gooide de
    eerste versie weg en ging op zoek naar horizontale lijnen, waarvan er te
    weinig blijken te zijn; toen werd de hele pagina één band met twaalf
    stoffen erin.

    Levert dat niets op, dan alsnog de horizontale randen, gemeten op de
    breedte die alle stukjes op dezelfde hoogte samen bestrijken.
    """
    ends: dict[float, int] = {}
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.width <= 2.0 and rect.height >= 10.0:
            for y in (round(rect.y0, 1), round(rect.y1, 1)):
                ends[y] = ends.get(y, 0) + 1
    edges = _recurring(ends, tolerance)
    if len(edges) >= 2:
        return edges

    spans: dict[float, float] = {}
    widest = 0.0
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.height > 2.0 or rect.width <= 0:
            continue
        key = round((rect.y0 + rect.y1) / 2, 1)
        spans[key] = spans.get(key, 0.0) + rect.width
        widest = max(widest, rect.x1)
    if not spans:
        return []

    merged: list[tuple[float, float]] = []
    for y in sorted(spans):
        if merged and y - merged[-1][0] <= tolerance:
            previous, width = merged[-1]
            merged[-1] = (previous, width + spans[y])
        else:
            merged.append((y, spans[y]))
    needed = max(widest, 1.0) * coverage
    return [y for y, width in merged if width >= needed]


def un_number_rows(page, bounds: list[tuple[str, float, float]]) -> list[float]:
    """De hoogtes waarop in de eerste kolom een UN-nummer staat."""
    found = []
    for x0, y0, x1, _y1, word, *_ in page.get_text("words"):
        if not BODY_TOP <= y0 <= BODY_BOTTOM:
            continue
        if column_of((x0 + x1) / 2, bounds) == "un_number" and UN_WORD.match(word.strip()):
            found.append(y0)
    return sorted(found)


def row_rules_for(page, bounds: list[tuple[str, float, float]],
                  clearance: float = 3.0, tolerance: float = 4.0) -> list[float]:
    """De rijgrenzen, aangevuld op de plaatsen waar de tabel er geen tekent.

    De getekende randen omranden een blók rijen zodra de vermeldingen kort
    zijn. Op p627 belandden UN 1360, UN 1361 (twee verpakkingsgroepen) en
    UN 1362 daardoor in één band en dus in één vermelding, met '4.3 4.2 4.2
    4.2' als klasse. Elke rij begint met een UN-nummer in de eerste kolom, dus
    net boven zo'n nummer hoort een grens — of de tabel daar nu een lijn trekt
    of niet.
    """
    candidates = list(find_row_rules(page))
    candidates += [y - clearance for y in un_number_rows(page, bounds)]
    merged: list[float] = []
    for y in sorted(candidates):
        if not merged or y - merged[-1] > tolerance:
            merged.append(y)
    return merged


def _recurring(counts: dict[float, int], tolerance: float) -> list[float]:
    """Posities die vaak genoeg terugkomen om een echte rand te zijn."""
    if not counts:
        return []
    merged: list[tuple[float, int]] = []
    for value in sorted(counts):
        if merged and value - merged[-1][0] <= tolerance:
            previous, count = merged[-1]
            merged[-1] = (previous, count + counts[value])
        else:
            merged.append((value, counts[value]))
    threshold = max(2, max(count for _, count in merged) // 4)
    return [value for value, count in merged if count >= threshold]


def column_of(x: float, bounds: list[tuple[str, float, float]]) -> str:
    """De kolom waarin x valt, of "" voor wat buiten de tabel staat.

    Buiten de randen ligt de marge: paginanummers, het driehoekje dat een
    gewijzigde vermelding aanwijst. Dat bij de dichtstbijzijnde kolom
    optellen zou het als gegeven laten doorgaan.
    """
    for name, left, right in bounds:
        if left <= x < right:
            return name
    return ""


def band_of(y: float, rules: list[float]) -> int:
    """In welke rijband een woord valt, geteld tussen de horizontale randen."""
    band = 0
    for rule in rules:
        if y < rule:
            return band
        band += 1
    return band


def page_lines(page, bounds: list[tuple[str, float, float]],
               row_rules: list[float] | None = None) -> list[dict[str, str]]:
    """De rijen van een lijstpagina, per kolom uitgesplitst.

    Met de horizontale randen erbij is een rij precies wat tussen twee randen
    staat, hoeveel tekstregels dat ook zijn: een lange vervoersnaam die
    doorloopt hoort bij dezelfde vermelding, en de volgende vermelding begint
    pas na de rand. Zonder die randen valt de indeling terug op afstand in y,
    wat genoeg is om door te lezen maar twee korte vermeldingen aan elkaar kan
    plakken.

    Een woord hoort bij de kolom waarin zijn mídden valt, niet zijn linkerrand.
    Een gewijzigde vermelding draagt een driehoekje vóór het UN-nummer, en dat
    zet het woord "△1361" met zijn linkerrand buiten de tabel; op de linkerrand
    afgaan liet die rijen zonder UN-nummer achter, waarna zij als vervolgregel
    bij UN 1360 introkken — klasse '4.3 4.2 4.2 4.2'. Celtekst steekt verder
    nooit over een kolomgrens heen, dus het midden wijst dezelfde kolom aan.

    Binnen een rij worden de woorden op leesvolgorde gezet: eerst van boven
    naar beneden, dan van links naar rechts, zodat een naam over twee regels in
    de goede volgorde aan elkaar komt.
    """
    rows: dict[Any, dict[str, list[tuple[float, float, str]]]] = defaultdict(
        lambda: defaultdict(list))
    for x0, y0, x1, _y1, word, *_ in page.get_text("words"):
        if not BODY_TOP <= y0 <= BODY_BOTTOM:
            continue
        column = column_of((x0 + x1) / 2, bounds)
        if not column:
            continue
        if row_rules:
            key: Any = band_of(y0, row_rules)
        else:
            key = next((k for k in rows if abs(k - y0) <= LINE_TOLERANCE), round(y0, 1))
        rows[key][column].append((y0, x0, word))

    lines = []
    for key in sorted(rows):
        cells = {}
        for name, words in rows[key].items():
            ordered = sorted(words, key=lambda w: (round(w[0], 1), w[1]))
            cells[name] = " ".join(word for _y, _x, word in ordered)
        lines.append(cells)
    return lines


def merge_rows(lines: list[dict[str, str]]) -> list[dict[str, str]]:
    """Tekstregels samenvoegen tot vermeldingen.

    Een nieuwe vermelding begint waar de eerste kolom een UN-nummer draagt.
    Alles daarna zonder eigen UN-nummer is een vervolgregel en hoort bij de
    vorige — zo blijft "GASOLINE" niet los staan van de regel eronder.
    """
    entries: list[dict[str, str]] = []
    for cells in lines:
        first = cells.get("un_number", "").strip()
        if UN_OVERFLOW.match(first):
            # Meelezen als vermelding zou een half afgekapte naam opleveren;
            # overslaan zou hem verbergen. De cel blijft staan zoals hij is,
            # zodat de telling in extract() hem als overloop kan melden.
            entries.append({k: v for k, v in cells.items() if not k.startswith("_")})
            continue
        clean = UN_CELL.match(first)
        if clean:
            entry = {k: v for k, v in cells.items() if not k.startswith("_")}
            entry["un_number"] = clean.group(2)
            if clean.group(1):
                entry["amended"] = "42-24"
            entries.append(entry)
            continue
        if not entries:
            continue
        for name, value in cells.items():
            if name.startswith("_") or not value.strip():
                continue
            entries[-1][name] = f"{entries[-1].get(name, '')} {value}".strip()
    return entries


def normalise(entry: dict[str, str]) -> dict[str, Any]:
    return {k: re.sub(r"\s+", " ", v).strip() for k, v in entry.items() if v.strip()}


def extract(path: Path, only_pages: list[int] | None = None) -> tuple[list[dict], dict]:
    import fitz

    entries: list[dict[str, Any]] = []
    pages_read: list[int] = []
    skipped: list[int] = []
    rule_shapes: dict[tuple[float, ...], int] = {}
    # Een pagina zonder leesbare nummerband mag meeliften op een pagina met
    # exact hetzelfde randenpatroon; verder gaat zij ongelezen de telling in.
    layouts: dict[tuple[float, ...], list[tuple[str, float, float]]] = {}

    with fitz.open(path) as document:
        for index in range(document.page_count):
            number = index + 1
            if only_pages and number not in only_pages:
                continue
            page = document[index]
            if not only_pages:
                text = page.get_text()
                if sum(1 for h in HEADINGS if h in text) < 2:
                    continue

            rules = find_rules(page)
            shape = tuple(rules)
            bounds = boundaries(rules, column_markers(page))
            if bounds:
                layouts[shape] = bounds
            else:
                bounds = layouts.get(shape, [])
            if not bounds:
                skipped.append(number)
                continue

            pages_read.append(number)
            rule_shapes[shape] = rule_shapes.get(shape, 0) + 1
            row_rules = row_rules_for(page, bounds)
            for entry in merge_rows(page_lines(page, bounds, row_rules)):
                clean = normalise(entry)
                cell = clean.get("un_number", "")
                if UN_CELL.match(cell) or UN_OVERFLOW.match(cell):
                    clean["_page"] = number
                    entries.append(clean)

    # Eén rasterindeling voor de hele lijst is het teken dat de detectie klopt;
    # veel verschillende betekent dat er pagina's anders zijn opgemaakt.
    shapes = sorted(rule_shapes.items(), key=lambda kv: -kv[1])
    overflow = [e["un_number"] for e in entries if UN_OVERFLOW.match(e["un_number"])]
    return entries, {
        "pages": len(pages_read), "entries": len(entries),
        "overflowing_cells": len(overflow),
        "overflow_examples": overflow[:10],
        "first_page": pages_read[0] if pages_read else None,
        "last_page": pages_read[-1] if pages_read else None,
        "distinct_rule_layouts": len(shapes),
        "most_common_rules": list(shapes[0][0]) if shapes else [],
        "most_common_rules_pages": shapes[0][1] if shapes else 0,
        "pages_without_grid": len(skipped),
        "pages_without_grid_examples": skipped[:10],
    }


# --- Zelfcontrole -------------------------------------------------------------

def load(name: str) -> Any:
    try:
        return json.loads((SEED / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - seed ontbreekt
        return None


def cross_check(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """De uitkomst leggen naast wat we langs andere wegen al weten.

    Klasse komt uit ADR Tabel A, EmS uit de EmS Guide. Beide zijn onafhankelijk
    van deze PDF. Klopt de kolomindeling, dan moeten ze grotendeels
    samenvallen; een verschoven kolom laat hier meteen honderden verschillen
    zien in plaats van stilletjes de app in te lekken.
    """
    cards = (load("card_data.json") or {}).get("entries", {})
    ems_seed = (load("ems.json") or {}).get("entries", {})

    checks = {"class": {"same": 0, "differs": 0, "examples": []},
              "ems": {"same": 0, "differs": 0, "examples": []}}

    by_un: dict[str, dict[str, Any]] = {}
    for entry in entries:
        by_un.setdefault(entry["un_number"], entry)

    for un, entry in by_un.items():
        card = cards.get(un)
        if card and card.get("class"):
            found = entry.get("class", "").strip()
            key = "same" if found == str(card["class"]).strip() else "differs"
            checks["class"][key] += 1
            if key == "differs" and len(checks["class"]["examples"]) < 15:
                checks["class"]["examples"].append(
                    f"UN {un}: lijst {found!r} vs kaart {card['class']!r}")

        seeded = ems_seed.get(un)
        if isinstance(seeded, dict) and seeded.get("fire"):
            expected = f"{seeded['fire']} {seeded['spillage']}".replace(" ", "")
            found = entry.get("ems", "").replace(" ", "").replace(",", "")
            key = "same" if found == expected.replace(",", "") else "differs"
            checks["ems"][key] += 1
            if key == "differs" and len(checks["ems"]["examples"]) < 15:
                checks["ems"]["examples"].append(
                    f"UN {un}: lijst {entry.get('ems')!r} vs EmS Guide {expected!r}")

    for name, result in checks.items():
        total = result["same"] + result["differs"]
        result["agreement"] = round(result["same"] / total, 4) if total else None
    return checks


def diagnose(path: Path, pages: list[int]) -> None:
    """Tonen wat de parser op een pagina werkelijk aantreft.

    Twee keer achter elkaar de verkeerde aanname doen kost meer tijd dan één
    keer meten. Dit drukt de paginamaat af, wat er aan tekeningen op staat, de
    eerste woorden met hun positie en de cellen die daaruit volgen.
    """
    import fitz

    with fitz.open(path) as document:
        for number in pages:
            if not 0 < number <= document.page_count:
                continue
            page = document[number - 1]
            print(f"\n===== p{number} =====")
            print(f"  rect {page.rect}, rotatie {page.rotation}")

            drawings = page.get_drawings()
            vertical = [d["rect"] for d in drawings if d["rect"].width <= 2.0]
            print(f"  tekeningen: {len(drawings)}, waarvan smal-en-verticaal: {len(vertical)}")
            if vertical:
                tallest = sorted(vertical, key=lambda r: -r.height)[:8]
                print("    hoogste: " + ", ".join(
                    f"x{r.x0:.1f} h{r.height:.1f}" for r in tallest))
            elif drawings:
                sample = [d["rect"] for d in drawings[:8]]
                print("    voorbeeld: " + ", ".join(
                    f"({r.x0:.0f},{r.y0:.0f})-({r.x1:.0f},{r.y1:.0f})" for r in sample))

            words = page.get_text("words")
            ys = [w[1] for w in words]
            print(f"  woorden: {len(words)}, y van {min(ys, default=0):.1f} "
                  f"tot {max(ys, default=0):.1f}")
            print(f"  binnen BODY_TOP..BODY_BOTTOM ({BODY_TOP}..{BODY_BOTTOM}): "
                  f"{sum(1 for y in ys if BODY_TOP <= y <= BODY_BOTTOM)}")

            print("  eerste 25 woorden onder de koptekst:")
            for word in sorted((w for w in words if w[1] > BODY_TOP),
                               key=lambda w: (w[1], w[0]))[:25]:
                print(f"    x{word[0]:8.1f} y{word[1]:8.1f}  {word[4]!r}")

            horizontals: dict[float, float] = {}
            for drawing in page.get_drawings():
                rect = drawing["rect"]
                if rect.height <= 2.0 and rect.width > 0:
                    key = round((rect.y0 + rect.y1) / 2, 1)
                    horizontals[key] = horizontals.get(key, 0.0) + rect.width
            print(f"  horizontale stukjes op {len(horizontals)} hoogtes; "
                  f"breedste dekking {max(horizontals.values(), default=0):.0f}")
            heights = [d["rect"].height for d in page.get_drawings()
                       if d["rect"].width <= 2.0 and d["rect"].height >= 10.0]
            print(f"  verticale segmenten: {len(heights)}, hoogte "
                  f"{min(heights, default=0):.1f}..{max(heights, default=0):.1f}")
            print(f"  getekende horizontale randen: {len(find_row_rules(page))}")

            rules = find_rules(page)
            markers = column_markers(page)
            print(f"  kolomnummers in de koptekst: {len(markers)}")
            print("    " + ", ".join(f"({label})@{x:.0f}" for x, label in markers))
            bounds = boundaries(rules, markers)
            if not bounds:
                print("  GEEN bruikbare kolomindeling; deze pagina wordt overgeslagen.")
                continue
            print("  kolommen:")
            for name, left, right in bounds:
                print(f"    {left:7.1f} - {right:7.1f}  {name}")

            starts = un_number_rows(page, bounds)
            row_rules = row_rules_for(page, bounds)
            print(f"  UN-nummers in de eerste kolom: {len(starts)}; "
                  f"rijgrenzen na aanvulling: {len(row_rules)}")

            lines = page_lines(page, bounds, row_rules)
            print(f"  rijen na kolom- en rijindeling: {len(lines)}")
            odd = [ascii(cells.get("un_number", "")) for cells in lines
                   if not UN_CELL.match(cells.get("un_number", "").strip())]
            print(f"  eerste cellen die geen UN-nummer zijn: {odd}")
            for cells in lines[:5]:
                print(f"    {cells}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=SEED / "imdg_dgl.json")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--pages", help="Alleen deze pagina's, voor een proef")
    parser.add_argument("--dry-run", action="store_true",
                        help="Wel lezen en controleren, niet wegschrijven")
    parser.add_argument("--debug", action="store_true",
                        help="Per proefpagina tonen wat de parser werkelijk ziet")
    parser.add_argument("--min-agreement", type=float, default=0.95,
                        help="Onder deze overeenstemming wordt niets vastgelegd")
    args = parser.parse_args(argv)

    path = args.pdf or download(SOURCE_URL, Path("/tmp/imdg_42_24.pdf"))
    only = [int(p) for p in (args.pages or "").split(",") if p.strip().isdigit()] or None

    if args.debug and only:
        diagnose(path, only)

    entries, summary = extract(path, only)
    print(f"gelezen: {summary}")
    if not entries:
        print("Geen vermeldingen gelezen.")
        return 1

    print("\n--- eerste drie vermeldingen ---")
    for entry in entries[:3]:
        print(json.dumps(entry, ensure_ascii=False, indent=1))

    checks = cross_check(entries)
    print("\n--- zelfcontrole tegen onafhankelijke bronnen ---")
    for name, result in checks.items():
        print(f"  {name}: {result['same']} gelijk, {result['differs']} anders, "
              f"overeenstemming {result['agreement']}")
        for example in result["examples"]:
            print(f"      {example}")

    weakest = [r["agreement"] for r in checks.values() if r["agreement"] is not None]
    if not weakest:
        print("\nNiets te vergelijken; er wordt niets vastgelegd.")
        return 1
    if min(weakest) < args.min_agreement:
        print(f"\nOvereenstemming {min(weakest)} ligt onder {args.min_agreement}: "
              "de kolomindeling klopt niet. Er wordt niets vastgelegd.")
        return 1

    payload = {
        "_comment": ("Dangerous Goods List van IMDG-code Amendment 42-24, machinaal "
                     "gelezen door scripts/extract_imdg_dgl.py. Feitelijke invulhulp; "
                     "de gepubliceerde tekst van de code blijft leidend."),
        "amendment": "42-24",
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "summary": summary,
        "cross_check": checks,
        "entries": [{k: v for k, v in e.items() if k != "_page"} for e in entries],
    }
    document = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    print(f"\n{len(entries)} vermeldingen, {len(document.encode('utf-8'))} bytes")

    if args.dry_run or only:
        print("Proefrun; er wordt niets vastgelegd.")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(document, encoding="utf-8")
    print(f"geschreven: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
