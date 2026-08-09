"""The Dangerous Goods List as the source for columns 16a and 16b.

What the app uses for this is not optional: 7.2.3.1 lets column 16b prevail over
the segregation table of 7.2.4. As long as that column came from the UN cards it
was incomplete — the cards are 41-22 and cover nowhere near every substance.
These tests record that the list itself is now the source, and that the reading
of its columns is right for entries whose content is independently known.
"""

from app.services.dg import dangerous_goods_list as dgl
from app.services.dg.enrichment import (
    imdg_segregation_codes_for,
    segregation_groups_for,
)
from app.services.dg.database import offline_lookup


def test_the_list_is_present_and_carries_the_amendment_it_claims():
    assert dgl.available()
    source = dgl.source()
    assert source["amendment"] == "42-24"
    assert source["entries"] > 2800
    assert "MSC.556(108)" in source["source"]


def test_a_dash_is_layout_and_not_a_value():
    """The publication puts an en dash where nothing applies. Passing that on as
    a value would put '–' on a transport document as a subsidiary risk."""
    row = dgl.entry_for("1203")
    assert row["subsidiary_hazards"] == "–"
    assert dgl.value(row, "subsidiary_hazards") == ""


def test_the_stowage_column_splits_into_a_category_and_its_codes():
    """Kolom 16a draagt allebei: 'Category B SW2 SW5'."""
    row = dgl.entry_for("1891")
    assert dgl.stowage_category(row) == "B"
    assert dgl.stowage_codes(row) == ["SW2", "SW5"]


def test_a_class_1_entry_carries_a_numbered_stowage_category():
    row = dgl.entry_for("0004")
    assert dgl.stowage_category(row) == "04"


def test_the_segregation_column_splits_into_groups_and_codes():
    """Column 16b puts the segregation groups before the SG codes: 'SGG2 SG27 SG31'."""
    row = dgl.entry_for("0004")
    assert dgl.segregation_groups(row) == ["SGG2"]
    assert dgl.segregation_codes(row) == ["SG27", "SG31"]


def test_the_two_packing_groups_of_one_substance_stay_apart():
    rows = dgl.entries_for("3424")
    assert [r["packing_group"] for r in rows] == ["II", "III"]
    assert dgl.entry_for("3424", "III")["packing_group"] == "III"


def test_an_unknown_packing_group_still_yields_the_right_substance():
    """Better a row of the right substance than no row: the columns the app uses
    rarely differ between packing groups."""
    row = dgl.entry_for("3424", "I")
    assert row["proper_shipping_name"].startswith("AMMONIUM DINITRO")


def test_a_substance_the_list_does_not_know_yields_nothing():
    assert dgl.entry_for("9999") == {}
    assert dgl.entries_for("9999") == []


def test_the_change_marker_is_carried_through_as_a_fact():
    """UN 3423 was touched by 42-24 and therefore carries the triangle."""
    assert dgl.amended_in_42_24(dgl.entry_for("3423"))
    assert not dgl.amended_in_42_24(dgl.entry_for("1203"))


def test_special_provisions_come_out_as_separate_numbers():
    assert dgl.special_provisions(dgl.entry_for("3423")) == ["279", "409"]


# --- Wat de app ermee doet ----------------------------------------------------

def test_column_16b_now_comes_from_the_list_itself():
    assert imdg_segregation_codes_for("2984") == ["SG16", "SG59", "SG72"]


def test_the_segregation_groups_of_both_sources_are_taken_together():
    """3.1.4.4 and column 16b say the same thing; where one knows a group the
    other misses, that one counts."""
    groups = segregation_groups_for("3423")
    assert "SGG2" in groups and "SGG18" in groups


def test_the_enrichment_hands_the_official_codes_to_the_interface():
    entry = offline_lookup("2984")
    assert entry["imdg_segregation_codes"] == ["SG16", "SG59", "SG72"]
    assert entry["imdg_stowage_category"] == "B"
    assert entry["imdg_amendment"] == "42-24"
    assert "MSC.556(108)" in entry["imdg_dgl_source"]


def test_every_code_the_enrichment_reports_has_a_description():
    """The code table of 7.1.5/7.1.6/7.2.8 and the list have to line up; a code
    without text is worth nothing to a user."""
    entry = offline_lookup("2984")
    described = {item["code"] for item in entry["imdg_segregation_definitions"]}
    assert described == set(entry["imdg_segregation_codes"])


def test_the_list_supplies_the_columns_the_cards_never_had():
    entry = offline_lookup("3423")
    assert entry["imdg_special_provisions"] == ["279", "409"]
    assert entry["imdg_packing_instructions"] == "P002"
    assert entry["imdg_tank_instructions"] == "T6"
    assert entry["imdg_amended_in_42_24"] is True
    assert "ammonia" in entry["imdg_properties"].lower()
