"""Chapter 5.2: what the person packing the drum has to put on it.

Every number asserted here was read out of an official edition on a runner
before the code was written, and the assertion names the provision it came
from. A test that pins a value nobody measured pins a guess.
"""
import json
from pathlib import Path

import pytest

from app.services.dg.package_marking import (
    _imdg_label_models,
    _label_models,
    check_package_marking,
    rules,
)

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg" / "package_marking.json"


def product(un, **extra):
    from app.services.dg import database
    rows = database.get_un_entries(un)
    row = rows[0] if rows else {}
    item = {
        "un_number": un,
        "proper_shipping_name": row.get("name_nl") or "",
        "class": row.get("class") or "",
        "labels": row.get("labels") or "",
        "packing_group": row.get("packing_group") or "",
        "subsidiary_risks": row.get("subsidiary_risks") or "",
    }
    item.update(extra)
    return item


def answer(*products, profiles=("ADR",)):
    return check_package_marking(
        [{"line_id": "1", "products": list(products)}], list(profiles), "nl")


def regime(result, profile):
    return next(block for block in result["regimes"] if block["profile"] == profile)


def marks(result, profile, un):
    item = next(row for row in regime(result, profile)["items"]
                if row["un_number"] == un)
    return {mark["kind"]: mark for mark in item["marks"]}


def labels(result, profile, un):
    item = next(row for row in regime(result, profile)["items"]
                if row["un_number"] == un)
    return item["labels"]


def column_6(result, profile, un):
    item = next(row for row in regime(result, profile)["items"]
                if row["un_number"] == un)
    return {entry["provision"]: entry for entry in item["column_6"]}


# --- the measured values, pinned where a future edition would break them ---


def test_the_seed_carries_the_values_that_were_measured():
    """ADR 2025 Volume II, pages 245-252. Each of these was quoted verbatim."""
    data = json.loads(SEED.read_text(encoding="utf-8"))

    # 5.2.1.1 — three tiers, and the smallest gives no figure at all. That the
    # third is null is a fact about the provision, not a hole in the file.
    heights = data["marks"]["un_number"]["character_height_mm"]
    assert [tier["min_mm"] for tier in heights] == [12, 6, None]

    # 5.2.2.2.1.1.2
    shape = data["labels"]["shape"]
    assert shape["size"] == {"min_width_mm": 100, "min_height_mm": 100}
    assert shape["inner_line_mm"] == 5

    # 5.2.1.9.2 — the only mark with a hard floor rather than "clearly visible".
    battery = data["marks"]["battery"]
    assert battery["reduction"]["floor_width_mm"] == 100
    assert battery["reduction"]["floor_height_mm"] == 70
    assert battery["hatching"] == {"min_mm": 5, "colour": "red"}

    # 5.2.1.8.1 — the exemption is per inner or single packaging, and it is the
    # reason the mark can never be settled from the substance alone.
    exemptions = data["marks"]["environmentally_hazardous"]["exempt_when"]
    assert any("5 l or less" in text for text in exemptions)
    assert any("5 kg or less" in text for text in exemptions)


def test_the_100_mm_is_the_side_and_not_the_bounding_box():
    """The provision leaves two readings; they differ by the square root of two.

    ADR 5.2.2.2.1.1.2 says only that a label is a square set at 45 degrees whose
    minimum dimensions are 100 mm x 100 mm. Measuring the official figure did
    not settle which distance that is — the drawing puts the "5 mm" inner line
    0.51 pt from an outline whose side is 96.89 pt, which is the stroke width
    and not the border. What settles it is the same label written out in full
    in 49 CFR 172.407(c)(1): the identical shape, the identical 100 mm, the
    identical 5 mm border measured from the outside edge, and the words "on
    each side".

    This is pinned because everything printable rests on it. A label built to
    the other reading is 71 mm on a side where the regulation asks for 100, on
    every package, while looking entirely correct.
    """
    which = json.loads(SEED.read_text(encoding="utf-8"))["labels"]["shape"]["_which_distance"]
    assert which["answer"] == "side"
    assert which["side_mm"] == 100
    assert round(which["point_to_point_mm"]) == 141
    assert any("172.407" in source for source in which["sources"])


