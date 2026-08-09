"""Een extra taal moet compleet zijn, anders is zij misleidend.

Het gevaar van een taal erbij zit niet in wat er misgaat maar in wat er
stilletjes goed lijkt te gaan: een ontbrekende vertaling valt terug op een
andere taal, het scherm blijft werken en de gebruiker ziet een Frans formulier
met Nederlandse veldnamen zonder te merken dat er iets mist. Bij een
vervoersdocument is dat geen cosmetisch probleem — een afzender die
"Verpakkingsgroep" niet leest, vult hem niet in.

Deze tests lopen daarom over de gegevensbestanden zelf: elk blokje dat een
Nederlandse én een Engelse tekst draagt, moet er ook één dragen in elke andere
taal die de applicatie zegt te spreken. Zo landt een nieuwe tekst in alle talen
tegelijk of hij landt niet.

**Deze tests noemen geen enkele taal bij naam.** Ze lezen `SUPPORTED` uit
`app.core.languages` en eisen elke taal daarin behalve `nl` en `en`, die de
brontalen zijn. Tot v1.44.0 stond overal letterlijk `"de"`, en toen het Frans
erbij kwam bewaakten ze het Frans dus niet — een taal toevoegen betekende toen
óók de bewaker uitbreiden, en precies dat vergeet je. Nu is `SUPPORTED` de enige
plek waar een taal wordt aangezet.
"""

import ast
import json
from pathlib import Path

import pytest

from app.core.languages import DEFAULT, SUPPORTED, normalise, pick
from app.services.parser.language_detector import detect_language
from app.services.parser.product_detector import detect_product_type

ROOT = Path(__file__).resolve().parents[1]

# De bestanden waaruit tekst naar het scherm en naar de documenten gaat.
TRANSLATED_FILES = [
    "app/config/dg_instructions.json",
    "app/config/dg_compliance.json",
    "app/config/document_registry.json",
    "seed/dg/ems.json",
    "seed/dg/packagings.json",
    "seed/dg/segregation_groups.json",
    "seed/dg/imdg_42_24.json",
    # De goederendatabase: de naam die de gebruiker aanklikt wordt de
    # omschrijving op zijn vrachtbrief.
    "seed/materials.json",
    "seed/reference_items.json",
]

# Sommige blokken dragen hun talen als achtervoegsel: note_nl/note_en.
SUFFIXES = ("note", "items", "changes", "assigned_to_note")

#: De talen die bewaakt worden: alles wat de applicatie spreekt, behalve de twee
#: brontalen. Groeit vanzelf mee met `SUPPORTED`.
EXTRA_LANGUAGES = tuple(language for language in SUPPORTED if language not in ("nl", "en"))


