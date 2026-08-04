"""De juiste vervoersnaam is niet zomaar mee te vertalen met het scherm.

De ADR-tabel draagt per UN-nummer twee officiële benamingen — `name_en` en
`name_de` — en de app pakte altijd de Engelse. Een Duitse afzender kreeg
"GASOLINE" op zijn CMR terwijl "BENZIN ODER OTTOKRAFTSTOFF" er in Tabel A
naast stond.

Rechttrekken kan niet met één regel, want de modaliteiten verschillen:

* ADR 5.4.1.4.1 (en langs dezelfde lijn RID/ADN) laat een Duitse benaming toe;
* IMDG 5.4.1.4.1 verlangt Engels, Frans of Spaans;
* IATA DGR 8.1.2.1 verlangt Engels.

"BENZIN" op een Shipper's Declaration is geen vertaalsmaak maar een geweigerde
zending. Deze tests leggen die grens vast — inclusief het geval waarin iemand
eerst een Duits wegdocument opmaakt en er daarna een zeetraject bij zet.
"""

import pytest

from app.services.dg.database import get_un_entries, offline_lookup
from app.services.dg.naming import (
    is_german_name,
    proper_shipping_name,
    requires_english_name,
)

# UN 1203 heet in Tabel A anders in het Duits dan in het Engels; dat maakt hem
# geschikt om het verschil aan af te lezen.
BENZINE = "1203"


def entry(un: str) -> dict:
    entries = get_un_entries(un)
    assert entries, f"UN {un} ontbreekt in de ADR-tabel"
    return entries[0]


def test_the_adr_table_actually_carries_german_names():
    """Zonder deze kolom heeft de rest van dit bestand geen grond."""
    assert entry(BENZINE)["name_de"].upper().startswith("BENZIN")
    assert entry(BENZINE)["name_en"].upper() == "GASOLINE"


@pytest.mark.parametrize("profiles", [["ADR"], ["RID"], ["ADN"], ["ADR", "RID"], []])
def test_a_land_document_in_german_gets_the_german_name(profiles):
    assert proper_shipping_name(entry(BENZINE), "de", profiles) == "BENZIN ODER OTTOKRAFTSTOFF"


@pytest.mark.parametrize("profiles", [["IMDG"], ["IATA_DGR"], ["ADR", "IMDG"], ["ADR", "IATA_DGR"]])
def test_sea_and_air_keep_english_whatever_the_screen_says(profiles):
    """Bij een multimodale zending voldoet Engels aan alle drie de regimes;
    Duits aan maar één ervan."""
    assert proper_shipping_name(entry(BENZINE), "de", profiles) == "GASOLINE"


@pytest.mark.parametrize("language", ["nl", "en", "fr", ""])
def test_every_other_language_keeps_english(language):
    """De ADR-tabel heeft geen Nederlandse kolom, dus Nederlands krijgt — net
    als voorheen — de Engelse benaming."""
    assert proper_shipping_name(entry(BENZINE), language, ["ADR"]) == "GASOLINE"


def test_an_entry_without_a_german_name_falls_back_instead_of_going_blank():
    # De alleen-IMDG-vermeldingen uit 42-24 dragen geen Duitse naam.
    assert proper_shipping_name({"name_en": "DISILANE", "name_de": ""}, "de", ["ADR"]) == "DISILANE"


def test_requires_english_name_is_case_and_whitespace_proof():
    assert requires_english_name(["imdg"])
    assert requires_english_name([" IATA_DGR "])
    assert not requires_english_name(["ADR", "RID"])
    assert not requires_english_name(None)


# --- Het gevaarlijke geval: eerst weg, daarna zee -------------------------


def test_a_german_name_on_a_sea_document_is_refused_at_export():
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document
    from tests.test_documents import BASE_VALUES, LINES

    goods = [{
        "line_id": "L1",
        "products": [{
            "un_number": "1203",
            "proper_shipping_name": "BENZIN ODER OTTOKRAFTSTOFF",
            "class": "3",
            "packing_group": "II",
            "quantity_packages": "4",
            "type_of_package": "1A1",
        }],
    }]
    errors, _ = validate_document(
        get_document("imo_dgd"), dict(BASE_VALUES), LINES, goods, "de"
    )
    about_name = [e for e in errors if "5.4.1.4.1" in e]
    assert about_name, errors
    # De melding moet zeggen wat er dan wél moet staan.
    assert "GASOLINE" in about_name[0]


def test_the_same_name_on_a_road_document_passes():
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document
    from tests.test_documents import BASE_VALUES, LINES

    goods = [{
        "line_id": "L1",
        "products": [{
            "un_number": "1203",
            "proper_shipping_name": "BENZIN ODER OTTOKRAFTSTOFF",
            "class": "3",
            "packing_group": "II",
            "quantity_packages": "4",
            "type_of_package": "1A1",
        }],
    }]
    errors, _ = validate_document(get_document("cmr"), dict(BASE_VALUES), LINES, goods, "de")
    assert [e for e in errors if "5.4.1.4.1" in e] == []


def test_an_english_name_never_trips_the_check():
    assert not is_german_name(entry(BENZINE), "GASOLINE")


def test_a_name_that_reads_the_same_in_both_languages_is_not_flagged():
    """Veel vermeldingen luiden in beide talen hetzelfde; daar valt niets over
    te melden en een waarschuwing zou alleen ruis zijn."""
    assert not is_german_name({"name_en": "TOLUENE", "name_de": "TOLUENE"}, "TOLUENE")


def test_a_technical_name_in_brackets_is_not_flagged():
    """Bij een n.e.g.-vermelding vult de afzender zelf een technische naam aan;
    dat is geen taalfout."""
    nos = entry("3082")
    assert not is_german_name(nos, f"{nos['name_en']} (ALLYLALCOHOL)")


# --- De lookup levert dezelfde naam als de export -------------------------


@pytest.mark.parametrize("profiles,expected", [
    (["ADR"], "BENZIN ODER OTTOKRAFTSTOFF"),
    (["IMDG"], "GASOLINE"),
])
def test_the_lookup_suggests_the_name_that_the_document_will_carry(profiles, expected):
    """De suggestie die de gebruiker aanklikt ís de tekst die op het document
    belandt; die twee mogen niet uiteenlopen."""
    result = offline_lookup(BENZINE, "de", profiles)
    assert result["proper_shipping_name"] == expected