def test_the_three_reduction_rules_stay_three_rules():
    """Each mark reduces on its own terms; one slider for all three is wrong.

    The class label reduces *proportionally* with no floor (5.2.2.2.1.1.3), the
    battery mark has a floor of 100 x 70 mm (5.2.1.9.2), and the
    environmentally hazardous mark reduces only so far as it stays clearly
    visible, with no figure at all (5.2.1.8.3).
    """
    data = json.loads(SEED.read_text(encoding="utf-8"))
    assert data["labels"]["shape"]["reduction"]["floor_mm"] is None
    assert data["marks"]["battery"]["reduction"]["floor_height_mm"] == 70
    assert data["marks"]["environmentally_hazardous"]["reduction"]["floor_mm"] is None


# --- the land regimes ---


def test_the_un_number_is_offered_at_the_height_that_is_always_enough():
    """5.2.1.1: 12 mm unless the package is small, and the package is unknown."""
    mark = marks(answer(product("1263")), "ADR", "1263")["un_number"]
    assert mark["text"] == "UN 1263"
    assert mark["height_mm"] == 12
    assert mark["provision"] == "5.2.1.1"


def test_only_class_1_and_class_7_carry_the_name_on_land():
    """5.2.1.5 and 5.2.1.7.2 name two classes. Paint is neither."""
    assert "proper_shipping_name" in marks(answer(product("0004")), "ADR", "0004")
    assert "proper_shipping_name" not in marks(answer(product("1263")), "ADR", "1263")


def test_the_class_1_name_carries_its_language_rule():
    """5.2.1.5 asks for French, German or English; no other mark says that."""
    mark = marks(answer(product("0004")), "ADR", "0004")["proper_shipping_name"]
    assert mark["language_rule"] is True
    assert mark["provision"] == "5.2.1.5"


def test_the_battery_mark_needs_both_the_number_and_the_provision():
    """5.2.1.9.1 marks cells "prepared in accordance with" SP 188 or 400."""
    assert "battery" in marks(answer(product("3480")), "ADR", "3480")
    # A class 9 entry that is not a battery entry gets no battery mark.
    assert "battery" not in marks(answer(product("1263")), "ADR", "1263")


def test_a_salvage_packaging_says_so():
    """5.2.1.3, and the 12 mm lettering that goes with it."""
    mark = marks(answer(product("1263", salvage_packaging="yes")), "ADR", "1263")
    assert mark["salvage"]["text"] == "SALVAGE"
    assert mark["salvage"]["height_mm"] == 12


def test_the_environmental_mark_admits_it_could_not_settle_the_threshold():
    """The substance decides whether the mark applies; the packing decides
    whether it falls away, and the packing is not something this can see."""
    result = answer(product("1263", environmentally_hazardous=True))
    mark = marks(result, "ADR", "1263")["environmentally_hazardous"]
    assert mark["certain"] is False
    assert "environmentally_hazardous_threshold" in result["open"]


# --- the sea regime, which is not the land one renumbered ---


def test_every_package_carries_the_name_at_sea():
    """IMDG 5.2.1.1 — the difference that reaches every single package.

    On land the name goes on Class 1 and Class 7 only. Borrowing the road
    answer for a sea leg would leave the name off every other package.
    """
    result = answer(product("1263"), product("1830"), profiles=("IMDG",))
    for un in ("1263", "1830"):
        mark = marks(result, "IMDG", un)["proper_shipping_name"]
        assert mark["provision"] == "5.2.1.1"


def test_the_sea_label_comes_from_the_code_and_not_from_table_a():
    """UN 0004 is "1" in Table A and "1.1D" in the Dangerous Goods List.

    IMDG 5.2.2.1.2 takes the primary label from column 3 of the List. Reading
    the product's own class — which the wizard filled in from Table A — would
    print the class where the Code asks for the division and compatibility
    group.
    """
    both = answer(product("0004"), profiles=("ADR", "IMDG"))
    assert [row["model"] for row in labels(both, "ADR", "0004")] == ["1"]
    assert [row["model"] for row in labels(both, "IMDG", "0004")] == ["1.1D"]