def translated_blocks(value, language, path=""):
    """Elk blokje met een Nederlandse én Engelse tekst, met zijn pad."""
    if isinstance(value, dict):
        if "nl" in value and "en" in value:
            yield path or ".", value, language
        for suffix in SUFFIXES:
            if f"{suffix}_nl" in value and f"{suffix}_en" in value:
                yield f"{path}#{suffix}", value, f"{suffix}_{language}"
        for key, item in value.items():
            yield from translated_blocks(item, language, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from translated_blocks(item, language, f"{path}[{index}]")


def source_key(block_key, language):
    """Bij `de` hoort `en`; bij `note_de` hoort `note_en`."""
    return "en" if block_key == language else f"{block_key[: -len(language)]}en"


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
@pytest.mark.parametrize("name", TRANSLATED_FILES)
def test_every_translated_text_carries_each_extra_language(name, language):
    incomplete = [path for path, block, key in translated_blocks(load(name), language)
                  if not block.get(key)]
    assert incomplete == [], f"{name}: geen {language} voor {incomplete[:5]}"


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
@pytest.mark.parametrize("name", TRANSLATED_FILES)
def test_a_translation_keeps_the_shape_of_the_other_languages(name, language):
    """Een lijst blijft een lijst, en even lang.

    De vaste teksten van een formulier en de vrijstellingsbepalingen van
    1.1.3.6 zijn lijsten; een vertaling die daar één regel van maakt levert
    een document met vier ontbrekende bepalingen op.
    """
    wrong = []
    for path, block, key in translated_blocks(load(name), language):
        english, translated = block[source_key(key, language)], block[key]
        if type(translated) is not type(english):
            wrong.append(f"{path}: {type(translated).__name__} vs {type(english).__name__}")
        elif isinstance(english, list) and len(translated) != len(english):
            wrong.append(f"{path}: {len(translated)} regels vs {len(english)}")
    assert wrong == []


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
def test_a_translation_is_not_simply_the_dutch_text(language):
    """Een 'vertaling' die de Nederlandse tekst herhaalt, is geen vertaling.

    Vakbegrippen die overal onvertaald blijven staan zijn de uitzondering —
    "Proper Shipping Name", "Verified Gross Mass", de letterlijk voor te
    drukken IATA-waarschuwing. Die zijn te herkennen doordat het Nederlands en
    het Engels er al gelijk waren; wat daar níét gelijk was, is een zin die
    vertaald hoort te zijn.
    """
    copies = []
    for name in TRANSLATED_FILES:
        for path, block, key in translated_blocks(load(name), language):
            source = source_key(key, language)
            dutch = block[f"{source[:-2]}nl"]
            english = block[source]
            if not isinstance(dutch, str) or len(dutch.split()) <= 3:
                continue
            # Alleen hoofdletterverschil telt niet als vertaling: "Air Waybill
            # Shipping Instructions" is in elke taal dezelfde term.
            if dutch.casefold() != english.casefold() and block[key] == dutch:
                copies.append(f"{name}{path}")
    assert copies == []


# --- Ook de teksten die in de code zelf staan ------------------------------


def bilingual_literals(tree):
    """Elk dict-literaal in de broncode met een 'nl'- én een 'en'-sleutel."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        if {"nl", "en"} <= keys:
            yield node.lineno, keys


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
def test_no_translation_left_behind_in_the_code(language):
    """De helft van de teksten staat niet in een gegevensbestand maar in de
    code: de vaste teksten van de exporter, de scheidingswoorden, de
    productnamen. Die zijn bij het toevoegen van een taal net zo makkelijk te
    vergeten, en juist daar valt het niet op — een tweewegkeuze levert dan
    zonder klacht de verkeerde taal.
    """
    missing = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for lineno, keys in bilingual_literals(tree):
            if language not in keys:
                missing.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert missing == []


def test_nothing_decides_between_two_languages_any_more():
    """`"en" if language.startswith("en") else "nl"` was de oude manier. Zo'n
    tak geeft een derde taal stilzwijgend het verkeerde antwoord; hij hoort
    door `normalise()` en `pick()` te zijn vervangen."""
    offenders = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        if path.name == "languages.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if 'lang == "nl"' in line or 'language == "nl"' in line or 'startswith("en")' in line:
                offenders.append(f"{path.relative_to(ROOT)}:{number}")
    assert offenders == []


# --- De keuze zelf --------------------------------------------------------


def test_the_frontend_offers_the_same_languages():
    """Duits op het scherm en Nederlands in de export is erger dan alleen
    Nederlands: de gebruiker denkt dan dat hij een Duits document krijgt."""
    source = (ROOT.parent / "frontend/src/i18n/language.ts").read_text(encoding="utf-8")
    line = next(line for line in source.splitlines() if "SUPPORTED_LANGUAGES" in line)
    assert all(f'"{lang}"' in line for lang in SUPPORTED), line


@pytest.mark.parametrize("given,expected", [
    ("de", "de"), ("DE", "de"), ("de-AT", "de"), ("de_DE", "de"),
    ("en", "en"), ("en-GB", "en"), ("nl", "nl"),
    # Frans hoort sinds v1.44.0 bij SUPPORTED en valt dus niet meer terug op
    # de standaardtaal. Deze regel stond er als bewijs dat een onbekende taal
    # netjes werd opgevangen; die rol is nu voor "it".
    ("fr", "fr"), ("fr-BE", "fr"), ("FR_CH", "fr"),
    ("it", DEFAULT), ("", DEFAULT), (None, DEFAULT), (123, DEFAULT),
])
def test_a_language_code_is_narrowed_to_one_we_speak(given, expected):
    assert normalise(given) == expected


def test_a_missing_translation_falls_back_instead_of_showing_nothing():
    """Een veldnaam in een andere taal kan de gebruiker nog lezen; een veld
    zonder naam niet."""
    assert pick({"nl": "Afzender", "en": "Consignor"}, "de") == "Consignor"
    assert pick({"nl": "Afzender"}, "en") == "Afzender"
    assert pick({"de": "Absender"}, "de") == "Absender"


def test_an_empty_translation_counts_as_missing():
    # Een lege string in het register zou anders een leeg label opleveren.
    assert pick({"nl": "Afzender", "en": "", "de": ""}, "de") == "Afzender"


# --- De taal van wat de gebruiker plakt ------------------------------------


@pytest.mark.parametrize("text,expected", [
    ("Stalen hoekprofiel 80x80x8x6000", "nl"),
    ("Steel angle profile 80x80x8x6000", "en"),
    ("Stahl Winkelprofil 80x80x8x6000, 8 Stück", "de"),
    ("Träger HEA200, Länge 6000", "de"),
])
def test_a_pasted_line_gets_its_answer_in_its_own_language(text, expected):
    """De afgeleide omschrijving komt terug in de taal van de invoer; wie
    Duits plakt kreeg tot nu toe Engels terug."""
    assert detect_language(text) == expected


@pytest.mark.parametrize("text", ["", "artikel 12345", None])
def test_without_a_clue_the_paste_counts_as_dutch(text):
    assert detect_language(text) == DEFAULT


@pytest.mark.parametrize("text,expected", [
    ("Stahl Winkelprofil 80x80x8x6000", "angle_profile"),
    ("Quadratrohr 60x60x3", "square_tube"),
    ("Stahlrohr 42,4x2,6", "round_tube"),
    ("Rundstab 20 mm", "round_bar"),
    ("Stahlblech 2000x1000x5", "plate"),
    ("Träger HEA200 6000", "beam"),
    ("Betonplatte 2000x1000", "concrete_slab"),
    ("Sperrholz 18 mm", "plywood"),
    ("PVC-Rohr 110 mm", "pvc_pipe"),
    ("Kunststoffplatte 3 mm", "plastic_sheet"),
])
def test_a_german_description_is_recognised_as_a_product(text, expected):
    """De taal van het scherm helpt niet als de invoer niet herkend wordt: een
    onherkend product levert geen gewicht en dus geen bruikbaar document."""
    assert detect_product_type(text) == expected


def test_a_german_plastic_pipe_is_not_mistaken_for_a_steel_one():
    """Een kaal 'Rohr' zou ook een pvc-buis opslokken, en die weegt een orde
    van grootte minder."""
    assert detect_product_type("PVC-Rohr 110 mm") == "pvc_pipe"
    assert detect_product_type("Kunststoffrohr 110 mm") == "pvc_pipe"


def test_a_word_that_two_languages_share_does_not_decide():
    """'verzinkt' en 'beton' staan in de Nederlandse én de Duitse lijst. Een
    regel die alleen zo'n woord draagt mag niet naar het Duits kantelen."""
    assert detect_language("beton verzinkt") == "nl"
    assert detect_language("Blech beton verzinkt") == "de"  # 'Blech' geeft de doorslag


def test_something_that_is_not_a_translation_block_yields_the_default():
    assert pick(None, "de") == ""
    assert pick("Absender", "de", "-") == "-"
    assert pick({}, "de", "-") == "-"
