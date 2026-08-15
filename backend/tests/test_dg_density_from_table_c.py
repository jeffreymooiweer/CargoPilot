"""The tank density, pulled from where it is already known.

The consignor was being asked for the relative density of petrol at 15 °C as
if everyone knows it, while table C of the read ADN edition prints a density
for 329 of its 678 rows. These tests pin the boundary: one clean printed
number fills d15 (visible and editable), a printed range or bound is shown as
the book gives it and never averaged into an answer, and a user's own value is
never overwritten.
"""
from app.services.dg.autofill import prepare_entries, table_c_density


def prepare(product, profiles=("ADN",)):
    return prepare_entries(
        [{"line_id": 1, "products": [product]}], None, list(profiles), "nl")


def density_notes(res):
    return [h["density_note"] for h in res["hints"] if h.get("density_note")]


def test_a_single_printed_value_fills_d15():
    res = prepare({"un_number": "1090", "carriage_mode": "tank"})
    assert res["entries"][0]["products"][0]["density_15"] == "0.79"
    (note,) = density_notes(res)
    assert "tabel C" in note and "0.79" in note


def test_a_printed_range_is_shown_and_never_averaged():
    res = prepare({"un_number": "1203", "carriage_mode": "tank"}, ("ADR",))
    product = res["entries"][0]["products"][0]
    assert not str(product.get("density_15") or "")
    (note,) = density_notes(res)
    assert "0,68 - 0,72" in note


def test_the_note_points_to_the_safety_data_sheet():
    (note,) = density_notes(prepare({"un_number": "1090", "carriage_mode": "tank"}))
    assert "veiligheidsinformatieblad" in note


def test_the_user_s_own_value_stands():
    res = prepare({"un_number": "1090", "carriage_mode": "tank",
                   "density_15": "0.81"})
    assert res["entries"][0]["products"][0]["density_15"] == "0.81"


def test_packages_raise_no_density_at_all():
    res = prepare({"un_number": "1090", "carriage_mode": "packages"})
    assert not str(res["entries"][0]["products"][0].get("density_15") or "")
    assert density_notes(res) == []


def test_a_substance_without_a_printed_density_stays_a_question():
    assert table_c_density("0336") is None


def test_footnote_markers_are_stripped_from_what_is_shown():
    """UN 1203's cell ends in a footnote reference ("10)"); the note carries
    the density, not the typography around it."""
    printed = table_c_density("1203")["printed"]
    assert printed == ["0,68 - 0,72"]
