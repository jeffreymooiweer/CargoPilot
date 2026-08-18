"""ADN 7.1.4.2, 7.1.4.4/7.1.4.5 and 7.1.4.10: the water's own prohibitions.

Read in the ADN 2025 English edition (printed pages 394-399, quoted by
scripts/read_land_regulations.py --doc adn) and in section 7.1.4 of the
official Dutch edition, which agree on every provision cited here.

Until v1.119.0 an inland-only consignment was measured against ADR 7.5.2 — a
road chapter the ADN does not prescribe — and its foodstuffs answer cited
CV28, a code name the ADN does not have. The ADN gates that precaution with
special provision 802 in column (6) of its own table A, and its separation
measures are its own: full-height partitions, unmarked packages in between,
or 0.8 m.
"""

from app.services.dg.compliance import check_adn_mixed_loading, check_compliance


def line(line_id, **product):
    return {"line_id": line_id, "products": [product]}


ANILINE = {"un_number": "1547", "proper_shipping_name": "ANILINE",
           "class": "6.1", "packing_group": "II"}
GASOLINE = {"un_number": "1203", "proper_shipping_name": "GASOLINE",
            "class": "3", "packing_group": "II"}
FERTILIZER = {"un_number": "2067", "proper_shipping_name":
              "AMMONIUM NITRATE BASED FERTILIZER", "class": "5.1",
              "packing_group": "III", "carriage_mode": "bulk"}


# --- 7.1.4.10: the foodstuffs precaution hangs on special provision 802 ----


def test_special_provision_802_raises_the_foodstuffs_precaution():
    findings = check_adn_mixed_loading([line("L1", **ANILINE)])
    rules = [f["rule"] for f in findings]
    assert "ADN 7.1.4.10 (802)" in rules
    finding = next(f for f in findings if f["rule"] == "ADN 7.1.4.10 (802)")
    assert "0,8 m" in finding["message"] or "0.8 m" in finding["message"]


def test_a_substance_without_802_raises_nothing():
    """Petrol's column (6) carries 243 and 534, not 802 — the road's CV28
    never applied to it either, but the gate is now the ADN's own column."""
    assert check_adn_mixed_loading([line("L1", **GASOLINE)]) == []


# --- 7.1.4.2: Class 5.1 in bulk excludes everything else -------------------


def test_bulk_51_beside_other_goods_is_an_error():
    findings = check_adn_mixed_loading([
        line("L1", **FERTILIZER), line("L2", **GASOLINE)])
    finding = next(f for f in findings if f["rule"] == "ADN 7.1.4.2")
    assert finding["severity"] == "error"
    assert "1203" in finding["products"] and "2067" in finding["products"]


def test_bulk_51_alone_is_a_condition_on_the_vessel():
    """The consignment itself is fine; what else is on board this application
    cannot see, so the prohibition is handed over rather than granted."""
    findings = check_adn_mixed_loading([line("L1", **FERTILIZER)])
    finding = next(f for f in findings if f["rule"] == "ADN 7.1.4.2")
    assert finding["severity"] == "warning"


def test_packaged_51_is_not_caught_by_the_bulk_prohibition():
    packaged = dict(FERTILIZER, carriage_mode="packages")
    findings = check_adn_mixed_loading([
        line("L1", **packaged), line("L2", **GASOLINE)])
    assert all(f["rule"] != "ADN 7.1.4.2" for f in findings)


# --- 7.1.4.4/7.1.4.5: the container exceptions, on the consignor's word ----


def test_declared_in_containers_names_the_exceptions():
    findings = check_adn_mixed_loading([
        line("L1", **dict(ANILINE, containers_only="yes")),
        line("L2", **dict(GASOLINE, containers_only="yes"))])
    finding = next(
        f for f in findings if f["rule"] == "ADN 7.1.4.4 / 7.1.4.5")
    assert finding["severity"] == "info"
    assert "2,40 m" in finding["message"] or "2.40 m" in finding["message"]


def test_a_partial_declaration_does_not_name_them():
    """One line in containers and one loose: 7.1.4.3 still governs the loose
    one, so the exception note would reassure about the wrong package."""
    findings = check_adn_mixed_loading([
        line("L1", **dict(ANILINE, containers_only="yes")),
        line("L2", **GASOLINE)])
    assert all(f["rule"] != "ADN 7.1.4.4 / 7.1.4.5" for f in findings)


# --- The wiring: which regime answers which selection ----------------------


def test_inland_only_is_no_longer_measured_against_the_road_table():
    out = check_compliance([
        line("L1", **ANILINE), line("L2", **GASOLINE)], ["ADN"], "en")
    rules = [f["rule"] for f in out["adr_mixed_loading"]]
    assert all(not r.startswith("ADR") for r in rules)
    assert "ADN 7.1.4.10 (802)" in rules
    assert "adr_mixed_loading_basis_note" not in out


def test_a_combined_selection_gets_both_answers():
    out = check_compliance([
        line("L1", **ANILINE), line("L2", **GASOLINE)], ["ADR", "ADN"], "en")
    rules = [f["rule"] for f in out["adr_mixed_loading"]]
    assert any(r.startswith("ADR") for r in rules)
    assert "ADN 7.1.4.10 (802)" in rules
    assert "7.1.4" in out["adr_mixed_loading_basis_note"]


def test_rail_with_inland_uses_the_rail_table_not_the_road_one():
    """RID+ADN used to hand the road table to both legs; the rail leg is
    evaluated against RID's own table and cited to it."""
    explosive = {"un_number": "0331", "proper_shipping_name": "EXPLOSIVE",
                 "class": "1", "classification_code": "1.5D"}
    out = check_compliance([
        line("L1", **explosive), line("L2", **GASOLINE)], ["RID", "ADN"], "en")
    rules = [f["rule"] for f in out["adr_mixed_loading"]]
    assert any(r.startswith("RID 7.5.2.1") for r in rules)
    assert all(not r.startswith("ADR 7.5.2") for r in rules)


def test_every_language_has_the_texts():
    for language in ("nl", "en", "de", "fr"):
        findings = check_adn_mixed_loading(
            [line("L1", **FERTILIZER), line("L2", **ANILINE)], language)
        assert len(findings) >= 2
        assert all(f["message"] for f in findings)
