"""The articles library: keeping, finding, importing and exporting articles.

One article per code, case-insensitively — the code is what the office
types, and "abc-1" typed in a hurry is the same article as "ABC-1". Saving
a code that exists brings that article up to date rather than adding a
second, the same rule the address book applies, because an import is run
every time the list changes and the library must not grow by one copy of
everything each time.

The UN number is kept as four digits and nothing else: "UN 1263", "1263"
and "un1263" all become "1263", and a code without one is an article that
is not dangerous goods — the line it is put on is not flagged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.messages import detail as message_detail
from app.models.article import Article
from app.models.user import User
from app.services.spreadsheet_io import normalize_header

MAX_ARTICLES = 20_000

#: The columns of the template, in order; what the export writes and the
#: import reads, so a file round-trips.
ARTICLE_HEADERS = [
    "code",
    "name",
    "un_number",
    "proper_shipping_name",
    "technical_name",
    "class",
    "packing_group",
    "type_of_package",
    "net_per_package",
    "notes",
    "active",
]

ARTICLE_EXAMPLE = [
    "PAINT-25",
    "Alkyd paint, 25 L jerrican",
    "1263",
    "PAINT",
    "",
    "3",
    "II",
    "jerrican",
    "25 L",
    "",
    "yes",
]

COLUMN_ALIASES: dict[str, set[str]] = {
    "code": {"code", "artikelcode", "article_code", "article", "artikel", "artikelnummer", "sku", "matnr"},
    "name": {"name", "naam", "omschrijving", "description", "bezeichnung", "designation"},
    "un_number": {"un_number", "un", "un_nummer", "unnummer", "un_no", "numero_onu", "onu"},
    "proper_shipping_name": {"proper_shipping_name", "psn", "shipping_name", "juiste_vervoersnaam", "vervoersnaam", "benennung"},
    "technical_name": {"technical_name", "technische_naam", "technischer_name", "nom_technique"},
    "class": {"class", "klasse", "classe", "hazard_class"},
    "packing_group": {"packing_group", "pg", "verpakkingsgroep", "vg", "verpackungsgruppe", "groupe_emballage", "ge"},
    "type_of_package": {"type_of_package", "package", "packaging", "verpakking", "verpakkingssoort", "verpackung", "emballage"},
    "net_per_package": {"net_per_package", "net", "netto", "inhoud", "inhoud_per_verpakking", "content", "contenu"},
    "notes": {"notes", "note", "opmerking", "opmerkingen", "bemerkung", "remarque"},
    "active": {"active", "actief", "enabled", "aktiv", "actif"},
}


@dataclass
class ArticleImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[Any] = field(default_factory=list)


class ArticleError(ValueError):
    """A save the library refuses: an empty code, or a library that is full."""


# --- normalising ---------------------------------------------------------------


def un_digits(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits.zfill(4) if digits and len(digits) <= 4 else digits[:4] if digits else ""


def clean_code(value: Any) -> str:
    return str(value or "").strip()[:64]


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _bool(value: Any, default: bool = True) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return default
    return text in {"yes", "y", "true", "1", "ja", "oui", "actief", "active", "aktiv", "actif", "x"}


def normalise(payload: dict[str, Any]) -> dict[str, Any]:
    """An article's fields as the library keeps them."""
    return {
        "code": clean_code(payload.get("code")),
        "name": _text(payload.get("name"), 255),
        "un_number": un_digits(payload.get("un_number")),
        "proper_shipping_name": _text(payload.get("proper_shipping_name"), 255),
        "technical_name": _text(payload.get("technical_name"), 255),
        "hazard_class": _text(payload.get("hazard_class", payload.get("class")), 16),
        "packing_group": _text(payload.get("packing_group"), 8).upper(),
        "type_of_package": _text(payload.get("type_of_package"), 64),
        "net_per_package": _text(payload.get("net_per_package"), 64),
        "notes": _text(payload.get("notes"), 4000),
        "active": bool(payload.get("active", True)),
    }


def to_dict(article: Article) -> dict[str, Any]:
    return {
        "id": article.id,
        "code": article.code,
        "name": article.name or "",
        "un_number": article.un_number or "",
        "proper_shipping_name": article.proper_shipping_name or "",
        "technical_name": article.technical_name or "",
        "class": article.hazard_class or "",
        "packing_group": article.packing_group or "",
        "type_of_package": article.type_of_package or "",
        "net_per_package": article.net_per_package or "",
        "notes": article.notes or "",
        "active": bool(article.active),
    }


