"""Eenheden, en het omrekenen ertussen met behulp van soortelijk gewicht.

Tot nu toe was de eenheid van een regel een vrij tekstveld met "stuks" als
standaard. Wie 1200 liter diesel invoerde kreeg 1200 *stuks* diesel, en het
gewicht moest hij er zelf bij zetten. Dat is niet zozeer een ontbrekende functie
als wel een ontbrekend begrip: een hoeveelheid zonder eenheid betekent niets, en
met eenheid betekent zij precies één ding.

Het model is klein met opzet. Elke eenheid heeft een **dimensie** — massa,
volume, lengte of aantal — en een factor naar de basiseenheid van die dimensie
(kilogram of kubieke meter). Tussen massa en volume ligt precies één brug: de
dichtheid van het goed. Daarmee is elke omrekening die deze applicatie nodig
heeft een vermenigvuldiging, en is er nergens een tabel met stof-specifieke
uitzonderingen nodig.

Waar het mis kan gaan, en waarom hier een ``DensityBasis`` staat: 20 m³ grind
maal de dichtheid van grind is juist, 20 m³ staal maal de dichtheid van staal
is juist, en 20 m³ *gestapeld* hout is geen van beide — daar zit lucht tussen.
De goederendatabase draagt geen veld dat zegt welk soort dichtheid een getal is;
``docs/data-sources.md`` beweerde jarenlang van wel. Die basis wordt hier dus
uit de categorie *afgeleid* en als afgeleid gemeld, niet als vaststaand.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Dimension(str, Enum):
    """Waar een eenheid over gaat."""

    MASS = "mass"
    VOLUME = "volume"
    LENGTH = "length"
    COUNT = "count"


class DensityBasis(str, Enum):
    """Wat het getal in ``density_kg_m3`` van een goed betekent.

    Afgeleid uit de categorie, niet uit de data zelf. Zie de moduletoelichting.
    """

    SOLID = "solid"          # het materiaal zelf, zonder holtes
    BULK = "bulk"            # stortgoed: korrels met lucht ertussen
    LIQUID = "liquid"
    STACKED = "stacked"      # gestapeld of gebundeld: lucht tussen de stukken
    EFFECTIVE = "effective"  # praktijkgemiddelde per pallet of collo
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Unit:
    """Eén eenheid: waar zij over gaat en hoeveel er in de basiseenheid gaat."""

    code: str
    dimension: Dimension
    # Naar kg voor massa, naar m³ voor volume, naar meter voor lengte.
    factor: float
    # Korte weergave achter een getal, zoals het artikel het doet: "150 (sqm)".
    symbol: str


UNITS: dict[str, Unit] = {
    # Massa
    "kg": Unit("kg", Dimension.MASS, 1.0, "kg"),
    "ton": Unit("ton", Dimension.MASS, 1000.0, "t"),
    "g": Unit("g", Dimension.MASS, 0.001, "g"),
    "lb": Unit("lb", Dimension.MASS, 0.45359237, "lb"),
    # Volume
    "m3": Unit("m3", Dimension.VOLUME, 1.0, "m³"),
    "l": Unit("l", Dimension.VOLUME, 0.001, "L"),
    "hl": Unit("hl", Dimension.VOLUME, 0.1, "hL"),
    "ml": Unit("ml", Dimension.VOLUME, 0.000001, "mL"),
    # Lengte — voor profielen en balken, waar het gewicht per meter bekend is.
    "m": Unit("m", Dimension.LENGTH, 1.0, "m"),
    "cm": Unit("cm", Dimension.LENGTH, 0.01, "cm"),
    "mm": Unit("mm", Dimension.LENGTH, 0.001, "mm"),
    # Aantal. Een collo is geen natuurkundige eenheid; het gewicht ervan kan
    # alleen uit de invoer komen, nooit uit een dichtheid.
    "pcs": Unit("pcs", Dimension.COUNT, 1.0, "st"),
    "pallet": Unit("pallet", Dimension.COUNT, 1.0, "pal"),
    "box": Unit("box", Dimension.COUNT, 1.0, "ds"),
    "drum": Unit("drum", Dimension.COUNT, 1.0, "vat"),
    "ibc": Unit("ibc", Dimension.COUNT, 1.0, "IBC"),
    "bag": Unit("bag", Dimension.COUNT, 1.0, "zak"),
    "roll": Unit("roll", Dimension.COUNT, 1.0, "rol"),
    "bundle": Unit("bundle", Dimension.COUNT, 1.0, "bundel"),
}

# Welke eenheden een categorie normaal gesproken gebruikt, met de standaard
# vooraan. De gebruiker kan altijd iets anders kiezen — dit is een voorstel, geen
# hek. Een goederendatabase van 400 stoffen in 16 categorieen heeft altijd
# uitzonderingen, en vastlopen op een uitzondering is erger dan een rare eenheid.
SUGGESTED_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "liquid": ("l", "m3", "kg", "ton", "ibc", "drum"),
    "chemical": ("kg", "l", "ton", "m3", "drum", "ibc"),
    "agri": ("ton", "kg", "m3", "bag", "pallet"),
    "bulk_material": ("ton", "m3", "kg"),
    "ore_mineral": ("ton", "m3", "kg"),
    "waste": ("ton", "m3", "kg"),
    "construction": ("ton", "m3", "kg", "pcs", "pallet"),
    "concrete": ("ton", "m3", "kg"),
    "metal": ("kg", "ton", "pcs", "m", "bundle"),
    "wood": ("m3", "pcs", "m", "kg", "bundle"),
    "plastic": ("kg", "ton", "pcs", "pallet", "roll"),
    "paper": ("kg", "ton", "roll", "pallet", "pcs"),
    "textile": ("kg", "roll", "pcs", "pallet"),
    "insulation": ("m3", "pcs", "pallet", "kg"),
    "food": ("kg", "ton", "pallet", "box", "pcs"),
    "general_cargo": ("pcs", "pallet", "box", "kg"),
}

DEFAULT_SUGGESTED: tuple[str, ...] = ("pcs", "kg", "ton", "m3", "l", "pallet")

# Welk soort dichtheid het getal van een categorie is. Afgeleid, en als afgeleid
# gerapporteerd — de data zelf zegt het niet.
BASIS_BY_CATEGORY: dict[str, DensityBasis] = {
    "liquid": DensityBasis.LIQUID,
    "chemical": DensityBasis.LIQUID,
    "agri": DensityBasis.BULK,
    "bulk_material": DensityBasis.BULK,
    "ore_mineral": DensityBasis.BULK,
    "waste": DensityBasis.BULK,
    "concrete": DensityBasis.SOLID,
    "metal": DensityBasis.SOLID,
    "plastic": DensityBasis.SOLID,
    "construction": DensityBasis.SOLID,
    "insulation": DensityBasis.SOLID,
    "wood": DensityBasis.STACKED,
    "paper": DensityBasis.SOLID,
    "textile": DensityBasis.EFFECTIVE,
    "food": DensityBasis.EFFECTIVE,
    "general_cargo": DensityBasis.EFFECTIVE,
}


# --- De vorm waarin het reist ---------------------------------------------
#
# De dichtheid van eiken is 720 kg/m³ en die van staal 7850. Dat zijn de
# dichtheden van het materiaal zelf. Een kuub gestapelde planken, een kuub los
# gestort haardhout en een kuub massieve balk zijn drie verschillende gewichten
# van hetzelfde hout, en het verschil is lucht.
#
# v1.35.0 loste dat op met één verborgen factor van 0,65 voor al het hout. Dat
# was een gemiddelde dat niemands lading beschrijft. In plaats daarvan kiest de
# gebruiker nu de vorm, en die vorm draagt de factor. Datzelfde geldt voor
# staal (plaat tegenover schroot), kunststof (granulaat tegenover maalgoed) en
# papier (balen tegenover los).
#
# **Waar deze keuze niet geldt.** Bij grind, graan en erts is het opgeslagen
# getal al een stortdichtheid: die stof wordt nooit anders dan gestort vervoerd
# en de database beschrijft hem in die toestand. Daar nog eens een stortfactor
# overheen leggen telt de lucht twee keer. Hetzelfde bij vloeistoffen en bij de
# praktijkgemiddelden per pallet. De vorm wordt daarom alleen aangeboden waar
# het opgeslagen getal de stof zelf beschrijft — zie ``form_applies``.
#
# De factoren zijn praktijkwaarden en geen normen. Ze staan hier omdat
# ``seed_catalogs`` de goederentabel alleen vult wanneer die leeg is: nieuwe
# seed-gegevens bereiken een bestaande installatie nooit.


class CargoForm(str, Enum):
    """Hoe het goed op het vervoermiddel ligt."""

    SOLID = "solid"        # één stuk, of maatwerk met opgegeven afmetingen
    SHEETS = "sheets"      # platen vlak op elkaar
    BUNDLED = "bundled"    # strak gebundeld of in pakket
    STACKED = "stacked"    # netjes gestapeld, met lucht ertussen
    LOOSE = "loose"        # los gestort


# Welk deel van een kuub daadwerkelijk materiaal is.
FILL_FACTOR: dict[CargoForm, float] = {
    CargoForm.SOLID: 1.0,
    CargoForm.SHEETS: 1.0,
    CargoForm.BUNDLED: 0.75,
    CargoForm.STACKED: 0.65,
    CargoForm.LOOSE: 0.45,
}

# Welke vormen bij een categorie horen, met de standaard vooraan. Alles blijft
# kiesbaar; dit is een voorstel, net als bij de eenheden.
FORMS_BY_CATEGORY: dict[str, tuple[CargoForm, ...]] = {
    "wood": (CargoForm.STACKED, CargoForm.SOLID, CargoForm.SHEETS,
             CargoForm.BUNDLED, CargoForm.LOOSE),
    "metal": (CargoForm.SOLID, CargoForm.BUNDLED, CargoForm.STACKED, CargoForm.LOOSE),
    "plastic": (CargoForm.SOLID, CargoForm.LOOSE, CargoForm.BUNDLED, CargoForm.STACKED),
    "paper": (CargoForm.BUNDLED, CargoForm.SHEETS, CargoForm.STACKED, CargoForm.LOOSE),
    "construction": (CargoForm.SOLID, CargoForm.STACKED, CargoForm.LOOSE, CargoForm.BUNDLED),
    "concrete": (CargoForm.SOLID, CargoForm.LOOSE),
    "insulation": (CargoForm.SHEETS, CargoForm.STACKED, CargoForm.BUNDLED, CargoForm.SOLID),
    "textile": (CargoForm.BUNDLED, CargoForm.LOOSE, CargoForm.STACKED),
}

# Plaatmateriaal ligt vlak; daar is een kuub stapel bijna een kuub materiaal.
# Dit bepaalt alleen de standaardvorm — de gebruiker mag altijd iets anders.
SHEET_LIKE_WOOD = frozenset({
    "plywood", "chipboard", "osb", "mdf", "hdf", "hardboard", "softboard",
    "cork", "clt", "glulam",
})


def form_applies(category: str | None) -> bool:
    """Beschrijft het opgeslagen getal de stof zelf, of de gestorte toestand?

    Alleen in het eerste geval valt er nog een vorm overheen te leggen. Grind
    en graan dragen al een stortdichtheid; daar zou een tweede factor de lucht
    dubbel tellen.
    """
    return density_basis(category) in {DensityBasis.SOLID, DensityBasis.STACKED}


def available_forms(category: str | None) -> list[CargoForm]:
    """De vormen die bij deze categorie horen, standaard vooraan."""
    if not form_applies(category):
        return []
    key = str(category or "").strip().lower()
    return list(FORMS_BY_CATEGORY.get(key, (CargoForm.SOLID, CargoForm.STACKED,
                                            CargoForm.BUNDLED, CargoForm.LOOSE)))


def default_form(category: str | None, canonical_name: str | None = None) -> CargoForm | None:
    """De vorm die zonder keuze wordt aangenomen."""
    forms = available_forms(category)
    if not forms:
        return None
    if str(category or "").lower() == "wood" and str(canonical_name or "").lower() in SHEET_LIKE_WOOD:
        return CargoForm.SHEETS
    return forms[0]


def get_form(value: str | None) -> CargoForm | None:
    try:
        return CargoForm(str(value or "").strip().lower())
    except ValueError:
        return None


def fill_factor(
    category: str | None, canonical_name: str | None = None, form: str | None = None
) -> float:
    """Welk deel van een kuub materiaal is, gegeven de gekozen vorm."""
    if not form_applies(category):
        return 1.0
    chosen = get_form(form) or default_form(category, canonical_name)
    return FILL_FACTOR.get(chosen, 1.0) if chosen else 1.0


def effective_density(
    density_kg_m3: float | None,
    category: str | None,
    canonical_name: str | None = None,
    form: str | None = None,
) -> float | None:
    """De dichtheid van een kuub zoals hij op het vervoermiddel staat."""
    if density_kg_m3 is None:
        return None
    return density_kg_m3 * fill_factor(category, canonical_name, form)


def get_unit(code: str | None) -> Unit | None:
    """Zoek een eenheid op, ook als er 'M3', ' ton ' of 'liter' staat."""
    if not code:
        return None
    key = str(code).strip().lower().replace("³", "3").replace("²", "2")
    if key in UNITS:
        return UNITS[key]
    return _ALIASES.get(key)


# Wat mensen intypen, en wat ze bedoelen. Ruim opgezet omdat de oude vrije
# tekstinvoer jarenlang van alles heeft opgeleverd dat nog in opgeslagen
# zendingen zit en gewoon moet blijven werken.
_ALIASES: dict[str, Unit] = {}
for _code, _names in {
    "kg": ("kilo", "kilos", "kilogram", "kilograms", "kgs", "kilogramm"),
    "ton": ("t", "tonne", "tonnes", "tons", "mt", "metric ton", "tonnen"),
    "g": ("gram", "grams", "gr", "gramm"),
    "lb": ("lbs", "pound", "pounds"),
    "m3": ("m^3", "cbm", "kubieke meter", "kubiek", "cubic meter", "cubic metre", "cbms"),
    "l": ("ltr", "liter", "liters", "litre", "litres", "lt"),
    "hl": ("hectoliter", "hectolitre"),
    "ml": ("milliliter", "millilitre"),
    "m": ("meter", "meters", "metre", "metres", "mtr"),
    "cm": ("centimeter", "centimetre"),
    "mm": ("millimeter", "millimetre"),
    "pcs": ("stuk", "stuks", "st", "pc", "piece", "pieces", "ea", "each", "stück", "stk"),
    "pallet": ("pallets", "pal", "europallet", "europallets", "palette"),
    "box": ("boxes", "doos", "dozen", "ds", "karton", "carton", "cartons", "kiste"),
    "drum": ("drums", "vat", "vaten", "fass"),
    "ibc": ("ibcs", "ibc-tank", "container ibc"),
    "bag": ("bags", "zak", "zakken", "sack", "sacks", "big bag", "bigbag", "sack"),
    "roll": ("rolls", "rol", "rollen", "rolle"),
    "bundle": ("bundles", "bundel", "bundels", "bos", "bossen", "bund"),
}.items():
    for _name in _names:
        _ALIASES[_name] = UNITS[_code]


def suggested_units(category: str | None) -> list[str]:
    """De eenheden die bij deze categorie voor de hand liggen, standaard vooraan."""
    return list(SUGGESTED_BY_CATEGORY.get(str(category or "").strip().lower(), DEFAULT_SUGGESTED))


def default_unit(category: str | None) -> str:
    return suggested_units(category)[0]


def density_basis(category: str | None) -> DensityBasis:
    return BASIS_BY_CATEGORY.get(str(category or "").strip().lower(), DensityBasis.UNKNOWN)


@dataclass
class Converted:
    """Wat een hoeveelheid in massa en volume is, en wat er niet kon.

    ``mass_kg`` of ``volume_m3`` is None wanneer de omrekening niet kan worden
    gemaakt zonder te gokken. Dat is een uitkomst, geen fout: bij 40 pallets
    zonder gewicht per pallet is het gewicht onbekend, en een 0 neerzetten zou
    een totaal opleveren dat er goed uitziet en nergens op slaat.
    """

    mass_kg: float | None = None
    volume_m3: float | None = None
    basis: DensityBasis = DensityBasis.UNKNOWN
    # Waarom een van beide leeg bleef, als machineleesbare reden.
    missing: str | None = None
    # De dichtheid waarmee daadwerkelijk is gerekend, en het deel van een kuub
    # dat materiaal is. Bij een gestapelde of gestorte vorm wijkt dat af van de
    # dichtheid van het goed zelf, en dat hoort de gebruiker te kunnen zien.
    density_used_kg_m3: float | None = None
    fill_factor: float = 1.0
    form: str | None = None


def convert(
    quantity: float | None,
    unit_code: str | None,
    density_kg_m3: float | None = None,
    category: str | None = None,
    mass_per_item_kg: float | None = None,
    volume_per_item_m3: float | None = None,
    canonical_name: str | None = None,
    form: str | None = None,
) -> Converted:
    """Reken een ingevoerde hoeveelheid om naar massa en volume.

    De dichtheid slaat de brug tussen massa en volume. Ontbreekt zij, dan wordt
    alleen de kant ingevuld die rechtstreeks uit de eenheid volgt.

    De vorm bepaalt hoeveel van een kuub daadwerkelijk materiaal is: een kuub
    gestapelde planken is geen kuub hout. Zie ``fill_factor``.
    """
    basis = density_basis(category)
    chosen = get_form(form) or default_form(category, canonical_name)
    chosen_name = chosen.value if chosen else None
    factor = fill_factor(category, canonical_name, form)
    if density_kg_m3 is not None and factor != 1.0:
        density_kg_m3 = density_kg_m3 * factor
    unit = get_unit(unit_code)
    if quantity is None or unit is None:
        return Converted(basis=basis, missing="unit" if quantity is not None else "quantity")

    amount = float(quantity)
    if amount < 0:
        return Converted(basis=basis, missing="negative")

    if unit.dimension is Dimension.MASS:
        mass = amount * unit.factor
        volume = mass / density_kg_m3 if density_kg_m3 else None
        return Converted(mass, volume, basis, None if volume is not None else "density",
                         density_kg_m3, factor, chosen_name)

    if unit.dimension is Dimension.VOLUME:
        volume = amount * unit.factor
        mass = volume * density_kg_m3 if density_kg_m3 else None
        return Converted(mass, volume, basis, None if mass is not None else "density",
                         density_kg_m3, factor, chosen_name)

    if unit.dimension is Dimension.COUNT:
        # Een aantal draagt geen natuurkunde in zich. Zonder gewicht of volume
        # per stuk valt er niets te berekenen, en dat wordt gemeld.
        mass = amount * mass_per_item_kg if mass_per_item_kg else None
        volume = amount * volume_per_item_m3 if volume_per_item_m3 else None
        if mass is None and volume is not None and density_kg_m3:
            mass = volume * density_kg_m3
        if volume is None and mass is not None and density_kg_m3:
            volume = mass / density_kg_m3
        missing = None if (mass is not None or volume is not None) else "per_item"
        return Converted(mass, volume, basis, missing, density_kg_m3, factor, chosen_name)

    # Lengte: alleen bruikbaar met een gewicht per meter, dat de profielentabel
    # levert. Dat pad loopt via pipeline.py en niet hierlangs.
    return Converted(basis=basis, missing="length_needs_profile")


def format_quantity(quantity: float | None, unit_code: str | None) -> str:
    """"1200 L" — het getal met het symbool van zijn eenheid erachter.

    Het artikel zet de eenheid klein achter de waarde in plaats van er een
    kolom voor te reserveren; dit levert de tekst waar de interface dat mee doet.
    """
    if quantity is None:
        return ""
    unit = get_unit(unit_code)
    number = f"{quantity:,.2f}".rstrip("0").rstrip(".").replace(",", " ")
    return f"{number} {unit.symbol}" if unit else number
