"""One assistant turn: user text in, a state patch and the next question out.

The orchestrator is deliberately deterministic. It parses goods through the
same pipeline the lines step uses, confirms substances only from the
candidates the name recognition offered, asks exactly the questions
`dg/prepare` and the document registry name as open — one per turn — and
writes answers through the same fields the wizard writes. A language model
(phase 23) may later do the reading of free text more flexibly; it can never
add a question or an answer of its own, because this module owns both lists.

Stateless by design: the wizard state travels with every request and goes
back patched. Nothing of the conversation is stored on the server, in line
with the application's privacy stance.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.dg.autofill import prepare_entries
from app.services.documents.registry import get_registry
from app.services.pipeline import parse_and_calculate

_INSTRUCTIONS_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "dg_instructions.json"
)

#: Which regulatory profiles belong to a modality — the same map the wizard
#: holds; the assistant may not invent a different one.
MODALITY_DG_PROFILES: dict[str, list[str]] = {
    "road": ["ADR"],
    "rail": ["RID"],
    "inland": ["ADN"],
    "sea": ["IMDG"],
    "air": ["IATA_DGR"],
    "multimodal": ["ADR", "IATA_DGR", "IMDG"],
}

#: "Today" in the four languages, for the drawn-up date questions.
_TODAY_WORDS = {"vandaag", "today", "heute", "aujourd'hui", "aujourdhui"}

_YES_WORDS = {"ja", "yes", "ok", "oké", "okay", "klopt", "oui", "jawohl", "yep"}
_NO_WORDS = {"nee", "no", "non", "nein", "geen", "niet"}
_SKIP_WORDS = {"overslaan", "skip", "sla over", "passer", "überspringen"}


@lru_cache(maxsize=1)
def _dg_fields() -> dict[str, Any]:
    try:
        payload = json.loads(_INSTRUCTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - config missing
        return {}
    return payload.get("dg_fields", {})


def _field_meta(field: str) -> dict[str, Any]:
    return _dg_fields().get(field, {})


def _profiles_for(state: dict[str, Any]) -> list[str]:
    return MODALITY_DG_PROFILES.get(str(state.get("modality") or ""), ["ADR"])


def _clean(value: Any) -> str:
    return str(value or "").strip()


# --- goods lines -----------------------------------------------------------

_LEADING_COUNT = re.compile(r"^(\d+(?:[.,]\d+)?)\s+(\S+)\s+(.+)$")


def _to_parser_row(segment: str) -> str:
    """One spoken segment as a row the paste parser knows.

    "1000 jerrycans diesel" carries its count and unit up front, the way
    people say it; the parser expects "description | quantity | unit". The
    unit word is only split off when the units catalogue actually knows it —
    "80x80 hoekprofiel" must not lose its measurements to this."""
    match = _LEADING_COUNT.match(segment)
    if match:
        from app.services.units import get_unit

        unit = get_unit(match.group(2))
        if unit is not None:
            quantity = match.group(1).replace(",", ".")
            return f"{match.group(3).strip()} | {quantity} | {unit.code}"
    return segment


def _apply_goods_message(
    state: dict[str, Any], message: str, db: Session, language: str,
) -> list[dict[str, Any]]:
    """Add goods lines from a free-text message, through the real pipeline.

    Every sentence or line becomes one goods line, exactly as if it had been
    typed on the lines step; recognition (UN numbers by name included) is the
    pipeline's, not ours.
    """
    text = "\n".join(_to_parser_row(part.strip())
                     for part in re.split(r"[\n;]+", message) if part.strip())
    if not text:
        return []
    result = parse_and_calculate(text, db, output_language=language)
    events: list[dict[str, Any]] = []
    lines = state.setdefault("draft_lines", [])
    next_id = max([int(l.get("id") or 0) for l in lines] + [0]) + 1
    added = 0
    for line in result.get("lines", []):
        if not _clean(line.get("description")):
            continue
        lines.append({
            "id": next_id,
            "description": line.get("description"),
            "quantity": line.get("quantity") or 1,
            "unit": line.get("unit") or "pcs",
            "dangerous_goods": bool(line.get("dangerous_goods")),
            "detected_un_numbers": line.get("detected_un_numbers") or [],
            "dg_name_candidates": line.get("dg_name_candidates") or [],
            "weight_total_kg": line.get("weight_total_kg"),
        })
        next_id += 1
        added += 1
    if added:
        events.append({"kind": "lines_added", "count": added})
    return events


# --- dangerous goods -------------------------------------------------------

def _dg_lines(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [line for line in state.get("draft_lines", [])
            if line.get("dangerous_goods")
            or line.get("confirmed_un")
            or line.get("detected_un_numbers")]


def _sync_dg_entries(state: dict[str, Any], db: Session, language: str) -> None:
    """Build or refresh the DG entries from the lines, then let the existing
    derivation fill everything derivable — the same call the DG step makes."""
    entries = state.setdefault("dg_entries", [])
    by_line = {entry.get("line_id"): entry for entry in entries}
    for line in _dg_lines(state):
        entry = by_line.get(line["id"])
        un = _clean(line.get("confirmed_un")) or _clean(
            (line.get("detected_un_numbers") or [""])[0] if line.get("detected_un_numbers") else "")
        if entry is None:
            entries.append({
                "line_id": line["id"],
                "vehicle": _clean(line.get("description")),
                "products": [{"un_number": un}],
            })
        elif un and not _clean(entry["products"][0].get("un_number")):
            entry["products"][0]["un_number"] = un
    if not entries:
        return
    prepare_lines = [
        {"line_id": line.get("id"), "quantity": line.get("quantity"),
         "unit": line.get("unit"), "weight_each_kg": line.get("weight_each_kg")}
        for line in state.get("draft_lines", [])
    ]
    prepared = prepare_entries(entries, prepare_lines, _profiles_for(state), language)
    state["dg_entries"] = prepared["entries"]
    state["_open_questions"] = prepared.get("open_questions", [])


def _skipped(state: dict[str, Any]) -> set[str]:
    return set(state.get("skipped_questions") or [])


def _next_pending(state: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """The next question, in the order that matters: substance confirmations
    first, then the DG open questions the backend named, then the documents'
    own required fields. One at a time; a chat that asks three things in one
    breath gets half answers."""
    # 1. A recognised substance awaiting confirmation.
    for line in state.get("draft_lines", []):
        candidates = line.get("dg_name_candidates") or []
        if candidates and not line.get("confirmed_un") and not line.get("dg_dismissed"):
            pending = {
                "scope": "un_confirm",
                "line_id": line.get("id"),
                "candidates": candidates,
                "options": ([c["un"] for c in candidates] if len(candidates) > 1 else []),
            }
            return pending, [{"kind": "un_question", **pending}]

    # 2. The open questions of dg/prepare.
    skipped = _skipped(state)
    for block in state.get("_open_questions") or []:
        for question in block.get("questions", []):
            key = f"dg:{block.get('line_id')}:{block.get('product_index')}:{question['field']}"
            if key in skipped:
                continue
            meta = _field_meta(question["field"])
            options = question.get("options")
            if not options and meta.get("type") == "select":
                options = [o.get("value") for o in meta.get("options", []) if o.get("value")]
            pending = {
                "scope": "dg_question",
                "line_id": block.get("line_id"),
                "product_index": block.get("product_index"),
                "un_number": block.get("un_number"),
                "field": question["field"],
                "required": bool(question.get("required")),
                "reason": question.get("reason"),
                "options": options or [],
                "label": meta.get("label"),
                "help": meta.get("help"),
                "option_labels": ({o.get("value"): o.get("label") for o in meta.get("options", [])}
                                  if meta.get("type") == "select" else {}),
            }
            return pending, [{"kind": "dg_question", **pending}]

    # 3. Required document fields still empty.
    for field in _missing_document_fields(state):
        key = f"doc:{field['field']}"
        if key in skipped:
            continue
        pending = {"scope": "doc_question", **field, "options": field.get("options") or []}
        return pending, [{"kind": "doc_question", **pending}]

    return None, [{"kind": "ready", "documents": _selected_documents(state)}]


# --- documents -------------------------------------------------------------

def _advised_documents(state: dict[str, Any]) -> list[str]:
    """The same advice the export step shows: required carries 5.4.1, the
    customary document and the DG papers are recommended (see
    DocumentAdvicePanel; the registry names the 5.4.1 document per modality)."""
    registry = get_registry()
    modality = str(state.get("modality") or "")
    modality_def = next((m for m in registry.get("modalities", [])
                         if m.get("key") == modality), None)
    docs = list(modality_def.get("documents", [])) if modality_def else []
    needs_dg = bool(_dg_lines(state))
    dg_doc = (registry.get("dg_transport_documents") or {}).get(modality)
    fallback = (registry.get("modality_defaults") or {}).get(modality)
    chosen: list[str] = []
    if needs_dg and dg_doc in docs:
        chosen.append(dg_doc)
    for key in docs:
        if key in chosen:
            continue
        doc = next((d for d in registry.get("documents", []) if d.get("key") == key), None)
        if doc is None:
            continue
        if (needs_dg and doc.get("dg_only")) or key == fallback:
            chosen.append(key)
    return chosen


def _selected_documents(state: dict[str, Any]) -> list[str]:
    selected = state.get("selected_docs")
    if isinstance(selected, list):
        return [str(key) for key in selected]
    return _advised_documents(state)


def _condition_met(condition: str | None, values: dict[str, Any]) -> bool:
    if not condition:
        return True
    field, _, expected = condition.partition("=")
    return _clean(values.get(field.strip())) == expected.strip()


def _missing_document_fields(state: dict[str, Any]) -> list[dict[str, Any]]:
    registry = get_registry()
    shared = {s.get("key"): s for s in registry.get("shared_sections", [])}
    values = state.get("doc_values") or {}
    seen: set[str] = set()
    missing: list[dict[str, Any]] = []
    for key in _selected_documents(state):
        doc = next((d for d in registry.get("documents", []) if d.get("key") == key), None)
        if doc is None:
            continue
        for section in doc.get("sections", []):
            resolved = shared.get(section.get("ref")) if section.get("ref") else section
            if not resolved:
                continue
            for field in resolved.get("fields", []) or []:
                if field.get("status") != "USER_REQUIRED":
                    continue
                if field.get("condition") and not _condition_met(field["condition"], values):
                    continue
                name = field.get("key")
                if name in seen or _clean(values.get(name)):
                    continue
                seen.add(name)
                missing.append({
                    "field": name,
                    "label": field.get("label"),
                    "type": field.get("type") or "text",
                    "document": key,
                    "options": [o.get("value") for o in field.get("options", []) or []],
                    "option_labels": {o.get("value"): o.get("label")
                                      for o in field.get("options", []) or []},
                })
    return missing


# --- answers ---------------------------------------------------------------

def _match_option(
    message: str,
    options: list[str],
    option_labels: dict[str, Any] | None = None,
) -> str | None:
    """A chip click arrives verbatim; a typed answer gets a tolerant match.

    Matched against the option value *and* its labels in every language —
    the stored value of the carriage mode is "packages", but the person
    answering typed "colli", and both mean the same stored answer. Exact and
    case-insensitive first, then an unambiguous substring. Ambiguity is not
    resolved here: no match means the question is asked again."""
    lowered = message.strip().casefold()
    if not lowered:
        return None
    aliases: dict[str, set[str]] = {}
    for option in options:
        names = {str(option).casefold()}
        label = (option_labels or {}).get(option)
        if isinstance(label, dict):
            names |= {str(text).casefold() for text in label.values() if text}
        elif label:
            names.add(str(label).casefold())
        aliases[option] = names
    for option, names in aliases.items():
        if lowered in names:
            return option
    partial = [option for option, names in aliases.items()
               if any(lowered in name for name in names)]
    if len(partial) == 1:
        return partial[0]
    return None


def _apply_answer(
    state: dict[str, Any], pending: dict[str, Any], message: str, language: str,
) -> list[dict[str, Any]]:
    text = message.strip()
    lowered = text.casefold()
    scope = pending.get("scope")

    if lowered in _SKIP_WORDS and not pending.get("required"):
        key = (f"dg:{pending.get('line_id')}:{pending.get('product_index')}:{pending.get('field')}"
               if scope == "dg_question" else f"doc:{pending.get('field')}")
        state.setdefault("skipped_questions", []).append(key)
        return [{"kind": "skipped", "field": pending.get("field")}]

    if scope == "un_confirm":
        line = next((l for l in state.get("draft_lines", [])
                     if l.get("id") == pending.get("line_id")), None)
        if line is None:
            return [{"kind": "not_understood"}]
        candidates = pending.get("candidates") or []
        if lowered in _NO_WORDS:
            line["dg_dismissed"] = True
            line["dangerous_goods"] = False
            return [{"kind": "un_dismissed"}]
        chosen = None
        if len(candidates) == 1 and lowered in _YES_WORDS:
            chosen = candidates[0]
        else:
            digits = "".join(ch for ch in text if ch.isdigit())
            chosen = next((c for c in candidates if c.get("un") == digits.zfill(4)), None)
        if chosen is None:
            return [{"kind": "not_understood"}]
        line["confirmed_un"] = chosen["un"]
        line["dangerous_goods"] = True
        line.pop("dg_dismissed", None)
        return [{"kind": "un_confirmed", "un": chosen["un"]}]

    if scope == "dg_question":
        options = pending.get("options") or []
        value: str | None = (
            _match_option(text, options, pending.get("option_labels"))
            if options else text
        )
        if options and value is None:
            return [{"kind": "not_understood"}]
        if not _clean(value):
            return [{"kind": "not_understood"}]
        entry = next((e for e in state.get("dg_entries", [])
                      if e.get("line_id") == pending.get("line_id")), None)
        if entry is None:
            return [{"kind": "not_understood"}]
        product = entry["products"][int(pending.get("product_index") or 0)]
        product[pending["field"]] = value
        return [{"kind": "answered", "field": pending["field"], "value": value}]

    if scope == "doc_question":
        value = text
        if pending.get("type") == "date" and lowered in _TODAY_WORDS:
            value = _dt.date.today().isoformat()
        options = pending.get("options") or []
        if options:
            matched = _match_option(text, options, pending.get("option_labels"))
            if matched is None:
                return [{"kind": "not_understood"}]
            value = matched
        if not _clean(value):
            return [{"kind": "not_understood"}]
        state.setdefault("doc_values", {})[pending["field"]] = value
        return [{"kind": "answered", "field": pending["field"], "value": value}]

    return [{"kind": "not_understood"}]


# --- the turn --------------------------------------------------------------

def step(
    state: dict[str, Any],
    message: str,
    pending: dict[str, Any] | None,
    db: Session,
    language: str = "nl",
) -> dict[str, Any]:
    """One turn of the conversation. Everything the reply contains is either
    the user's own data run through the existing services, or a question the
    backend itself raised — never the assistant's invention."""
    state = json.loads(json.dumps(state or {}))  # work on a copy; stateless contract
    events: list[dict[str, Any]] = []

    if pending:
        events.extend(_apply_answer(state, pending, message, language))
        if events and events[-1]["kind"] == "not_understood":
            # The same question again, with its options; nothing was changed.
            _sync_dg_entries(state, db, language)
            next_pending, ask_events = _next_pending(state)
            state.pop("_open_questions", None)
            return {"state": state, "events": events + ask_events, "pending": next_pending}
    elif _clean(message):
        events.extend(_apply_goods_message(state, message, db, language))
        if not events:
            events.append({"kind": "not_understood"})

    _sync_dg_entries(state, db, language)
    next_pending, ask_events = _next_pending(state)
    state.pop("_open_questions", None)
    return {"state": state, "events": events + ask_events, "pending": next_pending}