# --- finding -------------------------------------------------------------------


def by_code(db: Session, code: str) -> Article | None:
    wanted = clean_code(code)
    if not wanted:
        return None
    return db.query(Article).filter(Article.code.ilike(wanted)).first()


def search(db: Session, q: str = "", limit: int = 500, active_only: bool = False) -> list[Article]:
    query = db.query(Article)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        query = query.filter(or_(Article.code.ilike(like), Article.name.ilike(like),
                                 Article.un_number.ilike(like), Article.proper_shipping_name.ilike(like)))
    if active_only:
        query = query.filter(Article.active.is_(True))
    return query.order_by(Article.code).limit(limit).all()


# --- keeping -------------------------------------------------------------------


def upsert(db: Session, user: User | None, payload: dict[str, Any],
           existing: Article | None = None) -> tuple[Article, bool]:
    """Keep an article; the same code brings the one article up to date.
    Returns the article and whether it was created."""
    fields = normalise(payload)
    if not fields["code"]:
        raise ArticleError("An article needs a code.")
    carrier = by_code(db, fields["code"])
    if existing is not None and carrier is not None and carrier.id != existing.id:
        raise ArticleError("Another article already carries that code.")
    target = existing or carrier
    created = target is None
    if created:
        if db.query(Article).count() >= MAX_ARTICLES:
            raise ArticleError(f"The library holds {MAX_ARTICLES} articles, which is the most it may.")
        target = Article(created_by_id=user.id if user and user.id else None)
        db.add(target)
    for key, value in fields.items():
        setattr(target, key, value)
    db.commit()
    db.refresh(target)
    return target, created


def remove(db: Session, article: Article) -> None:
    db.delete(article)
    db.commit()


# --- the file ----------------------------------------------------------------------


def articles_to_rows(items: list[Article]) -> list[list[str]]:
    return [[
        item.code, item.name or "", item.un_number or "", item.proper_shipping_name or "",
        item.technical_name or "", item.hazard_class or "", item.packing_group or "",
        item.type_of_package or "", item.net_per_package or "", item.notes or "",
        "yes" if item.active else "no",
    ] for item in items]


def _column_map(header: list[str]) -> dict[str, int | None]:
    mapping: dict[str, int | None] = {key: None for key in ARTICLE_HEADERS}
    for index, cell in enumerate(header):
        name = normalize_header(cell)
        for key, aliases in COLUMN_ALIASES.items():
            if mapping[key] is None and name in aliases:
                mapping[key] = index
                break
    return mapping


def _has_header(rows: list[list[str]]) -> bool:
    if not rows:
        return False
    names = {normalize_header(cell) for cell in rows[0]}
    known = set().union(*COLUMN_ALIASES.values())
    return len(names & known) >= 2


def import_rows(db: Session, user: User | None, rows: list[list[str]]) -> ArticleImportResult:
    """Rows from a spreadsheet into the library, one article per code."""
    result = ArticleImportResult()
    if not rows:
        result.errors.append(message_detail("import.no_usable_lines"))
        return result
    if _has_header(rows):
        mapping = _column_map(rows[0])
        start = 1
    else:
        mapping = {key: (index if index < len(rows[0]) else None)
                   for index, key in enumerate(ARTICLE_HEADERS)}
        start = 0
    if mapping["code"] is None:
        mapping["code"] = 0

    def cell(row: list[str], key: str) -> str:
        index = mapping.get(key)
        return str(row[index]).strip() if index is not None and index < len(row) else ""

    for line_no, row in enumerate(rows[start:], start=start + 1):
        code = clean_code(cell(row, "code"))
        if not code:
            result.skipped += 1
            continue
        payload = {key: cell(row, key) for key in ARTICLE_HEADERS if key not in ("active",)}
        payload["active"] = _bool(cell(row, "active"))
        try:
            _article, created = upsert(db, user, payload)
        except ArticleError as exc:
            result.errors.append(message_detail("articles.row_refused", row=line_no, reason=str(exc)))
            result.skipped += 1
            continue
        if created:
            result.created += 1
        else:
            result.updated += 1
    return result
