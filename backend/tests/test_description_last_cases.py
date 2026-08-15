"""The last special cases of 5.4.1.1, and special provision 274.

Read in the UNECE English and French volumes II and the RID German edition
(printed pages 266-267 / 293 / 909), which agree; the Dutch words came with the
fase-8 reading of page 996. With these, every numbered special provision of
5.4.1.1 that a consignment field can trigger is composed — what remains of the
subsection is either class-specific extras already handled (5.4.1.2.1 NEM) or
provisions about how the document is transmitted.
"""
import pytest

from app.services.dg.autofill import description_line, prepare_entries
from app.services.dg.compliance import check_technical_name_required


def product_of(un="1350", **extra):
    prepared = prepare_entries(
        [{"line_id": "L1", "products": [{"un_number": un, **extra}]}],
        profiles=["ADR"])
    return prepared["entries"][0]["products"][0]


# --- 5.4.1.1.23: molten ------------------------------------------------------


def test_molten_joins_the_name_in_the_documents_language():
    """UN 1350 sulphur, offered molten: the qualifying word joins the name
    block — after the paired English name on a Dutch document, before the
    class: "UN 1350, ZWAVEL (SULPHUR), GESMOLTEN, 4.1, III, (E)"."""
    product = product_of(molten="yes")
    line = description_line(product, "ADR", "nl")
    assert "ZWAVEL (SULPHUR), GESMOLTEN, 4.1" in line
    assert ", MOLTEN" in description_line(product, "ADR", "en")
    assert ", GESCHMOLZEN" in description_line(product, "ADR", "de")
    assert ", FONDU" in description_line(product, "ADR", "fr")


def test_a_name_that_already_says_molten_is_not_doubled():
    """UN 2448 is SULPHUR, MOLTEN by name (3.1.2.5): nothing is added."""
    product = product_of("2448", molten="yes")
    line = description_line(product, "ADR", "en")
    assert line.count("MOLTEN") == 1


# --- 5.4.1.1.19: UN 3509 -----------------------------------------------------


def test_un_3509_carries_its_residues_and_no_quantity():
    """The book's own example: "UN 3509 PACKAGINGS, DISCARDED, EMPTY,
    UNCLEANED (WITH RESIDUES OF 3, 4.1, 6.1), 9" — and 5.4.1.1.1 (f) does not
    apply, so no total quantity is composed."""
    product = product_of("3509", residue_classes="3, 4.1, 6.1",
                         quantity_packages="4", type_of_package="kisten",
                         net_mass_liters_per_package="100 kg")
    line = description_line(product, "ADR", "en")
    assert "(WITH RESIDUES OF 3, 4.1, 6.1)" in line
    assert "400 kg" not in line
    assert "4 kisten" in line  # (e) still applies


def test_the_residues_speak_the_documents_language():
    product = product_of("3509", residue_classes="3, 6.1")
    assert "(BEVAT RESTEN VAN 3, 6.1)" in description_line(product, "ADR", "nl")
    assert "(MIT RÜCKSTÄNDEN VON 3, 6.1)" in description_line(product, "ADR", "de")
    assert "(AVEC DES RÉSIDUS DE 3, 6.1)" in description_line(product, "ADR", "fr")


def test_other_substances_never_get_a_residues_bracket():
    product = product_of("1203", residue_classes="3")
    assert "RESIDUES" not in description_line(product, "ADR", "en")


# --- 5.4.1.1.20: classified per 2.1.2.8 --------------------------------------


def test_the_2_1_2_8_statement_is_worded_as_the_provision_sets_it():
    product = product_of(classified_2_1_2_8="yes")
    assert description_line(product, "ADR", "en").endswith(
        "Classified in accordance with 2.1.2.8")
    assert description_line(product, "ADR", "nl").endswith(
        "Ingedeeld overeenkomstig 2.1.2.8")
    # The German edition sets its statement in capitals; it is kept as printed.
    assert description_line(product, "ADR", "de").endswith(
        "GEMÄSS UNTERABSCHNITT 2.1.2.8 KLASSIFIZIERT")
    assert description_line(product, "ADR", "fr").endswith(
        "Classé conformément au 2.1.2.8")


# --- special provision 274 ---------------------------------------------------


def line_of(*products):
    return [{"line_id": "L1", "products": [dict(p) for p in products]}]


def test_an_nos_entry_without_its_technical_name_is_flagged():
    """UN 1993 flammable liquid n.o.s. carries SP 274 in column (6): without a
    technical name the description is one 3.1.2.8.1 calls incomplete."""
    findings = check_technical_name_required(
        line_of({"un_number": "1993"}), "en")
    assert len(findings) == 1
    assert "274" in findings[0]["rule"]


def test_filled_in_it_is_silent():
    assert check_technical_name_required(
        line_of({"un_number": "1993",
                 "technical_name": "toluene and ethyl alcohol"})) == []


def test_an_entry_without_sp274_is_not_asked():
    """UN 1203 petrol carries no SP 274: naming a specific substance needs no
    technical name, and a warning here would teach people to ignore it."""
    assert check_technical_name_required(line_of({"un_number": "1203"})) == []


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_the_sp274_finding_speaks_four_languages(language):
    findings = check_technical_name_required(
        line_of({"un_number": "1993"}), language)
    assert findings and findings[0]["message"]


def test_it_reaches_the_document():
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document

    values = {
        "consignor_name": "Afzender", "consignor_address": "Havenweg 1",
        "consignee_name": "Ontvanger", "consignee_address": "Hafenstrasse 4",
        "loading_point": "Rotterdam", "discharge_point": "Duisburg",
        "freight_payment": "Franco", "established_place": "Rotterdam",
        "established_date": "2026-08-15",
    }
    goods = [{"line_id": "1", "products": [{
        "un_number": "1993", "proper_shipping_name": "FLAMMABLE LIQUID, N.O.S.",
        "class": "3", "packing_group": "II"}]}]
    _errors, warnings = validate_document(
        get_document("cmr"), values, [], goods, "nl")
    assert any("274" in w for w in warnings), warnings
