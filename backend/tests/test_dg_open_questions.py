"""The open questions of the DG step: what genuinely remains to be asked.

The step used to show every field as a question, and the ones the derivation
had already answered looked like work. `prepare_entries` now names the
remainder per product — facts of the consignment no table can supply — and the
interface renders exactly that list as questions. These tests pin the
boundary: derived and line-supplied values are never asked again, and each
question carries the reason it exists.
"""
from app.services.dg.autofill import open_questions_for, prepare_entries


def questions(product, profiles=("ADR",), lines=None, extra=None):
    entries = [{"line_id": 1, "products": [product]}]
    res = prepare_entries(entries, lines, list(profiles), "nl")
    blocks = res["open_questions"]
    return {q["field"]: q for block in blocks for q in block["questions"]}


def test_without_a_un_number_the_substance_itself_is_the_question():
    assert open_questions_for({"un_number": ""}, ["ADR"]) == []


def test_the_mode_of_carriage_is_always_a_land_question():
    q = questions({"un_number": "1203"})
    assert q["carriage_mode"]["required"] is True
    assert q["carriage_mode"]["reason"] == "carriage_mode_decides"


def test_an_answered_mode_is_not_asked_again():
    q = questions({"un_number": "1203", "carriage_mode": "tank"})
    assert "carriage_mode" not in q


def test_what_the_line_supplied_is_not_asked_again():
    """Count and packaging come over from the cargo line; only the net
    contents per package stays open for the 1.1.3.6 total."""
    q = questions(
        {"un_number": "1203"},
        lines=[{"line_id": 1, "quantity": 10, "unit": "vaten"}],
    )
    assert "quantity_packages" not in q
    assert q["net_mass_liters_per_package"]["reason"] == "totals_11136"


def test_sp_274_asks_the_technical_name_and_only_while_it_is_empty():
    q = questions({"un_number": "1993", "carriage_mode": "packages",
                   "adr_total_quantity": "100 L"})
    assert q["technical_name"]["required"] is True
    assert q["technical_name"]["reason"] == "sp274"
    q2 = questions({"un_number": "1993", "carriage_mode": "packages",
                    "adr_total_quantity": "100 L",
                    "technical_name": "tolueen"})
    assert "technical_name" not in q2
    # UN 1203 carries no SP 274; the question never appears there.
    assert "technical_name" not in questions({"un_number": "1203"})


def test_class_1_asks_the_net_explosive_mass():
    q = questions({"un_number": "0336", "carriage_mode": "packages"})
    assert q["net_explosive_mass"]["reason"] == "nem_class1"


def test_adn_dry_cargo_asks_where_on_board_a_tank_does_not():
    dry = questions({"un_number": "1203", "carriage_mode": "packages"},
                    profiles=("ADN",))
    assert dry["hold"]["reason"] == "hold_74111"
    tank = questions({"un_number": "1203", "carriage_mode": "tank"},
                     profiles=("ADN",))
    assert "hold" not in tank
    assert tank["density_15"]["reason"] == "filling_degree"


def test_sea_and_air_ask_what_their_documents_require():
    sea = questions({"un_number": "1203"}, profiles=("IMDG",))
    assert sea["quantity_packages"]["reason"] == "imdg_document"
    assert sea["type_of_package"]["required"] is True
    air = questions({"un_number": "1203"}, profiles=("IATA_DGR",))
    # The packing instruction itself is derived from the table and therefore
    # not asked; what the declaration still needs from the consignor is.
    assert "packing_instruction" not in air
    assert air["net_mass_liters_per_package"]["reason"] == "iata_declaration"


def test_a_prohibited_substance_raises_no_questions():
    assert open_questions_for(
        {"un_number": "0020", "transport_forbidden": True}, ["ADR"]) == []


def test_a_complete_packages_product_has_nothing_left_to_ask():
    q = questions({
        "un_number": "1203", "carriage_mode": "packages",
        "quantity_packages": "10", "net_mass_liters_per_package": "20 L",
        # UN 1203 combines BENZINE and MOTORBRANDSTOF; since v1.102.0 the
        # 3.1.2.2 choice is part of a complete product.
        "chosen_name": "BENZINE", "chosen_name_en": "PETROL",
    })
    assert q == {}


def test_a_bare_piece_count_is_not_a_packaging():
    """A line without a stated packaging carries the parser's fallback unit
    "pcs". Taking that over as the kind of package made the catalogue match
    it through "pc" to the code 6PC, and the searchable packaging field
    became a dropdown offering "6PC glass receptacle in wooden box" and
    nothing else. A piece count says nothing about the packaging, so it is
    not taken over and the field stays open to search."""
    q = questions(
        {"un_number": "1203"},
        lines=[{"line_id": 1, "quantity": 1, "unit": "pcs"}],
    )
    assert "type_of_package" not in q


def test_a_mass_or_volume_unit_never_becomes_the_kind_of_package():
    """"1000 kg petrol" counts mass. It used to end up on the document as
    the kind of package."""
    from app.services.dg.autofill import derive_from_line

    for unit in ("kg", "ton", "l", "m3", "m", "pcs"):
        patch = derive_from_line({}, {"line_id": 1, "quantity": 1000, "unit": unit})
        assert "type_of_package" not in patch, unit


def test_a_counted_packaging_still_comes_over_from_the_line():
    """The other half of the rule: units that do name a receptacle — and a
    word the table does not know, which is the consignor's own — are taken
    over as before."""
    from app.services.dg.autofill import derive_from_line

    for unit in ("jerrycan", "drum", "ibc", "pallet", "bag", "fust"):
        patch = derive_from_line({}, {"line_id": 1, "quantity": 10, "unit": unit})
        assert patch["type_of_package"] == unit


def test_the_jerrycan_choice_survives_the_rule():
    """The 5.4.1.1.1 (e) question is exactly what must keep working."""
    q = questions(
        {"un_number": "1203"},
        lines=[{"line_id": 1, "quantity": 1000, "unit": "jerrycan"}],
    )
    assert q["type_of_package"]["reason"] == "packaging_spec"
    assert [o.split()[0] for o in q["type_of_package"]["options"]] == [
        "3A1", "3A2", "3B1", "3B2", "3H1", "3H2"]
