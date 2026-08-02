"""Stuwage-, behandelings- en scheidingscodes uit IMDG-code Amendment 42-24.

De app kent per stof de codes uit kolom 16a en 16b — SW1, H2, SG35 — maar tot nu
toe alleen met de brokstukken tekst die van de UN-kaarten te schrapen waren. Een
kale code zegt een gebruiker niets, en een half citaat is erger dan geen citaat.

Dit script leest de definities uit hun eigen hoofdstukken:

- 7.1.5  stuwagecodes SW1 t/m SW31
- 7.1.6  behandelingscodes H1 t/m H5
- 7.2.8  scheidingscodes SG1 t/m SG78

Bron: resolutie MSC.556(108), aangenomen op 23 mei 2024, in werking getreden op
1 januari 2026 — het instrument waarmee Amendment 42-24 is vastgesteld. Het
draait via GitHub Actions, omdat de ontwikkelomgeving geen uitgaand netwerk
heeft.

Wat er wordt weggeschreven is een feitelijke codetabel: code, omschrijving en
waar die vandaan komt. Dezelfde lijn als bij de rest van de gegevens in deze
repo. De gepubliceerde tekst van de code blijft leidend.

Gebruik::

    python scripts/extract_imdg_codes.py --out backend/seed/dg/imdg_codes.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

SOURCE_URL = "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf"
SOURCE_NAME = ("IMO-resolutie MSC.556(108), aangenomen 23 mei 2024 — Amendments to the "
               "International Maritime Dangerous Goods (IMDG) Code, Amendment 42-24, "
               "in werking sinds 1 januari 2026")
UA = {"User-Agent": "CargoPilot data extraction (github.com/jeffreymooiweer/CargoPilot)"}

# Elke reeks met de kop waarop de sectie begint en het patroon van haar codes.
SECTIONS = [
    {
        "key": "stowage_codes",
        "section": "7.1.5",
        "heading": re.compile(r"^7\.1\.5\b"),
        "intro": "stowage codes given in column 16a",
        "code": re.compile(r"^(SW\d{1,2})\s*$"),
        "stop": re.compile(r"^7\.1\.6\b"),
    },
    {
        "key": "handling_codes",
        "section": "7.1.6",
        "heading": re.compile(r"^7\.1\.6\b"),
        "intro": "handling codes given in column 16a",
        "code": re.compile(r"^(H\d{1,2})\s*$"),
        "stop": re.compile(r"^Chapter 7\.2\b"),
    },
    {
        "key": "segregation_codes",
        "section": "7.2.8",
        "heading": re.compile(r"^7\.2\.8\b"),
        "intro": "segregation codes given in column 16b",
        "code": re.compile(r"^(SG\d{1,2})\s*$"),
        "stop": re.compile(r"^Annex\s*$"),
    },
]

# Kop- en voetregels van de uitgave. Die staan midden tussen de codes en zouden
# anders als omschrijving worden meegenomen.
NOISE = re.compile(
    r"^(?:"
    r"MSC \d+/\d+/Add\.\d+"
    r"|Annex \d+, page \d+"
    r"|IMDG Code \(Amendment [\d-]+\)\s*\d{4} EDITION"
    r"|Part \d+ [–-] .*"
    r"|Chapter [\d.]+ [–-] .*"
    r"|(?:Stowage|Handling|Segregation)\s*$"
    r"|code\s*$"
    r"|Description\s*$"
    r"|\d{1,4}\s*$"
    r"|■\s*"
    r")$"
)


def download(url: str, target: Path, timeout: int = 600) -> Path:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def clean_lines(document, first: int, last: int) -> list[str]:
    """Leesbare regels uit een paginabereik, zonder kop- en voetteksten."""
    out: list[str] = []
    for index in range(first, min(last, document.page_count)):
        for raw in document[index].get_text().splitlines():
            line = raw.replace("\t", " ").replace("\xa0", " ").strip()
            if line and not NOISE.match(line):
                out.append(line)
    return out


def find_section(document, spec: dict[str, Any]) -> int:
    """Paginanummer waarop een sectie begint, gezocht op kop én inleidingszin.

    Alleen op de kop zoeken levert de inhoudsopgave en elke kruisverwijzing op;
    de inleidingszin ("The stowage codes given in column 16a …") staat maar op
    één plaats.
    """
    for index in range(document.page_count):
        text = document[index].get_text()
        if spec["intro"] in text and spec["heading"].search(text.replace("\t", " ")):
            return index
    raise LookupError(f"sectie {spec['section']} niet gevonden")


def parse_codes(lines: list[str], spec: dict[str, Any]) -> dict[str, str]:
    """Codes en hun omschrijving uit een reeks regels.

    De opmaak is een tabel van twee kolommen die als losse regels uit de PDF
    komt: eerst de code alleen op een regel, daarna de omschrijving over een of
    meer regels. Alles tot de volgende code hoort bij de vorige.
    """
    codes: dict[str, list[str]] = {}
    current: str | None = None
    started = False

    for line in lines:
        if not started:
            if spec["heading"].match(line):
                started = True
            continue
        if spec["stop"].match(line):
            break
        match = spec["code"].match(line)
        if match:
            current = match.group(1)
            codes.setdefault(current, [])
            continue
        if current is not None:
            codes[current].append(line)

    return {code: " ".join(parts).strip() for code, parts in codes.items() if parts}


def sort_key(code: str) -> tuple[str, int]:
    match = re.match(r"^([A-Z]+)(\d+)$", code)
    return (match.group(1), int(match.group(2))) if match else (code, 0)


def extract(path: Path) -> dict[str, Any]:
    import fitz

    result: dict[str, Any] = {
        "_comment": (
            "Stuwagecodes (16a), behandelingscodes (16a) en scheidingscodes (16b) met hun "
            "omschrijving, overgenomen uit de hoofdstukken 7.1.5, 7.1.6 en 7.2.8 van de "
            "IMDG-code. Feitelijke invulhulp; de gepubliceerde tekst van de code blijft "
            "leidend. Machinaal gelezen door scripts/extract_imdg_codes.py."
        ),
        "amendment": "42-24",
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
    }

    with fitz.open(path) as document:
        for spec in SECTIONS:
            start = find_section(document, spec)
            lines = clean_lines(document, start, start + 6)
            codes = parse_codes(lines, spec)
            if not codes:
                raise LookupError(f"geen codes gelezen in {spec['section']}")
            result[spec["key"]] = {
                "section": spec["section"],
                "codes": {code: codes[code] for code in sorted(codes, key=sort_key)},
            }
            print(f"{spec['section']}: {len(codes)} codes "
                  f"({min(codes, key=sort_key)}..{max(codes, key=sort_key)}), "
                  f"vanaf PDF-pagina {start + 1}")
    return result


def sanity_check(data: dict[str, Any]) -> list[str]:
    """Wat er mis kan gaan bij het lezen van een PDF-tabel, expliciet gemaakt.

    Een parser die stilletjes de helft mist is gevaarlijker dan een die faalt,
    dus dit meldt onvolledigheid in plaats van haar te laten passeren.
    """
    problems: list[str] = []
    expected = {"stowage_codes": ("SW", 31), "handling_codes": ("H", 5),
                "segregation_codes": ("SG", 78)}
    for key, (prefix, highest) in expected.items():
        codes = data[key]["codes"]
        numbers = {int(c[len(prefix):]) for c in codes}
        if highest not in numbers:
            problems.append(f"{key}: hoogste code {prefix}{highest} ontbreekt")
        # Gaten mogen bestaan — SG64, SG66 en SG73 zijn gereserveerd, SG75 is
        # met 41-22 vervallen — maar een gat van meer dan drie op rij wijst op
        # een leesfout in plaats van op de code.
        missing = sorted(set(range(1, highest + 1)) - numbers)
        run: list[int] = []
        for number in missing + [None]:
            if run and number == run[-1] + 1:
                run.append(number)
                continue
            if len(run) > 3:
                problems.append(f"{key}: {prefix}{run[0]}..{prefix}{run[-1]} ontbreken")
            run = [number] if number is not None else []
        for code, text in codes.items():
            if len(text) < 5:
                problems.append(f"{key}: {code} heeft een verdacht korte omschrijving")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("backend/seed/dg/imdg_codes.json"))
    parser.add_argument("--pdf", type=Path, help="Al gedownload bestand hergebruiken")
    args = parser.parse_args(argv)

    path = args.pdf or download(SOURCE_URL, Path("/tmp/imdg_42_24.pdf"))
    print(f"bron: {path} ({path.stat().st_size} bytes)")

    data = extract(path)
    problems = sanity_check(data)
    for problem in problems:
        print(f"LET OP: {problem}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"geschreven: {args.out}")

    print("\n--- wat er gelezen is ---")
    for key in ("stowage_codes", "handling_codes", "segregation_codes"):
        for code, text in data[key]["codes"].items():
            print(f"{code:<6} {text}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
