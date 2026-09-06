"""Reading a number out of what somebody typed.

"800 kg", "1.250,5 L", "1,250.5", "12,5", "-5 L": the quantity fields are
free text, and a number in them arrives with whichever separators the
person's keyboard and habit produced. Until v1.190.0 every reader took the
first run of digits with one optional separator, which read "1.250,5" as
1.25 and "1,250.5" as 1.25 — a thousandfold error in a field that decides
an exemption. This module is the one reader now, so the compliance check,
the trip check and the IFTDGN cannot disagree about what a quantity says.

The rules, in order:

1. The first run of digits and separators is the number; what follows is
   the unit, read elsewhere. A leading minus counts: "-5 L" is -5, and it is
   the caller's job to refuse it, not this module's to make it positive.
2. With both "." and "," present the last one is the decimal separator and
   the other marks thousands: "1.250,5" and "1,250.5" are both 1250.5.
3. With one separator appearing more than once it marks thousands:
   "1.250.000" is 1250000.
4. With one separator appearing once, followed by exactly three digits and
   preceded by one to three digits not starting with a zero, it marks
   thousands: "1.250" is 1250 and "12,500" is 12500. Anything else makes it
   a decimal separator: "12,5" is 12.5, "0.500" is 0.5, "1000.000" is 1000.
5. Thousands come in groups of three. A number that does not fit
   ("1.2.3,4", "1,23,456") is not a number, and None comes back rather than
   a guess.
"""
from __future__ import annotations

import math
import re
from typing import Any

_NUMBER = re.compile(r"-?\d[\d.,]*")


def parse_number(value: Any) -> float | None:
    """The first number in ``value``, sign kept, or None when there is none."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    match = _NUMBER.search(str(value))
    if not match:
        return None
    token = match.group(0).rstrip(".,")
    negative = token.startswith("-")
    digits = token.lstrip("-")
    dots, commas = digits.count("."), digits.count(",")

    if dots and commas:
        decimal = "." if digits.rfind(".") > digits.rfind(",") else ","
        thousands = "," if decimal == "." else "."
    elif dots or commas:
        separator = "." if dots else ","
        if dots + commas > 1:
            decimal, thousands = "", separator
        else:
            head, tail = digits.split(separator)
            grouped = len(tail) == 3 and 1 <= len(head) <= 3 and head[0] != "0"
            decimal, thousands = ("", separator) if grouped else (separator, "")
    else:
        decimal = thousands = ""

    integer, fraction = digits, ""
    if decimal:
        if digits.count(decimal) != 1:
            return None
        integer, fraction = digits.split(decimal)
    if thousands:
        groups = integer.split(thousands)
        if not (1 <= len(groups[0]) <= 3 and all(len(g) == 3 for g in groups[1:])):
            return None
        integer = "".join(groups)
    if not integer.isdigit() or (fraction and not fraction.isdigit()):
        return None
    number = float(f"{integer}.{fraction}" if fraction else integer)
    return -number if negative else number


def positive_number(value: Any) -> float | None:
    """The number when it is one and greater than zero; otherwise None."""
    number = parse_number(value)
    return number if number is not None and number > 0 else None
