"""The proper shipping name cannot simply be translated along with the screen.

The ADR table carries two official names per UN number — `name_en` and `name_de`
— and the app always took the English one. A German consignor got "GASOLINE" on
their CMR while "BENZIN ODER OTTOKRAFTSTOFF" was sitting next to it in Table A.

Putting that right cannot be done with one line, because the modes differ:

* ADR 5.4.1.4.1 (and along the same lines RID/ADN) permits a German name;
* IMDG 5.4.1.4.1 requires English, French or Spanish;
* IATA DGR 8.1.2.1 requires English.

"BENZIN" on a Shipper's Declaration is not a matter of translation taste but a
refused consignment. These tests record that boundary — including the case where
somebody first draws up a German road document and then adds a sea leg.
"""

import pytest

from app.services.dg.database import get_un_entries, offline_lookup
from app.services.dg.naming import (
    is_german_name,
    proper_shipping_name,
    requires_english_name,
    resolve_for_profile,
)

# UN 1203 is called something different in German from English in Table A; that
# makes it suitable for reading the difference off.
BENZINE = "1203"


def entry(un: str) -> dict:
    entries = get_un_entries(un)
    assert entries, f"UN {un} ontbreekt in de ADR-tabel"
    return entries[0]


def test_the_adr_table_actually_carries_german_names():
    """Without this column the rest of this file has no ground to stand on."""
    assert entry(BENZINE)["name_de"].upper().startswith("BENZIN")
    assert entry(BENZINE)["name_en"].upper() == "GASOLINE"


@pytest.mark.parametrize("profiles", [["ADR"], ["RID"], ["ADN"], ["ADR", "RID"], []])
def test_a_land_document_in_german_gets_the_german_name(profiles):
    assert proper_shipping_name(entry(BENZINE), "de", profiles) == "BENZIN ODER OTTOKRAFTSTOFF"


@pytest.mark.parametrize("profiles", [["IMDG"], ["IATA_DGR"], ["ADR", "IMDG"], ["ADR", "IATA_DGR"]])
def test_sea_and_air_keep_english_whatever_the_screen_says(profiles):
    """For a multimodal consignment English satisfies all three regimes; German
    only one of them."""
    assert proper_shipping_name(entry(BENZINE), "de", profiles) == "GASOLINE"


@pytest.mark.parametrize("language", ["nl", "en", "fr", ""])
def test_every_other_language_keeps_english(language):
    """The ADR table has no Dutch column, so Dutch gets — as before — the English
    name."""
    assert proper_shipping_name(entry(BENZINE), language, ["ADR"]) == "GASOLINE"


def test_an_entry_without_a_german_name_falls_back_instead_of_going_blank():
    # The IMDG-only entries from 42-24 carry no German name.
    assert proper_shipping_name({"name_en": "DISILANE", "name_de": ""}, "de", ["ADR"]) == "DISILANE"


def test_requires_english_name_is_case_and_whitespace_proof():
    assert requires_english_name(["imdg"])
    assert requires_english_name([" IATA_DGR "])
    assert not requires_english_name(["ADR", "RID"])
    assert not requires_english_name(None)


# --- The dangerous case: road first, sea afterwards ------------------------
#
# The language of the name belongs to the document, not to the consignment. One
# consignment produces a CMR with the German name and an IMO DGF with the
# English, from the same data. Refusing the export and making the user retype
# "GASOLINE" would have them do what the app already knows.


def german_goods():
    return [{
        "line_id": "L1",
        "products": [{
            "un_number": "1203",
            "proper_shipping_name": "BENZIN ODER OTTOKRAFTSTOFF",
            "class": "3",
            "packing_group": "II",
            "quantity_packages": "4",
            "type_of_package": "1A1",
            "net_mass_liters_per_package": "20",
        }],
    }]


@pytest.mark.parametrize("profile,expected", [
    ("ADR", "BENZIN ODER OTTOKRAFTSTOFF"),
    ("RID", "BENZIN ODER OTTOKRAFTSTOFF"),
    ("ADN", "BENZIN ODER OTTOKRAFTSTOFF"),
    ("IMDG", "GASOLINE"),
    ("IATA_DGR", "GASOLINE"),
])
def test_the_document_gets_the_name_its_own_rulebook_wants(profile, expected):
    name, _ = resolve_for_profile(german_goods()[0]["products"][0], profile)
    assert name == expected


