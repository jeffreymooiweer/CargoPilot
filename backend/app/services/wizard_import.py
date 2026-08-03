"""Wizard-import: spreadsheet naar plaktekst.

De wizard leest `omschrijving | aantal | eenheid`. Een spreadsheet die van
iemand anders komt heeft die kolommen zelden in die volgorde en met die namen,
en tot nu toe raadde de import stilzwijgend: herkent hij de koptekst niet, dan
neemt hij kolom 0, 1 en 2. Bij `Artikelnr | Omschrijving | Aantal | Eenheid`
levert dat het artikelnummer als omschrijving en de omschrijving als aantal.
Wat de gebruiker daarvan ziet is `status=error` en 0 kg, zonder aanwijzing dat
het aan de kolomindeling ligt.

Deze module raadt nog steeds — dat moet ook, anders wordt elke import handwerk
— maar zij zegt er nu bij wat zij heeft gedaan en waarop. Met die gegevens kan
de interface de indeling laten bijstellen in plaats van de gebruiker met een
onverklaarbare nul achter te laten.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.parser.paste_parser import detect_columns
from app.services.spreadsheet_io import rows_to_pipe_text

WIZARD_HEADERS = ["description", "quantity", "unit"]
WIZARD_EXAMPLE = ["staal hoekprofiel 80x80x8x6000", "8", "stuks"]

# Hoeveel voorbeeldwaarden per kolom meegaan naar de interface: genoeg om te
# zien wát er in een kolom staat, weinig genoeg om geen halve zending door te
# sturen naar een scherm dat er verder niets mee doet.
SAMPLE_ROWS = 3


@dataclass
class Column:
    """Eén kolom uit het bestand, zoals de gebruiker hem herkent."""

    index: int
    header: str
    samples: list[str] = field(default_factory=list)


@dataclass
class Analysis:
    """Wat de import van dit bestand heeft gemaakt, en hoe zeker dat is.

    `source` draagt het verschil dat ertoe doet: "header" betekent dat de
    koptekst is herkend, "position" dat er op volgorde is geraden. Alleen in
    het tweede geval is er reden om de gebruiker iets te vragen.
    """

    columns: list[Column]
    mapping: dict[str, int | None]
    source: str
    has_header: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "columns": [asdict(column) for column in self.columns],
            "mapping": self.mapping,
            "source": self.source,
            "has_header": self.has_header,
        }


def _columns(rows: list[list[str]], has_header: bool) -> list[Column]:
    width = max((len(row) for row in rows), default=0)
    body = rows[1:] if has_header else rows
    columns = []
    for index in range(width):
        header = rows[0][index] if has_header and index < len(rows[0]) else ""
        samples = [
            str(row[index]).strip()
            for row in body[:SAMPLE_ROWS]
            if index < len(row) and str(row[index]).strip()
        ]
        columns.append(Column(index=index, header=str(header).strip(), samples=samples))
    return columns


def analyse(rows: list[list[str]]) -> Analysis:
    """Welke kolom waarvoor doorgaat, en of dat is herkend of geraden."""
    if not rows:
        return Analysis(columns=[], mapping={key: None for key in WIZARD_HEADERS},
                        source="none", has_header=False)

    header_map = detect_columns([str(cell).lower().strip() for cell in rows[0]])
    has_header = header_map["description"] is not None or header_map["quantity"] is not None
    if has_header:
        return Analysis(columns=_columns(rows, True), mapping=header_map,
                        source="header", has_header=True)

    # Niets herkend: op volgorde raden, precies zoals hiervoor — maar nu met de
    # mededeling erbij dat het een gok is.
    width = max((len(row) for row in rows), default=0)
    mapping: dict[str, int | None] = {
        "description": 0 if width >= 1 else None,
        "quantity": 1 if width >= 2 else None,
        "unit": 2 if width >= 3 else None,
    }
    return Analysis(columns=_columns(rows, False), mapping=mapping,
                    source="position", has_header=False)


def apply_mapping(rows: list[list[str]], mapping: dict[str, int | None],
                  has_header: bool) -> str:
    """De rijen omzetten met de indeling die de gebruiker heeft gekozen.

    Er blijft niets van het bestand achter: de rijen komen met het verzoek mee
    en gaan als tekst terug. Een zending die halverwege op de server blijft
    liggen zou in strijd zijn met wat deze applicatie over opslag belooft.
    """
    body = rows[1:] if has_header else rows
    lines = []
    for row in body:
        def cell(key: str) -> str:
            index = mapping.get(key)
            if index is None or index < 0 or index >= len(row):
                return ""
            return str(row[index]).strip()

        description = cell("description")
        if not description:
            # Een regel zonder omschrijving valt niet te herkennen en levert
            # alleen een foutregel op in de wizard.
            continue
        lines.append(" | ".join([description, cell("quantity"), cell("unit")]).rstrip(" |"))
    return "\n".join(lines)


def spreadsheet_to_wizard_text(rows: list[list[str]]) -> tuple[str, bool]:
    if not rows:
        return "", False
    header_map = detect_columns([str(cell).lower().strip() for cell in rows[0]])
    has_header = header_map["description"] is not None or header_map["quantity"] is not None
    return rows_to_pipe_text(rows, skip_header=has_header), has_header
