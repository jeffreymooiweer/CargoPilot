"""The ADR card, from the tables this repository has already read and sealed.

Everything printed comes from ``backend/seed/dg/adr_table_a.json`` (ADR 2025
table A, machine-read and cross-checked), ``adr_2025_additions.json`` (rows
the 2025 edition added, transcribed twice from the official Dutch edition),
the per-language name registers, and — for the 1.1.3.6 figures — the same
``dg_compliance.json`` the compliance engine itself computes with, whose
values were read from ADR 1.1.3.6.3 including note (a). Nothing here decides
regulatory content; empty columns stay visibly empty or carry the meaning an
empty cell has in the ADR's own system (no tank code assigned means tank
carriage is not allowed, 4.3.2.1.1; no bulk code in column (17) means bulk is
not permitted, 7.3.1.1).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from .base import REPO, SEED, CardPage, SourceUnavailable, dash


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads((SEED / "adr_table_a.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _additions() -> dict:
    return json.loads((SEED / "adr_2025_additions.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def _names(language: str) -> dict:
    data = json.loads((SEED / f"adr_names_{language}.json").read_text(encoding="utf-8"))
    return data.get("names") or data.get("entries") or {}


@lru_cache(maxsize=1)
def _provision_texts() -> dict:
    """The verbatim V/CV/S texts of 7.2.4, 7.5.11 and 8.5, where extracted.

    Absent until the "Extract UN card assets" workflow has committed the
    seed; the card then falls back to code-plus-reference rows rather than
    inventing a summary.
    """
    path = SEED / "adr_provision_texts.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("sections", {})


def _reflow(raw: str) -> str:
    """Turn the column's printed lines back into flowing paragraphs.

    The extraction keeps one line per printed line of a narrow table column;
    joined naively that reads fine, except that list markers ("1)", "a)")
    were printed on their own line and deserve to start a new paragraph.
    """
    paragraphs: list[str] = []
    current: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"(\d+\)|[a-z]\)|[A-Z]\)|[–-])", line):
            if current:
                paragraphs.append(" ".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return "\n".join(paragraphs)


def _family(code: str) -> str | None:
    if code.startswith("CV"):
        return "CV"
    if code.startswith("V"):
        return "V"
    if code.startswith("S"):
        return "S"
    return None


def _codes_with_texts(value: str, reference: str) -> str:
    """One paragraph per code: its verbatim provision text where the seed
    has it, the article reference where it does not."""
    sections = _provision_texts()
    parts: list[str] = []
    for code in [c.strip() for c in (value or "").split(",") if c.strip()]:
        family = _family(code)
        text = (sections.get(family) or {}).get(code) if family else None
        if text:
            parts.append(f"{code} — {_reflow(text)}")
        else:
            parts.append(f"{code} — see ADR {reference}")
    return "\n".join(parts)


@lru_cache(maxsize=1)
def _points_rules() -> dict:
    path = REPO / "backend" / "app" / "config" / "dg_compliance.json"
    return json.loads(path.read_text(encoding="utf-8"))["adr_points"]


#: Fields that make two printed rows the same *transport entry*. The printed
#: table repeats a row for each alternative name (BENZINE / MOTORBRANDSTOF)
#: and the extraction keeps every printed line; regulatory content decides
#: whether a second card page is warranted, the name alone does not — the
#: name register already lists the alternatives on the one page.
_IDENTITY_FIELDS = (
    "class", "classification_code", "packing_group", "labels",
    "special_provisions", "limited_quantity", "excepted_quantity",
    "packing_instructions", "portable_tank_instructions",
    "portable_tank_provisions", "tank_code", "tank_provisions",
    "tank_vehicle", "carriage_packages", "carriage_bulk", "carriage_loading",
    "carriage_operation", "hazard_number", "transport_category", "tunnel_code",
)


def unique_rows(rows: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    kept: list[dict] = []
    for row in rows:
        key = tuple(str(row.get(field) or "").strip() for field in _IDENTITY_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def _rows(un: str) -> list[dict]:
    rows = [e for e in _table()["entries"] if e.get("un") == un]
    rows += [e for e in _additions()["entries"] if e.get("un") == un]
    return unique_rows(rows)


def _category_figures(un: str, category: str) -> tuple[str, str]:
    """(max quantity, multiplication factor) as ADR 1.1.3.6.3/.4 assign them.

    Note (a) of 1.1.3.6.3 lists nine UN numbers of category 1 that carry 50 kg
    at factor 20 instead of 20 kg at factor 50 — the same list the compliance
    engine applies, read from the same configuration.
    """
    rules = _points_rules()
    spec = rules["categories"].get(category)
    if spec is None:
        return "—", "—"
    note_a = rules.get("category_1_note_a", {})
    if category == "1" and un in set(note_a.get("un_numbers", ())):
        return str(note_a["max_quantity"]), str(note_a["factor"])
    max_quantity = spec["max_quantity"]
    factor = spec["factor"]
    if category == "4":
        return "Unlimited", "0"
    if category == "0":
        return "0 (no 1.1.3.6 exemption)", "—"
    return str(max_quantity), str(factor)


def _labels(row: dict) -> list[str]:
    return [part.strip() for part in (row.get("labels") or "").split(",") if part.strip()]


def _quantity_text(value: str, not_allowed: str) -> str:
    value = (value or "").strip()
    if value in {"0", "E0"}:
        return f"Not allowed ({value})"
    return value or not_allowed


def cards(un: str) -> list[CardPage]:
    rows = _rows(un)
    if not rows:
        raise SourceUnavailable(
            f"UN {un} has no row in the ADR 2025 table A reading "
            "(backend/seed/dg/adr_table_a.json)")

    names = {}
    for language in ("en", "nl"):
        found = _names(language).get(un) or []
        if found:
            names[language] = " / ".join(found)

    edition = _table().get("edition", "ADR")
    pages: list[CardPage] = []
    for row in rows:
        category = str(row.get("transport_category") or "").strip()
        max_quantity, factor = _category_figures(un, category)
        klass = str(row.get("class") or "")
        if klass == "1" and max_quantity[0].isdigit():
            max_quantity = f"{max_quantity} kg NEM"

        name_for_marking = names.get("en") or row.get("name_nl") or ""
        tank_code = (row.get("tank_code") or "").strip()
        tank_provisions = (row.get("tank_provisions") or "").strip()
        bulk = (row.get("carriage_bulk") or "").strip()
        hin = (row.get("hazard_number") or "").strip()

        provision_rows: list[tuple[str, str]] = []
        if (row.get("special_provisions") or "").strip():
            provision_rows.append(
                ("Special provisions", f"{row['special_provisions']} — see ADR 3.3"))
        if (row.get("carriage_packages") or "").strip():
            provision_rows.append(
                ("Carriage of packages",
                 _codes_with_texts(row["carriage_packages"], "7.2.4")))
        if bulk:
            provision_rows.append(("Carriage in bulk", f"{bulk} — see ADR 7.3.3"))
        if (row.get("carriage_loading") or "").strip():
            provision_rows.append(
                ("Loading, unloading and handling",
                 _codes_with_texts(row["carriage_loading"], "7.5.11")))
        if (row.get("carriage_operation") or "").strip():
            provision_rows.append(
                ("Operation", _codes_with_texts(row["carriage_operation"], "8.5")))
        if not provision_rows:
            provision_rows.append(
                ("Special provisions",
                 "No special provisions are assigned to this entry in table A."))

        packing = (row.get("packing_instructions") or "").strip()
        packaging_rows = [(
            "Packaging",
            f"Permitted in packagings in accordance with packing instructions {packing} "
            "— see ADR 4.1.4." if packing
            else "No packing instructions are assigned in column (8).")]
        portable = (row.get("portable_tank_instructions") or "").strip()
        if portable:
            extra = (row.get("portable_tank_provisions") or "").strip()
            packaging_rows.append((
                "Portable tanks",
                f"Instruction {portable}" + (f", special provisions {extra}" if extra else "")
                + " — see ADR 4.2."))

        pages.append(CardPage(
            modality="ADR",
            un=un,
            names=names or {"nl": row.get("name_nl") or ""},
            klass=dash(klass),
            packing_group=(row.get("packing_group") or "").strip() or "Not applicable",
            classification_code=dash(row.get("classification_code")),
            labels=_labels(row),
            identity_extra=[
                ("ADR 1.1.3.6", max_quantity if category else "—"),
                ("ADR tunnel restriction",
                 f"({row['tunnel_code']})" if (row.get("tunnel_code") or "").strip() else "—"),
            ],
            label_extra=[
                ("Multiplication factor", factor if category else "—"),
                ("ADR transport category", dash(category)),
            ],
            marking=f"UN {un} {name_for_marking}".strip(),
            packaging_rows=packaging_rows,
            tank_rows=[
                ("Tank code", tank_code if tank_code else "Not allowed"),
                ("Tank special provisions", dash(tank_provisions)),
                ("Tank vehicle", (row.get("tank_vehicle") or "").strip() or "Not allowed"),
                ("Transport in bulk",
                 f"Permitted under {bulk} — see ADR 7.3." if bulk
                 else "Not permitted — no code in column (17)."),
                ("Orange plates",
                 f"{hin} / {un}" if hin and tank_code else
                 (f"Hazard identification number {hin}" if hin else "Not applicable")),
            ],
            provision_rows=provision_rows,
            lq_eq=(
                _quantity_text(row.get("limited_quantity"), "—"),
                _quantity_text(row.get("excepted_quantity"), "—"),
            ),
            regulation=edition,
            source=_table().get("source", ""),
        ))
    return pages


def available_un_numbers() -> list[str]:
    """Every UN number the measured ADR table assigns at least one row."""
    numbers = {e["un"] for e in _table()["entries"] if e.get("un")}
    numbers |= {e["un"] for e in _additions()["entries"] if e.get("un")}
    return sorted(numbers)
