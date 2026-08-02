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

# De kolommen zoals de koptekst ze neerzet, met hun begin-x, gemeten op p600 en
# p601. Deze posities dienen om de gedetecteerde kolomgrenzen een naam te geven
# — als grens zijn ze te grof. Celtekst begint zelden op de kopositie, en het
# midden tussen twee koppen ligt soms mídden in een cel: x 806.6 draagt 409
# woorden en viel bij die aanpak net aan de verkeerde kant van de streep.
#
# De tabel heeft getekende scheidingslijnen. Die zijn exact, en find_rules()
# leest ze uit de tekeningen van de pagina; de posities hieronder zijn dan nog
# slechts het etiket.
COLUMNS: list[tuple[str, float]] = [
    ("un_number", 49.0),
    ("proper_shipping_name", 95.0),
    ("class", 192.0),
    ("subsidiary_hazards", 221.0),
    ("packing_group", 260.0),
    ("special_provisions", 297.0),
    ("limited_quantity", 333.0),
    ("excepted_quantity", 368.0),
    ("packing_instructions", 402.0),
    ("packing_provisions", 443.0),
    ("ibc_instructions", 478.0),
    ("ibc_provisions", 519.0),
    ("tank_instructions", 644.0),
    ("tank_provisions", 673.0),
    ("ems", 736.0),
    ("stowage_and_handling", 773.0),
    ("segregation", 838.0),
    ("properties_and_observations", 963.0),
    ("_un_number_repeat", 1128.0),
]

# Twee of meer koppen maken een pagina tot lijstpagina. De scheidingsgroep-
# lijsten van 3.1.4.4 beginnen ook met UN-nummers en horen er niet bij.
HEADINGS = ["UN No.", "Proper shipping name", "Class or division", "Subsidiary",
            "Packing group", "Special provisions", "Limited and excepted",
            "Portable tanks", "EmS", "Stowage and handling", "Segregation",
            "Properties and observations"]

# Alles boven deze y is koptekst, alles eronder voettekst.
BODY_TOP, BODY_BOTTOM = 128.0, 795.0

# Regels op dezelfde tekstregel liggen binnen deze afstand in y.
LINE_TOLERANCE = 3.0

UN_CELL = re.compile(r"^\d{4}$")


def download(url: str, target: Path, timeout: int = 600) -> Path:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def find_rules(page, tolerance: float = 1.5) -> list[float]:
    """De x-posities van de verticale scheidingslijnen van de tabel.

    Een getekende lijn is een rechthoek die veel hoger is dan breed. Lijnen die
    minder dan een halve pagina beslaan horen bij een samengevoegde cel en
    zeggen niets over de kolomindeling.
    """
    found: list[float] = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.width <= 2.0 and rect.height >= 200.0:
            found.append(round((rect.x0 + rect.x1) / 2, 1))
    merged: list[float] = []
    for x in sorted(found):
        if not merged or x - merged[-1] > tolerance:
            merged.append(x)
    return merged


def boundaries(rules: list[float] | None = None) -> list[tuple[str, float, float]]:
    """(naam, linkergrens, rechtergrens) per kolom.

    Met de getekende lijnen erbij worden dat de echte celgrenzen; zonder die
    lijnen valt de parser terug op het midden tussen twee koppen, wat genoeg is
    om de meetkunde te kunnen testen maar niet om gegevens op te baseren.
    """
    if rules and len(rules) >= len(COLUMNS):
        edges = rules[:len(COLUMNS) + 1]
        out = []
        for index, (name, _start) in enumerate(COLUMNS):
            left = 0.0 if index == 0 else edges[index]
            right = edges[index + 1] if index + 1 < len(edges) else 10_000.0
            out.append((name, left, right))
        return out

    out = []
    for index, (name, start) in enumerate(COLUMNS):
        left = 0.0 if index == 0 else (COLUMNS[index - 1][1] + start) / 2
        right = (start + COLUMNS[index + 1][1]) / 2 if index + 1 < len(COLUMNS) else 10_000.0
        out.append((name, left, right))
    return out


def column_of(x: float, bounds: list[tuple[str, float, float]]) -> str:
    for name, left, right in bounds:
        if left <= x < right:
            return name
    return bounds[-1][0]


def page_lines(page, bounds: list[tuple[str, float, float]]) -> list[dict[str, str]]:
    """De tekstregels van een lijstpagina, per kolom uitgesplitst.

    Een rij van de lijst kan meerdere tekstregels beslaan: een lange
    vervoersnaam loopt door terwijl de andere kolommen leeg blijven. Hier wordt
    alleen per tekstregel gegroepeerd; het samenvoegen tot rijen gebeurt daarna.
    """
    rows: dict[float, dict[str, list[tuple[float, str]]]] = defaultdict(
        lambda: defaultdict(list))
    for x0, y0, _x1, _y1, word, *_ in page.get_text("words"):
        if not BODY_TOP <= y0 <= BODY_BOTTOM:
            continue
        key = next((k for k in rows if abs(k - y0) <= LINE_TOLERANCE), round(y0, 1))
        rows[key][column_of(x0, bounds)].append((x0, word))

    lines = []
    for key in sorted(rows):
        cells = {}
        for name, words in rows[key].items():
            cells[name] = " ".join(w for _, w in sorted(words))
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
        if UN_CELL.match(first):
            entries.append({k: v for k, v in cells.items() if not k.startswith("_")})
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
    rule_shapes: dict[tuple[float, ...], int] = {}

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
            pages_read.append(number)
            rules = find_rules(page)
            rule_shapes[tuple(rules)] = rule_shapes.get(tuple(rules), 0) + 1
            bounds = boundaries(rules)
            for entry in merge_rows(page_lines(page, bounds)):
                clean = normalise(entry)
                if UN_CELL.match(clean.get("un_number", "")):
                    clean["_page"] = number
                    entries.append(clean)

    # Eén rasterindeling voor de hele lijst is het teken dat de detectie klopt;
    # veel verschillende betekent dat er pagina's anders zijn opgemaakt.
    shapes = sorted(rule_shapes.items(), key=lambda kv: -kv[1])
    return entries, {
        "pages": len(pages_read), "entries": len(entries),
        "first_page": pages_read[0] if pages_read else None,
        "last_page": pages_read[-1] if pages_read else None,
        "distinct_rule_layouts": len(shapes),
        "most_common_rules": list(shapes[0][0]) if shapes else [],
        "most_common_rules_pages": shapes[0][1] if shapes else 0,
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

            lines = page_lines(page, boundaries(find_rules(page)))
            print(f"  tekstregels na kolomindeling: {len(lines)}")
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

    if args.dry_run or only:
        print("\nProefrun; er wordt niets vastgelegd.")
        return 0

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
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"\ngeschreven: {args.out} ({args.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
