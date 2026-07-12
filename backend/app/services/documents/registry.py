import json
from functools import lru_cache
from typing import Any

from app.core.config import get_settings


@lru_cache
def get_registry() -> dict[str, Any]:
    path = get_settings().config_dir / "document_registry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_document(document_key: str) -> dict[str, Any] | None:
    for doc in get_registry()["documents"]:
        if doc["key"] == document_key:
            return doc
    return None


def resolve_sections(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Vervang {"ref": ...}-verwijzingen door de gedeelde sectiedefinities."""
    shared = {section["key"]: section for section in get_registry()["shared_sections"]}
    resolved: list[dict[str, Any]] = []
    for section in document.get("sections", []):
        if "ref" in section:
            definition = shared.get(section["ref"])
            if definition:
                resolved.append(definition)
        else:
            resolved.append(section)
    return resolved


def condition_met(condition: str | None, values: dict[str, Any]) -> bool:
    """Evalueer een 'veld=waarde'-conditie tegen de ingevulde waarden."""
    if not condition:
        return True
    field, _, expected = condition.partition("=")
    return str(values.get(field.strip(), "")).strip() == expected.strip()
