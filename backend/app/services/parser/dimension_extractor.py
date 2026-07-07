import re
from dataclasses import dataclass

UNIT_TO_METERS = {
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
}


@dataclass
class Dimensions:
    values_m: list[float]
    length_m: float | None = None
    width_m: float | None = None
    height_m: float | None = None
    thickness_m: float | None = None
    profile_size: str | None = None


def _to_meters(value: float, unit: str | None) -> float:
    if unit:
        factor = UNIT_TO_METERS.get(unit.lower())
        if factor:
            return value * factor
    return value * 0.001  # default mm for construction materials


def parse_length_patterns(text: str) -> float | None:
    patterns = [
        r"(?:l(?:engte)?|length)\s*[=:]?\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m|millimeters?|centimeters?|meters?)?",
        r"(\d+(?:[.,]\d+)?)\s*(mm|cm|m)\b",
        r"(\d+(?:[.,]\d+)?)\s*(millimeters?|centimeters?|meters?)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1).replace(",", "."))
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            return _to_meters(val, unit)
    return None


def extract_dimensions(text: str) -> Dimensions:
    text = text.strip()
    profile_match = re.search(r"\b(UNP|UPN|UPE|IPE|HEA|HEB|HEM)\s*(\d+)\b", text, re.IGNORECASE)
    if profile_match:
        length_m = parse_length_patterns(text)
        return Dimensions(
            values_m=[],
            length_m=length_m,
            profile_size=f"{profile_match.group(1).upper()} {profile_match.group(2)}",
        )

    dim_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?\s*(mm|cm|m)?",
        text,
        re.IGNORECASE,
    )
    if dim_match:
        nums = [float(dim_match.group(i).replace(",", ".")) for i in range(1, 5) if dim_match.group(i)]
        unit = dim_match.group(5)
        values_m = [_to_meters(n, unit) for n in nums]
        if len(values_m) == 4:
            return Dimensions(
                values_m=values_m,
                width_m=values_m[0],
                height_m=values_m[1],
                thickness_m=values_m[2],
                length_m=values_m[3],
            )
        if len(values_m) == 3:
            return Dimensions(
                values_m=values_m,
                width_m=values_m[0],
                height_m=values_m[1],
                length_m=values_m[2],
            )
        return Dimensions(values_m=values_m)

    length_m = parse_length_patterns(text)
    return Dimensions(values_m=[], length_m=length_m)


def meters_to_cm(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value * 100, 2)