def test_the_battery_label_at_sea_is_no_longer_open():
    """v1.160.0 left this open because column 3 says plain "9". Reading settled
    it, so the answer must stop hedging: leaving the flag up after the question
    is answered is its own kind of wrong."""
    result = answer(product("3480"), profiles=("IMDG",))
    assert "imdg_battery_label_9_or_9a" not in result["open"]


def test_column_6_is_read_and_the_flag_is_gone():
    """It was the last thing chapter 5.2 said it had not done. Leaving the flag
    up once the reading is finished is the same fault as leaving it down before
    — it is just the flattering direction."""
    result = answer(product("1263"), profiles=("IMDG",))
    assert "imdg_column_6_not_read" not in result["open"]


def test_the_battery_label_comes_from_the_provision_that_assigns_it():
    """Special provision 384 says the label is model No. 9A and that only the
    placard on the unit is model No. 9. v1.161.1 reached 9A by inference from
    three other provisions; this reads it from the column that assigns it."""
    result = answer(product("3480"), profiles=("IMDG",))
    rows = labels(result, "IMDG", "3480")
    assert rows[0]["model"] == "9A"
    assert "384" in rows[0]["source"]
    effects = column_6(result, "IMDG", "3480")
    assert effects["384"]["effect"] == "model"
    assert effects["384"]["unit_model"] == "9"


def test_a_conditional_provision_is_named_and_not_applied():
    """UN 0143 cites special provision 271: no "TOXIC" subsidiary label if the
    mixture holds at least 90% phlegmatizer. That is a property of the mixture,
    not of the entry, so the label stays and the provision is named beside it.
    Removing a label on a condition nobody checked is the failure this whole
    module is arranged against."""
    result = answer(product("0143"), profiles=("IMDG",))
    effects = column_6(result, "IMDG", "0143")
    assert effects["271"]["effect"] == "removes"
    assert effects["271"]["certain"] is False
    assert effects["271"]["condition"]


def test_the_sea_reads_the_sea_s_column_six():
    """Both books have a column 6 and they are different sets of numbers. UN
    3480 carries 384 in the Code and does not in Table A; reading the wrong
    book here would leave no trace, because the numbers look plausible either
    way."""
    from app.services.dg import package_marking as module

    assert "384" in module._imdg_special_provisions("3480", "")
    assert "384" not in module._adr_special_provisions("3480")


def test_every_provision_that_mentions_a_label_was_judged():
    """Forty-two of the 262 numbers column 6 cites mention a label, a mark or an
    exemption. Each is either an effect or explicitly recorded as bearing on
    something else. A number in neither list is one nobody looked at."""
    from app.services.dg.package_marking import rules

    block = rules()["column_6"]
    judged = set(block["effects"]) | set(block["read_no_effect"])
    assert judged == set(block["source"]["mention_a_label_or_mark"])
    assert block["source"]["found_in_chapter"] == block["source"]["cited_by_column_6"]


def test_the_two_durability_rules_are_kept_apart():
    """ADR 5.2.1.2 asks a mark to survive the weather; IMDG 5.2.1.2 asks it to
    survive three months in the sea. That difference is what stops a sheet of
    office stickers being presented as sufficient for a sea consignment."""
    result = answer(product("1263"), profiles=("ADR", "IMDG"))
    assert "open weather" in result["durability"]["land"]
    assert "three months" in result["durability"]["sea"]


def test_division_1_4_s_is_marked_at_sea():
    """IMDG 5.2.1.1 asks for the division and compatibility group unless the
    1.4S label is displayed. No land regime asks for it."""
    result = answer(product("0012", **{"class": "1.4S"}), profiles=("IMDG",))
    kinds = marks(result, "IMDG", "0012")
    assert "division_and_compatibility_group" in kinds
    assert kinds["division_and_compatibility_group"]["unless"] == "label_1_4s_displayed"


# --- what it refuses to answer ---


def test_the_orientation_arrows_are_never_derived():
    """5.2.1.10 turns on the kind of packaging — combination with liquid inners,
    single with vents, cryogenic, machinery under SP 301 — none of which this
    application can see. Saying "no arrows" would be a claim; this is not."""
    result = answer(product("1263"))
    assert "orientation_arrows" in result["not_assessed"]


