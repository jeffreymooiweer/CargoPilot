import re

#: "1000 jerrycans van 25l", "10 vaten à 200 liter", "4 IBC met 1000 kg" —
#: the content of one package, said the way people say it. The words before
#: the number are the Dutch/English/German/French ways of saying "of ... each".
PACKAGE_CONTENT = re.compile(
    r"(?:\b(?:van|met|à|a|of|each|je|mit|de)\s+)?"
    r"(\d+(?:[.,]\d+)?)\s*(l|ltr|liter|liters|litre|litres|ml|kg|kilo|kilogram|g|gram)\b",
    re.IGNORECASE,
)

_CONTENT_UNITS = {
    "l": "L", "ltr": "L", "liter": "L", "liters": "L", "litre": "L",
    "litres": "L", "ml": "mL", "kg": "kg", "kilo": "kg", "kilogram": "kg",
    "g": "g", "gram": "g",
}


def detect_package_content(description: str) -> str | None:
    """The net content of one package, read from the description.

    Whoever writes "1000 jerrycans van 25l benzine" has already said what one
    jerrycan holds; asking for it again is the kind of question this
    application exists to remove. Only the first match counts, normalised to
    the unit symbol ("25 L"). The caller decides whether the line is counted
    in packages at all — on a line measured in litres the litre figure is the
    line's own quantity, not a package content.
    """
    match = PACKAGE_CONTENT.search(description or "")
    if not match:
        return None
    amount = match.group(1).replace(",", ".")
    if amount.endswith(".0"):
        amount = amount[:-2]
    return f"{amount} {_CONTENT_UNITS[match.group(2).lower()]}"


def strip_package_content(description: str) -> str:
    """The description without the content phrase, for a line the assistant
    composes itself: "van 25l met benzine" reads as damage, "benzine" as the
    goods. Leading connector words left dangling by the removal go with it."""
    stripped = PACKAGE_CONTENT.sub(" ", description or "", count=1)
    stripped = re.sub(r"^\s*(?:van|met|à|a|of|mit|de)\s+", "", stripped.strip(),
                      flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", stripped).strip(" ,")


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


def detect_dangerous_goods(description: str) -> tuple[bool, list[str]]:
    """True + a message when a UN/ID number appears in the description."""
    if detect_un_numbers(description):
        return True, ["dg_un_detected"]
    return False, []
