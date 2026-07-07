import re

UN_PATTERN = re.compile(r"\bUN\s*[-#:]?\s*(\d{4})\b", re.IGNORECASE)
ID_PATTERN = re.compile(r"\bID\s*[-#:]?\s*(\d{4})\b", re.IGNORECASE)


def detect_un_numbers(text: str) -> list[str]:
    found: list[str] = []
    for pattern in (UN_PATTERN, ID_PATTERN):
        for match in pattern.finditer(text or ""):
            number = match.group(1)
            if number not in found:
                found.append(number)
    return found


def default_appendix_flags() -> dict[str, str | None]:
    return {
        "loaded": "Y",
        "stackable": "N",
        "rotatable": "N",
        "weapons": "N",
        "conditioned": "N",
        "temperature_c": None,
        "dangerous_goods": "N",
        "ammunition": "N",
        "itar": "N",
        "tbb": "N",
        "tbb_category": None,
    }


def apply_un_detection(description: str, flags: dict[str, str | None]) -> tuple[dict[str, str | None], list[str]]:
    """Zet dangerous_goods op Y wanneer UN/ID-nummer in de omschrijving staat."""
    un_numbers = detect_un_numbers(description)
    messages: list[str] = []
    if un_numbers:
        flags = {**flags, "dangerous_goods": "Y"}
        messages.append("dg_un_detected")
    return flags, messages