@pytest.mark.parametrize("profiles", [("IATA_DGR",), ()])
def test_a_regime_that_was_not_read_gets_no_answer(profiles):
    """The IATA marking rules have not been read, so air gets nothing rather
    than the land answer wearing an aeroplane."""
    assert answer(product("1263"), profiles=profiles)["status"] == "not_checked"


def test_a_consignment_without_dangerous_goods_is_answered_not_asked():
    assert check_package_marking([], ["ADR"], "nl")["status"] == "not_checked"


# --- the parsing, where a space would have moved the primary hazard ---


def test_a_leading_separator_does_not_demote_the_primary_label():
    """Counting split tokens rather than kept models loses the primary hazard.

    The separator has to be one ``strip()`` does not remove. A leading *space*
    proves nothing here — the value is stripped before it is split, so the
    empty first element never appears and the token index is still right. A
    leading comma survives that strip, splits to an empty first element, and
    made column (5) report two subsidiary hazards and no primary one.
    """
    assert [(row["model"], row["role"]) for row in _label_models({"labels": ", 3, 6.1"})] == [
        ("3", "primary"), ("6.1", "subsidiary")]
    assert [(row["model"], row["role"]) for row in _label_models({"labels": "3, 6.1"})] == [
        ("3", "primary"), ("6.1", "subsidiary")]


def test_the_model_letter_survives_on_land():
    """9A is a different piece of artwork from 9; ``_label_numbers`` drops the
    letter because 8.1.5.1 wants the bare number, and this must not."""
    assert _label_models({"labels": "9A"})[0]["model"] == "9A"


def test_an_entry_the_code_does_not_carry_says_which_book_answered():
    models = _imdg_label_models({"un_number": "9999", "class": "3"})
    assert models[0]["model"] == "3"
    assert "Table A" in models[0]["source"]


def test_the_source_of_every_regime_names_its_edition():
    result = answer(product("1263"), profiles=("ADR", "RID", "ADN", "IMDG"))
    editions = {block["profile"]: block["source"] for block in result["regimes"]}
    assert "ADR 2025" in editions["ADR"]
    assert "RID 2025" in editions["RID"]
    assert "ADN 2025" in editions["ADN"]
    assert "42-24" in editions["IMDG"]


def test_the_rules_are_read_once():
    assert rules() is rules()


# --- what a read run settled after v1.160.0 shipped with it open ---


def test_the_marine_pollutant_relief_never_reaches_un_3077_and_3082():
    """IMDG 2.10.2.7 relieves the mark at 5 l or 5 kg per inner packaging — the
    same figures the land regulations use — but says in as many words that it
    does not apply to UN 3077 or UN 3082. Those two are the generic
    environmentally hazardous entries, which is to say exactly the ones a reader
    would expect the relief to cover. So for them the answer is certain."""
    for un in ("3077", "3082"):
        mark = marks(answer(product(un, marine_pollutant="P"), profiles=("IMDG",)),
                     "IMDG", un)["marine_pollutant"]
        assert mark["certain"] is True
        assert "2.10.2.7" in mark["no_exemption"]


def test_any_other_pollutant_keeps_the_threshold_named_and_unapplied():
    """The relief turns on the quantity per inner or single packaging, which is
    a property of the packing and not of the goods."""
    result = answer(product("1263", marine_pollutant="P"), profiles=("IMDG",))
    mark = marks(result, "IMDG", "1263")["marine_pollutant"]
    assert mark["certain"] is False
    assert mark["exemption_provision"] == "2.10.2.7"
    assert "marine_pollutant_threshold" in result["open"]


def test_the_sea_package_label_for_batteries_is_9a_and_not_9():
    """Column 3 of the Dangerous Goods List gives the class, not the model, so
    it says plain 9. Three provisions choose 9A for the package: 5.2.2.2.1.3
    gives it a layout of its own, special provision 188 names it, and 5.3.1.1.2
    forbids 9A *for placarding purposes* — a prohibition that means nothing
    unless 9A is a package label."""
    result = answer(product("3480"), profiles=("ADR", "IMDG"))
    assert [row["model"] for row in labels(result, "IMDG", "3480")] == ["9A"]
    assert [row["model"] for row in labels(result, "ADR", "3480")] == ["9A"]


