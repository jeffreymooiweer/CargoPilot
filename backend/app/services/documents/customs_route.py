"""Which customs references a route asks for, read off the route itself.

Two reference fields on the details step carry a condition rather than a
rule: the ENS reference for goods entering the EU customs territory, the AES
ITN for exports from the United States. Until v1.181.0 the help text named
the condition and the person filling in the form decided whether it applied.
The route is on the same screen, so the application can say it: from the
country of the loading point and the country of the destination it derives
whether each reference applies, does not, is exempt, or cannot be told — and
names the ground each time.

What the derivation rests on:

* Regulation (EU) No 952/2013 (the Union Customs Code), Article 4: the
  customs territory of the Union is the territory of the Member States with
  the named exceptions — the Faroe Islands and Greenland (Denmark), the
  island of Heligoland and the territory of Büsingen (Germany), Ceuta and
  Melilla (Spain), Livigno (Italy), the French overseas countries and
  territories — and, situated outside the Member States, Monaco. The Canary
  Islands, the Åland Islands, Mount Athos and the French outermost regions
  are inside it; they are outside the VAT territory, which is not this
  question.
* Article 127 of the same regulation: goods brought into that territory are
  covered by an entry summary declaration. It is lodged in ICS2 (DG TAXUD,
  Import Control System 2), since 1 September 2025 for every mode of
  transport, for goods brought into or via the EU, Northern Ireland, Norway
  or Switzerland. Northern Ireland: the Windsor Framework keeps the Union
  Customs Code applicable to goods entering Northern Ireland, and HMRC's
  guidance "Make an entry summary declaration using the Import Control
  System 2" asks for an ENS on movements into Northern Ireland, from Great
  Britain included. Norway and Switzerland: their security agreements with
  the Union take the ENS off what moves between them and the Union and put
  it on what enters from elsewhere — hence one area of four members here.
* 15 CFR Part 30 (the Foreign Trade Regulations), § 30.2(a)(1): Electronic
  Export Information is filed in AES for exports from the United States,
  Puerto Rico, the U.S. Virgin Islands and the foreign-trade zones to foreign
  countries, between Puerto Rico and the United States, and to the U.S.
  Virgin Islands from the United States or Puerto Rico. § 30.36 exempts
  shipments originating in the United States whose country of ultimate
  destination is Canada, with exceptions — goods for storage in Canada that
  are destined elsewhere, goods moving through Canada to a third country,
  goods needing a licence among them. § 30.37(a) exempts a commodity line
  valued at USD 2,500 or less per Schedule B number, unless a licence or
  another named condition applies.

What it does not do. It does not know the value of the goods, so it cannot
apply § 30.37(a); it does not know whether a Canadian delivery is storage for
a third country; it does not know a transit. Each verdict therefore names
its ground and stops there. And a route the application cannot read — free
text with no country in it — gets no verdict rather than a guess: the
question then stays with the person, as it did before.

How a route is read. The route fields are text. Picked from the location
database they read ``Rotterdam (NLRTM), ZH, NL``; picked from the address
lookup they end in the country's English name; typed by hand they can say
anything. So the reader takes, in this order: a location code in
parentheses, looked up in the database; a place name that Article 4 takes
out of the customs territory; the segment after the last comma, as a
two-letter code or a country name; and, last, a country name anywhere in
the text. Names are known in the four languages of the interface for the
countries this question turns on and the larger trading partners; another
country's name in the text is not read, and its route gets no verdict.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from app.services.geo.locations import location_by_code

#: The fields a verdict is given for.
FIELDS = ("ens_mrn", "aes_itn")

#: Where the goods start, first match wins; where they end up, likewise. The
#: final destination before the discharge point because "entering" and
#: "country of ultimate destination" are both about where the goods end up,
#: not where the carrier hands them over.
ORIGIN_KEYS = ("loading_point", "place_of_receipt")
DESTINATION_KEYS = ("final_destination", "place_of_delivery", "discharge_point")

#: Article 4(1) UCC: the Member States. Article 4(2): Monaco. The Åland
#: Islands have an ISO code of their own and are inside.
EU_CUSTOMS_TERRITORY = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
    "MC", "AX",
})

#: The two non-members whose security agreements make one area with the
#: Union for the entry summary declaration.
ENS_PARTNERS = frozenset({"NO", "CH"})

#: § 30.2(a)(1): the places an export is filed from.
US_SIDE = frozenset({"US", "PR", "VI"})

#: Places Article 4(1) takes out of a Member State's customs territory,
#: by UN/LOCODE where one exists and by name in any case.
OUTSIDE_TERRITORY_CODES = {"DEHGL": "DE", "ESCEU": "ES", "ESMLN": "ES"}
OUTSIDE_TERRITORY_NAMES = {
    "heligoland": "DE", "helgoland": "DE", "busingen": "DE",
    "ceuta": "ES", "melilla": "ES", "livigno": "IT",
}

#: Northern Ireland, as the route text can carry it. The subdivision codes
#: are those of ISO 3166-2:GB for the Northern Irish districts, both the
#: pre-2015 councils and the eleven that replaced them, because UN/LOCODE
#: carries both generations (Belfast is BFS, Warrenpoint is DOW, Kilkeel is
#: NMD in the same edition). The airports are the three in the province.
NORTHERN_IRELAND_NAMES = ("northern ireland", "noord-ierland", "nordirland", "irlande du nord")
NORTHERN_IRELAND_SUBDIVISIONS = frozenset({
    "ANT", "ARD", "ARM", "BLA", "BLY", "BNB", "BFS", "CKF", "CSR", "CLR", "CKT",
    "CGV", "DRY", "DOW", "DGN", "FER", "LRN", "LMV", "LSB", "MFT", "MYL", "NYM",
    "NTA", "NDN", "OMH", "STB",
    "ABC", "AND", "ANN", "CCG", "DRS", "FMO", "LBC", "MEA", "MUL", "NMD",
})
NORTHERN_IRELAND_AIRPORTS = frozenset({"BFS", "BHD", "LDY"})

#: Country names in the four languages of the interface, plus the variants
#: people type. Only what this question turns on and the larger trading
#: partners: a name not in here is not read, and the route gets no verdict.
COUNTRY_NAMES: dict[str, tuple[str, ...]] = {
    "AT": ("Austria", "Oostenrijk", "Österreich", "Autriche"),
    "BE": ("Belgium", "België", "Belgie", "Belgien", "Belgique"),
    "BG": ("Bulgaria", "Bulgarije", "Bulgarien", "Bulgarie"),
    "HR": ("Croatia", "Kroatië", "Kroatie", "Kroatien", "Croatie"),
    "CY": ("Cyprus", "Zypern", "Chypre"),
    "CZ": ("Czechia", "Czech Republic", "Tsjechië", "Tsjechie", "Tschechien",
           "Tschechische Republik", "Tchéquie", "République tchèque"),
    "DK": ("Denmark", "Denemarken", "Dänemark", "Danemark"),
    "EE": ("Estonia", "Estland", "Estonie"),
    "FI": ("Finland", "Finnland", "Finlande"),
    "FR": ("France", "Frankrijk", "Frankreich"),
    "DE": ("Germany", "Duitsland", "Deutschland", "Allemagne"),
    "GR": ("Greece", "Griekenland", "Griechenland", "Grèce"),
    "HU": ("Hungary", "Hongarije", "Ungarn", "Hongrie"),
    "IE": ("Ireland", "Ierland", "Irland", "Irlande"),
    "IT": ("Italy", "Italië", "Italie", "Italien"),
    "LV": ("Latvia", "Letland", "Lettland", "Lettonie"),
    "LT": ("Lithuania", "Litouwen", "Litauen", "Lituanie"),
    "LU": ("Luxembourg", "Luxemburg"),
    "MT": ("Malta", "Malte"),
    "NL": ("Netherlands", "The Netherlands", "Holland", "Nederland", "Niederlande", "Pays-Bas"),
    "PL": ("Poland", "Polen", "Pologne"),
    "PT": ("Portugal",),
    "RO": ("Romania", "Roemenië", "Roemenie", "Rumänien", "Roumanie"),
    "SK": ("Slovakia", "Slowakije", "Slowakei", "Slovaquie"),
    "SI": ("Slovenia", "Slovenië", "Slovenie", "Slowenien", "Slovénie"),
    "ES": ("Spain", "Spanje", "Spanien", "Espagne"),
    "SE": ("Sweden", "Zweden", "Schweden", "Suède"),
    "MC": ("Monaco",),
    "AX": ("Åland", "Åland Islands", "Ålandseilanden", "Åland-Inseln", "Îles Åland"),
    "NO": ("Norway", "Noorwegen", "Norwegen", "Norvège"),
    "CH": ("Switzerland", "Zwitserland", "Schweiz", "Suisse"),
    "GB": ("United Kingdom", "UK", "Great Britain", "England", "Scotland", "Wales",
           "Verenigd Koninkrijk", "Groot-Brittannië", "Engeland", "Schotland",
           "Vereinigtes Königreich", "Großbritannien", "Schottland",
           "Royaume-Uni", "Grande-Bretagne", "Angleterre", "Écosse", "Pays de Galles"),
    "IS": ("Iceland", "IJsland", "Island", "Islande"),
    "LI": ("Liechtenstein",),
    "FO": ("Faroe Islands", "Faroes", "Faeröer", "Färöer", "Îles Féroé"),
    "GL": ("Greenland", "Groenland", "Grönland"),
    "GI": ("Gibraltar",),
    "TR": ("Turkey", "Türkiye", "Turkije", "Türkei", "Turquie"),
    "UA": ("Ukraine", "Oekraïne", "Oekraine"),
    "RS": ("Serbia", "Servië", "Servie", "Serbien", "Serbie"),
    "MA": ("Morocco", "Marokko", "Maroc"),
    "CN": ("China", "Chine"),
    "JP": ("Japan", "Japon"),
    "IN": ("India", "Indien", "Inde"),
    "BR": ("Brazil", "Brazilië", "Brazilie", "Brasilien", "Brésil"),
    "AU": ("Australia", "Australië", "Australie", "Australien"),
    "SG": ("Singapore", "Singapur", "Singapour"),
    "AE": ("United Arab Emirates", "Verenigde Arabische Emiraten",
           "Vereinigte Arabische Emirate", "Émirats arabes unis"),
    "ZA": ("South Africa", "Zuid-Afrika", "Südafrika", "Afrique du Sud"),
    "KR": ("South Korea", "Korea", "Zuid-Korea", "Südkorea", "Corée du Sud"),
    "MX": ("Mexico", "Mexiko", "Mexique"),
    "US": ("United States", "United States of America", "USA", "U.S.A.", "U.S.",
           "Verenigde Staten", "Vereinigte Staaten", "États-Unis", "Etats-Unis"),
    "CA": ("Canada", "Kanada"),
    "PR": ("Puerto Rico",),
    "VI": ("U.S. Virgin Islands", "US Virgin Islands", "United States Virgin Islands",
           "Virgin Islands (U.S.)", "Amerikaanse Maagdeneilanden",
           "Amerikanische Jungferninseln", "Îles Vierges américaines",
           "Îles Vierges des États-Unis"),
}


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _name_index() -> list[tuple[str, str]]:
    """(folded name, code), longest name first so a longer name is never
    beaten by a shorter one it contains."""
    pairs = [(_fold(name), code) for code, names in COUNTRY_NAMES.items() for name in names]
    pairs.sort(key=lambda pair: -len(pair[0]))
    return pairs


_NAMES = _name_index()
_CODE_IN_BRACKETS = re.compile(r"\(([A-Za-z0-9]{3,7})\)")


def _has_word(folded: str, name: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", folded) is not None


@dataclass(frozen=True)
class Place:
    """A route end as far as this question needs it."""

    country: str
    northern_ireland: bool = False
    outside_customs_territory: bool = False

    @property
    def in_ens_area(self) -> bool:
        if self.outside_customs_territory:
            return False
        if self.country in EU_CUSTOMS_TERRITORY or self.country in ENS_PARTNERS:
            return True
        return self.country == "GB" and self.northern_ireland


def _from_code(code: str, northern_ireland: bool) -> Place | None:
    upper = code.upper()
    if upper in OUTSIDE_TERRITORY_CODES:
        return Place(OUTSIDE_TERRITORY_CODES[upper], outside_customs_territory=True)
    entry = location_by_code(upper)
    if entry is None:
        return None
    country = str(entry.get("country") or "").upper()
    if not country:
        return None
    if country == "GB" and not northern_ireland:
        northern_ireland = (
            str(entry.get("subdivision") or "").upper() in NORTHERN_IRELAND_SUBDIVISIONS
            or (entry.get("type") == "airport" and upper in NORTHERN_IRELAND_AIRPORTS)
        )
    return Place(country, northern_ireland=northern_ireland)


def _from_name(folded: str) -> str | None:
    for name, code in _NAMES:
        if _has_word(folded, name):
            return code
    return None


def read_place(text: Any) -> Place | None:
    """The country a route field names, or nothing when it names none."""
    raw = str(text or "").strip()
    if not raw:
        return None
    folded = _fold(raw)
    northern_ireland = any(_has_word(folded, name) for name in NORTHERN_IRELAND_NAMES)

    for match in _CODE_IN_BRACKETS.finditer(raw):
        place = _from_code(match.group(1), northern_ireland)
        if place is not None:
            return place

    for name, country in OUTSIDE_TERRITORY_NAMES.items():
        if _has_word(folded, name):
            return Place(country, outside_customs_territory=True)

    # Said in so many words. Before the name lookup, because "Ireland" sits
    # inside "Northern Ireland" and would otherwise be read as the Republic.
    if northern_ireland:
        return Place("GB", northern_ireland=True)

    tail = raw.rsplit(",", 1)[-1].strip()
    if re.fullmatch(r"[A-Za-z]{2}", tail) and tail.upper() in COUNTRY_NAMES:
        return Place(tail.upper(), northern_ireland=northern_ireland)
    tail_code = _from_name(_fold(tail))
    if tail_code is not None:
        return Place(tail_code, northern_ireland=northern_ireland)

    code = _from_name(folded)
    if code is not None:
        return Place(code, northern_ireland=northern_ireland)
    return None


@dataclass(frozen=True)
class Verdict:
    field: str
    #: "yes", "no", "exempt" or "unknown".
    applies: str
    #: The ground, as a code the interface translates.
    reason: str
    origin: str | None
    destination: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_ends(values: dict[str, Any]) -> tuple[Place | None, Place | None]:
    origin = next((p for key in ORIGIN_KEYS if (p := read_place(values.get(key)))), None)
    destination = next((p for key in DESTINATION_KEYS if (p := read_place(values.get(key)))), None)
    return origin, destination


def _ens(origin: Place | None, destination: Place | None) -> tuple[str, str]:
    if origin is None or destination is None:
        return "unknown", "ens_unknown"
    if destination.in_ens_area and not origin.in_ens_area:
        return "yes", "ens_entering"
    if origin.in_ens_area and destination.in_ens_area:
        return "no", "ens_within_area"
    if origin.in_ens_area:
        return "no", "ens_leaving"
    return "no", "ens_outside"


def _aes(origin: Place | None, destination: Place | None) -> tuple[str, str]:
    if origin is None or destination is None:
        return "unknown", "aes_unknown"
    start, end = origin.country, destination.country
    if start not in US_SIDE:
        return "no", "aes_not_us"
    if start == end:
        return "no", "aes_domestic"
    if end == "CA":
        # § 30.36 speaks of shipments originating in the United States; whether
        # that reaches a shipment from Puerto Rico or the Virgin Islands is
        # not something this module has read, so it does not say.
        return ("exempt", "aes_canada") if start == "US" else ("unknown", "aes_unresolved")
    if start == "VI" and end in ("US", "PR"):
        # Not among the movements § 30.2(a)(1) names.
        return "no", "aes_not_named"
    if {start, end} == {"US", "PR"}:
        return "yes", "aes_puerto_rico"
    if end == "VI":
        return "yes", "aes_virgin_islands"
    return "yes", "aes_export"


def assess(values: dict[str, Any]) -> dict[str, Verdict]:
    """One verdict per customs reference field, from the route in ``values``."""
    origin, destination = route_ends(values)
    start = origin.country if origin else None
    end = destination.country if destination else None
    ens_applies, ens_reason = _ens(origin, destination)
    aes_applies, aes_reason = _aes(origin, destination)
    return {
        "ens_mrn": Verdict("ens_mrn", ens_applies, ens_reason, start, end),
        "aes_itn": Verdict("aes_itn", aes_applies, aes_reason, start, end),
    }
