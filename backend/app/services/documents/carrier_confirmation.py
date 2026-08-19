"""Reading a booking confirmation, so nobody retypes what the carrier sent.

The numbers a carrier assigns — the air waybill number, the booking
reference, the customs references that come back from a filing — arrive in a
confirmation e-mail after the booking, which is exactly when the wizard's
fields for them are still empty. Pasting that e-mail here fills them.

Every extraction is a *format*, not a guess:

* an AWB number is three digits (the airline prefix), then eight, of which
  the last is the serial modulo 7 — the check digit IATA prints on every
  air waybill. A random eleven-digit phone number fails it six times in
  seven, which is what keeps this regex from grabbing one;
* an MRN (ENS in ICS2, or an export declaration) is 18 characters: year,
  country, alphanumerics — with a Luhn-like check digit at the end that
  this parser deliberately does not verify, because member states have
  printed MRNs with deviant check digits and a reader that rejects a real
  MRN is worse than one that accepts a mistyped one. The shape alone is
  distinctive enough at 18 characters;
* an AES ITN is the letter X and fourteen digits, the first eight of which
  are the filing date — printed exactly so on every US export confirmation;
* a booking reference has no format of its own, so it is only read where
  the confirmation itself names it one: a token after "booking", "boeking",
  "Buchung" or "réservation" wording.

What the text does not contain is absent from the answer — never invented,
never defaulted. The caller decides what to do with the findings; the
interface fills only fields that are still empty, so nothing a user typed is
ever overwritten.
"""
from __future__ import annotations

import re

#: Prefix, seven digits and the mod-7 check digit, each part separable —
#: confirmations print 074-98765434, 074 98765434 and 074 9876543 4 alike.
_AWB = re.compile(r"\b(\d{3})[- ]?(\d{7})[- ]?(\d)\b")

#: Two year digits, ISO country letters, thirteen alphanumerics, check digit.
_MRN = re.compile(r"\b(\d{2}[A-Z]{2}[A-Z0-9]{13}\d)\b")

#: The letter X and the filing date plus six digits.
_ITN = re.compile(r"\b(X\d{14})\b")

#: A named booking reference: the word, an optional qualifier (longest
#: variants first, or "ref" eats the front of "reference" and the tail gets
#: captured as the token), a separator, then the token itself — uppercase
#: only, case-sensitively, so a lowercase word like "confirmed" never reads
#: as a reference, and at least five characters so "no" is never one.
_BOOKING = re.compile(
    r"(?:booking|boeking(?:s)?|buchung(?:s)?|r[ée]servation)\s*"
    r"(?:number|nummer|num[ée]ro|reference|referentie|ref\.?|no\.?|nr\.?)?\s*[:#]?\s*"
    r"((?-i:[A-Z0-9][A-Z0-9-]{4,}))",
    re.IGNORECASE,
)


def _awb_number(text: str) -> str | None:
    for match in _AWB.finditer(text):
        prefix, serial, check = match.groups()
        if int(serial) % 7 == int(check):
            return f"{prefix}-{serial}{check}"
    return None


def parse_carrier_confirmation(text: str) -> dict[str, str]:
    """The carrier-assigned references the text actually carries.

    Keys that may appear: ``awb_number``, ``booking_number``, ``ens_mrn``,
    ``aes_itn``. A key the text does not support is left out entirely.
    """
    found: dict[str, str] = {}
    if not text or not text.strip():
        return found

    awb = _awb_number(text)
    if awb:
        found["awb_number"] = awb

    booking = _BOOKING.search(text)
    if booking:
        candidate = booking.group(1).rstrip("-")
        # A booking line can also carry the AWB itself; that one already has
        # a home, and repeating it as the booking reference helps nobody.
        if not awb or candidate.replace("-", "") != awb.replace("-", ""):
            found["booking_number"] = candidate

    mrn = _MRN.search(text)
    if mrn:
        found["ens_mrn"] = mrn.group(1)

    itn = _ITN.search(text)
    if itn:
        found["aes_itn"] = itn.group(1)

    return found