def test_a_class_9_entry_that_is_not_a_battery_keeps_model_9():
    """The refinement must not sweep in every class 9 entry."""
    result = answer(product("3077", marine_pollutant="P"), profiles=("IMDG",))
    assert [row["model"] for row in labels(result, "IMDG", "3077")] == ["9"]


def test_the_seed_records_why_9a_belongs_on_the_package():
    """Pinned because the reasoning is the answer: no single provision says it,
    and a future reader who cannot see the three together would undo it."""
    data = json.loads(SEED.read_text(encoding="utf-8"))["imdg"]["class_9_label_model"]
    assert data["answer"].startswith("9A on the package")
    assert set(data["provisions"]) == {"5.2.2.2.1.3", "special provision 188", "5.3.1.1.2"}


# --- the limited quantities mark of chapter 3.4 ---


def lq_product(**extra):
    product = {
        "un_number": "1263", "proper_shipping_name": "VERF", "class": "3",
        "labels": "3", "packing_group": "II", "limited_quantity": "5 L",
        "net_per_inner_packaging": "1 L", "gross_mass_per_package": "10 kg",
    }
    product.update(extra)
    return product


def kinds(result, profile, un="1263"):
    item = next(row for row in regime(result, profile)["items"]
                if row["un_number"] == un)
    return [mark["kind"] for mark in item["marks"]]


def test_a_line_within_the_limits_of_three_four_carries_the_diamond():
    result = check_package_marking(
        [{"line_id": "1", "products": [lq_product()]}], ["ADR"], "nl")
    assert "limited_quantities" in kinds(result, "ADR")


def test_a_line_over_the_inner_packaging_limit_does_not():
    """Column 7a gives 5 L; a 6 L inner packaging is outside chapter 3.4, and
    a mark on that package would be a claim the goods do not support."""
    result = check_package_marking(
        [{"line_id": "1", "products": [lq_product(net_per_inner_packaging="6 L")]}],
        ["ADR"], "nl")
    assert "limited_quantities" not in kinds(result, "ADR")


def test_a_line_whose_column_7a_forbids_it_does_not():
    """'0' in column 7a means carriage as a limited quantity is not permitted."""
    result = check_package_marking(
        [{"line_id": "1", "products": [lq_product(limited_quantity="0")]}],
        ["ADR"], "nl")
    assert "limited_quantities" not in kinds(result, "ADR")


def test_the_same_function_decides_this_as_decides_the_lq_check():
    """Two readings of one question drift apart, and here that would mean a
    package that carries the mark on one screen and not on the other. The
    marking check calls ``_assess_lq`` rather than testing the limits again."""
    import inspect

    from app.services.dg import package_marking

    source = inspect.getsource(package_marking._limited_quantities_mark)
    assert "_assess_lq" in source


def test_the_sea_does_not_borrow_the_land_s_chapter_three_four():
    """The Code has a chapter 3.4 of its own, with its own numbering, and it
    has not been read. Answering the sea out of ADR 3.4.7 is the mistake
    column 6 already made once; the open point says so instead."""
    result = check_package_marking(
        [{"line_id": "1", "products": [lq_product()]}], ["IMDG"], "nl")
    assert "limited_quantities" not in kinds(result, "IMDG")
    assert "imdg_chapter_3_4_not_read" in result["open"]


def test_the_mark_carries_the_size_and_the_reduction_the_provision_gives():
    result = check_package_marking(
        [{"line_id": "1", "products": [lq_product()]}], ["ADR"], "nl")
    item = next(row for row in regime(result, "ADR")["items"])
    mark = next(m for m in item["marks"] if m["kind"] == "limited_quantities")
    assert mark["provision"] == "3.4.7"
    assert mark["size"]["min_width_mm"] == 100
    assert mark["size"]["min_line_width_mm"] == 2
    assert mark["reduction"]["floor_width_mm"] == 50
    assert mark["air_variant"]["symbol"] == "Y"
    assert mark["air_variant"]["optional"] is True
