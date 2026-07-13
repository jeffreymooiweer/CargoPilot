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


def detect_dangerous_goods(description: str) -> tuple[bool, list[str]]:
    """True + melding wanneer een UN/ID-nummer in de omschrijving staat."""
    if detect_un_numbers(description):
        return True, ["dg_un_detected"]
    return False, []