def test_a_sea_document_is_not_refused_but_corrected():
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document
    from tests.test_documents import BASE_VALUES, LINES

    errors, warnings = validate_document(
        get_document("imo_dgd"), dict(BASE_VALUES), LINES, german_goods(), "de"
    )
    assert [e for e in errors if "5.4.1.4.1" in e] == [], "export mag hier niet blokkeren"
    said = [w for w in warnings if "5.4.1.4.1" in w]
    assert said, warnings
    # The message says what happened, not what the user still has to do.
    assert "BENZIN ODER OTTOKRAFTSTOFF" in said[0] and "GASOLINE" in said[0]


def test_the_road_document_keeps_the_german_name_and_says_nothing():
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document
    from tests.test_documents import BASE_VALUES, LINES

    errors, warnings = validate_document(
        get_document("cmr"), dict(BASE_VALUES), LINES, german_goods(), "de"
    )
    assert [e for e in errors if "5.4.1.4.1" in e] == []
    assert [w for w in warnings if "5.4.1.4.1" in w] == []


def test_the_exported_sea_document_actually_carries_the_english_name():
    """The warning is not enough — it has to actually be on the sheet."""
    import openpyxl

    from app.services.documents.exporter import export_document
    from tests.test_documents import BASE_VALUES, LINES

    path = export_document(
        "imo_dgd", dict(BASE_VALUES), LINES, german_goods(), language="de"
    )
    text = "\n".join(
        str(cell)
        for row in openpyxl.load_workbook(path).active.iter_rows(values_only=True)
        for cell in row
        if cell
    )
    assert "GASOLINE" in text
    assert "BENZIN ODER OTTOKRAFTSTOFF" not in text


def test_the_exported_road_document_carries_the_german_name():
    import openpyxl

    from app.services.documents.exporter import export_document
    from tests.test_documents import BASE_VALUES, LINES

    path = export_document("cmr", dict(BASE_VALUES), LINES, german_goods(), language="de")
    text = "\n".join(
        str(cell)
        for row in openpyxl.load_workbook(path).active.iter_rows(values_only=True)
        for cell in row
        if cell
    )
    assert "BENZIN ODER OTTOKRAFTSTOFF" in text


def test_the_description_line_follows_the_document_too():
    """The 5.4.1.1.1 line is the text that goes into the goods column verbatim."""
    from app.services.dg.autofill import description_line

    product = german_goods()[0]["products"][0]
    assert "BENZIN ODER OTTOKRAFTSTOFF" in description_line(product, "ADR")
    assert "GASOLINE" in description_line(product, "IMDG")
    assert "BENZIN" not in description_line(product, "IMDG")


def test_wording_the_user_wrote_themselves_is_left_alone():
    """A technical name with an n.o.s. entry or an addition of the user's own is
    something we cannot assess, and certainly must not replace silently."""
    own = {"un_number": "1203", "proper_shipping_name": "BENZIN, ENTHÄLT ETHANOL"}
    name, replaced = resolve_for_profile(own, "IMDG")
    assert name == "BENZIN, ENTHÄLT ETHANOL"
    assert replaced == ""


def test_an_english_name_is_not_touched_and_not_reported():
    name, replaced = resolve_for_profile(
        {"un_number": "1203", "proper_shipping_name": "GASOLINE"}, "IMDG"
    )
    assert (name, replaced) == ("GASOLINE", "")


def test_an_empty_name_stays_empty_rather_than_being_invented():
    """A missing name is a separate fault; that is already reported as a missing
    field and must not be quietly filled in here."""
    assert resolve_for_profile({"un_number": "1203"}, "IMDG") == ("", "")


def test_an_english_name_never_trips_the_check():
    assert not is_german_name(entry(BENZINE), "GASOLINE")


def test_a_name_that_reads_the_same_in_both_languages_is_not_flagged():
    """Many entries read the same in both languages; there is nothing to report
    about those and a warning would be nothing but noise."""
    assert not is_german_name({"name_en": "TOLUENE", "name_de": "TOLUENE"}, "TOLUENE")


def test_a_technical_name_in_brackets_is_not_flagged():
    """With an n.o.s. entry the consignor adds a technical name themselves; that
    is not a language fault."""
    nos = entry("3082")
    assert not is_german_name(nos, f"{nos['name_en']} (ALLYLALCOHOL)")


# --- The lookup produces the same name as the export ----------------------


@pytest.mark.parametrize("profiles,expected", [
    (["ADR"], "BENZIN ODER OTTOKRAFTSTOFF"),
    (["IMDG"], "GASOLINE"),
])
def test_the_lookup_suggests_the_name_that_the_document_will_carry(profiles, expected):
    """The suggestion the user clicks *is* the text that ends up on the document;
    those two must not diverge."""
    result = offline_lookup(BENZINE, "de", profiles)
    assert result["proper_shipping_name"] == expected
