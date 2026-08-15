"""The special cases of 5.4.1.1: waste, salvage, empty uncleaned, environment.

Read in the official Dutch edition (printed pages 991-996) and in the RID
English and German editions, which carry the provisions word for word; the
English and French words come from the UNECE volumes II. Each case changes what
the description line must say, and none of them can be derived — whether the
goods are waste is a fact about the consignment, not about the UN number.

The words are document entries, not interface strings: the regulation
prescribes the word itself, so it follows the language of the *document* and is
always English where the document must be (IMDG 5.4.1.4.1, IATA DGR 8.1.2.1).
"""
import pytest

from app.services.dg.autofill import description_line, prepare_entries


def product_of(un="1230", **extra):
    prepared = prepare_entries(
        [{"line_id": "L1", "products": [{"un_number": un, **extra}]}],
        profiles=["ADR"])
    return prepared["entries"][0]["products"][0]


# --- 5.4.1.1.3: waste -------------------------------------------------------


def test_waste_precedes_the_proper_shipping_name():
    """The provision's own example is "UN 1230 AFVAL METHANOL, 3 (6.1), II,
    (D/E)" — the word goes after the UN number, before the name."""
    line = description_line(product_of(is_waste="yes"), "ADR", "nl")
    assert line.startswith("UN 1230, AFVAL METHANOL")


def test_waste_speaks_the_language_of_the_document():
    product = product_of(is_waste="yes")
    assert "WASTE METHANOL" in description_line(product, "ADR", "en")
    assert "ABFALL METHANOL" in description_line(product, "ADR", "de")
    assert "DÉCHET MÉTHANOL" in description_line(product, "ADR", "fr")


def test_a_name_that_already_says_waste_is_not_doubled():
    """The provision: unless this term is part of the proper shipping name."""
    product = product_of(is_waste="yes")
    product["proper_shipping_name"] = "AFVAL METHANOL"
    line = description_line(product, "ADR", "nl")
    assert line.count("AFVAL") == 1


def test_at_sea_the_waste_word_is_english_whatever_the_screen_says():
    """IMDG 5.4.1.4.1 requires English; a Dutch screen must not put AFVAL on
    a sea document."""
    line = description_line(product_of(is_waste="yes"), "IMDG", "nl")
    assert "WASTE" in line and "AFVAL" not in line


# --- 5.4.1.1.5: salvage packagings ------------------------------------------


def test_salvage_packaging_follows_the_description():
    line = description_line(
        product_of(salvage_packaging="packaging"), "ADR", "nl")
    assert "BERGINGSVERPAKKING" in line


def test_the_pressure_receptacle_gets_its_own_word():
    """5.4.1.1.5 knows two words — 4.1.1.19 and 4.1.1.20 are different
    provisions and the document says which one applied."""
    line = description_line(
        product_of(salvage_packaging="pressure_receptacle"), "ADR", "de")
    assert "BERGUNGSDRUCKGEFÄSS" in line


def test_the_salvage_word_is_refused_at_the_edge_when_unknown():
    from pydantic import ValidationError

    from app.schemas.dg_compliance import DangerousGoodsProduct

    with pytest.raises(ValidationError):
        DangerousGoodsProduct(salvage_packaging="doos")


# --- 5.4.1.1.6.1: empty uncleaned -------------------------------------------


def test_empty_uncleaned_is_said_and_the_quantity_dropped():
    """The entry joins the description, and 5.4.1.1.1 (f) then does not apply:
    a total quantity for residues nobody has weighed would be an invented
    figure on an official document."""
    product = product_of(empty_uncleaned="yes", quantity_packages="4",
                         type_of_package="vaten",
                         net_mass_liters_per_package="200 L")
    line = description_line(product, "ADR", "nl")
    assert "LEEG, ONGEREINIGD" in line
    assert "4 vaten" in line          # (e) still applies
    assert "800 L" not in line        # (f) does not


def test_empty_uncleaned_in_the_other_languages():
    product = product_of(empty_uncleaned="yes")
    assert "EMPTY, UNCLEANED" in description_line(product, "ADR", "en")
    assert "LEER, UNGEREINIGT" in description_line(product, "ADR", "de")
    assert "VIDE, NON NETTOYÉ" in description_line(product, "ADR", "fr")


# --- 5.4.1.1.18: environmentally hazardous ----------------------------------


def test_an_environmentally_hazardous_substance_carries_the_entry():
    """UN 3082 is excepted by name, so the case is exercised on a substance
    whose name does not already say it."""
    product = product_of("1203", marine_pollutant="P")
    line = description_line(product, "ADR", "nl")
    assert "MILIEUGEVAARLIJK" in line


def test_un_3077_and_3082_are_excepted_by_the_provision_itself():
    """Their *names* say it — "MILIEUGEVAARLIJKE VASTE STOF, N.E.G." — which is
    exactly why 5.4.1.1.18 excepts them: the check is that no separate entry is
    appended, not that the word is absent from a name that owns it."""
    for un in ("3077", "3082"):
        product = product_of(un, marine_pollutant="P")
        line = description_line(product, "ADR", "nl")
        assert not line.rstrip().endswith("MILIEUGEVAARLIJK")
        assert ", MILIEUGEVAARLIJK," not in line


def test_at_sea_marine_pollutant_is_the_entry():
    """The provision itself points at IMDG 5.4.1.4.3: for a chain including a
    sea leg "MARINE POLLUTANT" is the acceptable entry, and the IMDG branch
    already writes it. A second, land-styled entry would double it."""
    product = product_of("1203", marine_pollutant="P")
    line = description_line(product, "IMDG", "nl")
    assert "MARINE POLLUTANT" in line
    assert "MILIEUGEVAARLIJK" not in line


# --- and they reach the paper together --------------------------------------


def test_the_combined_line_reads_like_the_provision_wants():
    product = product_of(is_waste="yes", empty_uncleaned="yes")
    line = description_line(product, "ADR", "nl")
    # Waste in the name, the empty entry with the description.
    assert line.startswith("UN 1230, AFVAL METHANOL")
    assert "LEEG, ONGEREINIGD" in line


def test_the_form_renderer_carries_the_same_words():
    """One builder (v1.88.0): the CMR's own renderer must show the same case."""
    from app.services.documents.exporter import _dg_description

    product = product_of(is_waste="yes")
    assert "AFVAL" in _dg_description(product, "ADR", {}, "nl")
