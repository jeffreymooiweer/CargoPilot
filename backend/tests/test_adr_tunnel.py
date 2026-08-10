"""ADR 8.6.3: the tunnel restriction code, evaluated instead of only printed.

The code from column (15) has been on the transport document for a long time,
and correctly — 5.4.1.1.1 (k) asks for it there. What was missing is everything
after the printing. A consignor who reads "(D/E)" on a CMR may reasonably assume
somebody worked out what it means for this load. Nobody had.

Two provisions make that more than picking the strictest entry off a list, and
both are why this file exists rather than a one-line helper:

**8.6.3.2** assigns the most restrictive code to the *whole load*. A load is not
a set of separately restricted substances; it is one unit with one code, and the
driver needs that one. The order of restrictiveness is nowhere written out in
words — it is the order of the table in 8.6.4, and reading it out of that table
is the only defensible way to have it.

**8.6.3.3** is the one that changes an answer rather than adding one. Goods
carried under 1.1.3 are not subject to tunnel restrictions *and must not be
counted* when determining the load's code. For a consignment that stays within
the 1.1.3.6 exemption there is therefore no code to assign at all — the printed
"(D/E)" is not merely unevaluated, it does not apply. The single exception the
article names is the transport unit that has to carry the marking of 3.4.13
subject to 3.4.14, and that unit is barred from category E tunnels however
harmless its goods' own codes look.

The two split codes, B1000C and C5000D, turn on the total net explosive mass per
transport unit rather than on the mass of the line that carries them. The ADR's
own example is pinned below.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.dg.compliance import check_adr_tunnel, check_compliance

CONFIG = Path(__file__).resolve().parents[1] / "app" / "config" / "dg_compliance.json"


def entries(*products: dict) -> list[dict]:
    return [{"vehicle": "TRAILER-1", "line_id": "1", "products": list(products)}]


def product(**overrides) -> dict:
    base = {
        "un_number": "1203",
        "class": "3",
        "packing_group": "II",
        "transport_category": "2",
        "tunnel_code": "D/E",
        "adr_total_quantity": "400",
    }
    base.update(overrides)
    return base


# --- The table itself ------------------------------------------------------


def test_the_table_of_8_6_4_holds_every_code_table_a_uses():
    """A code Table A gives that the table here does not know leaves the load
    without an answer, and the check says so rather than guessing. This is the
    guard that keeps that from happening for an ordinary substance."""
    table = json.loads(CONFIG.read_text(encoding="utf-8"))["adr_tunnel"]["codes"]
    seed = json.loads(
        (Path(__file__).resolve().parents[1] / "seed" / "dg" / "un_numbers.json")
        .read_text(encoding="utf-8")
    )
    used = {str(entry.get("tunnel_code") or "").strip().upper()
            for entry in seed}
    used.discard("")
    assert used <= set(table), sorted(used - set(table))


def test_the_order_runs_from_the_most_to_the_least_restrictive():
    """8.6.3.2 says "most restrictive" and never says which that is. The table of
    8.6.4 is printed in that order, and the number of tunnel categories a code
    bars is the check on having copied it the right way round.

    Measured on the strictest branch of each row — carriage in tanks, and above
    the mass threshold for the two codes that split on it. That is the branch
    the table is ordered by: on the packages branch B/E bars only category E and
    still stands above C, which bars three.
    """
    rules = json.loads(CONFIG.read_text(encoding="utf-8"))["adr_tunnel"]
    barred = [len(rules["codes"][code].get("above") or rules["codes"][code]["tanks"])
              for code in rules["order"]]
    assert barred == sorted(barred, reverse=True), list(zip(rules["order"], barred))


@pytest.mark.parametrize("code,expected", [
    ("B", ["B", "C", "D", "E"]),
    ("B/D", ["D", "E"]),
    ("B/E", ["E"]),
    ("C", ["C", "D", "E"]),
    ("C/D", ["D", "E"]),
    ("C/E", ["E"]),
    ("D", ["D", "E"]),
    ("D/E", ["E"]),
    ("E", ["E"]),
    ("-", []),
])
def test_each_code_bars_the_categories_the_table_gives_it(code, expected):
    """Read off the table in 8.6.4 of the Dutch ADR 2025, for carriage in
    packages — the only kind this application knows about. "Other carriage" is
    the second half of each split row; the first half is for tanks and bulk."""
    result = check_adr_tunnel(entries(product(tunnel_code=code)), "nl",
                              points_status="above_threshold")
    assert result["code"] == code
    assert result["restricted_categories"] == expected


# --- 8.6.3.2: one code for the whole load ---------------------------------


def test_the_strictest_code_of_the_load_wins():
    """Two substances, two codes, one load. The driver has one route to choose
    and needs the code that governs it, not two codes to reconcile."""
    result = check_adr_tunnel(
        entries(product(tunnel_code="D/E"), product(un_number="1017", tunnel_code="C/D")),
        "nl", points_status="above_threshold",
    )
    assert result["code"] == "C/D"
    assert result["restricted_categories"] == ["D", "E"]
    assert "8.6.3.2" in result["message"]


def test_a_load_where_no_substance_is_restricted_says_so_rather_than_nothing():
    """"(-)" is an answer — passage through every tunnel — and leaving the
    section empty would read as "not checked"."""
    result = check_adr_tunnel(entries(product(tunnel_code="(-)")), "nl",
                              points_status="above_threshold")
    assert result["status"] == "unrestricted"
    assert result["code"] == "-"
    assert result["restricted_categories"] == []


@pytest.mark.parametrize("written", ["D/E", "(D/E)", " (d/e) "])
def test_the_code_is_read_however_it_was_written_into_the_field(written):
    """Table A prints it in brackets, the autofill strips them, and a user may
    type it either way. Three spellings of one code must not become three
    answers."""
    result = check_adr_tunnel(entries(product(tunnel_code=written)), "nl",
                              points_status="above_threshold")
    assert result["code"] == "D/E"


def test_a_line_without_a_code_stops_the_determination_instead_of_lowering_it():
    """The dangerous failure here is silence: with the unknown line skipped the
    load would get the code of the *other* substance, which may be milder."""
    result = check_adr_tunnel(
        entries(product(tunnel_code="C"), product(un_number="1993", tunnel_code="")),
        "nl", points_status="above_threshold",
    )
    assert result["status"] == "incomplete"
    assert result["code"] is None
    assert "UN 1993" in result["message"]


def test_a_code_the_table_does_not_know_is_named_rather_than_ignored():
    result = check_adr_tunnel(entries(product(tunnel_code="Z9")), "nl",
                              points_status="above_threshold")
    assert result["status"] == "unknown_code"
    assert "Z9" in result["message"]


# --- The two codes that split on the explosive mass -----------------------


def test_the_adr_own_example_of_c5000d():
    """8.6.4, the worked example under the table: UN 0161 smokeless powder,
    classification code 1.3C, code C5000D, in a quantity amounting to a total
    net explosive mass of 3,000 kg is forbidden through tunnels of category D
    and E — not C, because 3,000 does not exceed 5,000."""
    result = check_adr_tunnel(
        entries(product(un_number="0161", tunnel_code="C5000D",
                        transport_category="2", net_explosive_mass="3000",
                        adr_total_quantity="3000")),
        "nl", points_status="above_threshold",
    )
    assert result["code"] == "C5000D"
    assert result["restricted_categories"] == ["D", "E"]


def test_above_the_threshold_the_stricter_half_of_the_row_applies():
    result = check_adr_tunnel(
        entries(product(un_number="0161", tunnel_code="C5000D",
                        net_explosive_mass="5001", adr_total_quantity="5001")),
        "nl", points_status="above_threshold",
    )
    assert result["restricted_categories"] == ["C", "D", "E"]


def test_the_explosive_mass_is_totalled_over_the_unit_not_read_per_line():
    """8.6.4 says "per transport unit". Two pallets of 600 kg net explosive
    mass under B1000C together exceed the 1,000 kg the row splits on; assessing
    them line by line would keep both under it and give the milder answer."""
    result = check_adr_tunnel(
        entries(product(un_number="0004", tunnel_code="B1000C",
                        net_explosive_mass="600", adr_total_quantity="600"),
                product(un_number="0005", tunnel_code="B1000C",
                        net_explosive_mass="600", adr_total_quantity="600")),
        "nl", points_status="above_threshold",
    )
    assert result["explosive_mass_kg"] == 1200
    assert result["restricted_categories"] == ["B", "C", "D", "E"]


# --- 8.6.3.3: what 1.1.3 takes out of the determination -------------------


def test_a_consignment_within_the_1_1_3_6_exemption_gets_no_code_at_all():
    """The provision that changes an answer rather than adding one. Goods
    carried under 1.1.3 are not subject to tunnel restrictions and must not be
    counted — so there is nothing left to determine a code from, and printing
    one on the document invites an assumption nobody has earned."""
    result = check_adr_tunnel(
        entries(product(transport_category="3", adr_total_quantity="200")),
        "nl", points_status="exempt_possible",
    )
    assert result["status"] == "exempt"
    assert result["code"] is None
    assert result["restricted_categories"] == []
    assert "8.6.3.3" in result["message"]


def test_the_lq_marking_brings_a_category_e_restriction_back_with_it():
    """The one exception 8.6.3.3 names. Above 8 tonnes gross of LQ packages the
    unit carries the mark of 3.4.13, and 8.6.4 bars a marked unit from category
    E tunnels — even though every substance on it travels under 1.1.3."""
    result = check_adr_tunnel(
        entries(product(transport_category="3", adr_total_quantity="200")),
        "nl", points_status="exempt_possible", lq_marking_required=True,
    )
    assert result["status"] == "lq_marking_only"
    assert result["restricted_categories"] == ["E"]
    assert "3.4.13" in result["message"]


def test_a_load_over_the_threshold_is_determined_as_usual():
    """The mirror of the exemption case: above 1,000 points nothing is carried
    under 1.1.3.6 and the whole table applies again."""
    result = check_adr_tunnel(
        entries(product(transport_category="2", adr_total_quantity="400")),
        "nl", points_status="above_threshold",
    )
    assert result["status"] == "derived"


def test_a_substance_forbidden_for_carriage_does_not_get_a_tunnel_code():
    """There is no route to restrict for something that may not be offered at
    all, and the prohibition is already in view elsewhere."""
    result = check_adr_tunnel(
        entries(product(tunnel_code="B", transport_forbidden=True),
                product(un_number="1993", tunnel_code="E")),
        "nl", points_status="above_threshold",
    )
    assert [row["product"] for row in result["rows"]] == ["UN 1993"]
    assert result["code"] == "E"


# --- Where it appears in the compliance result ----------------------------


def test_the_check_runs_for_road_and_not_for_rail_or_water():
    """RID table A has no column (15) and the ADN document does not carry the
    code either. A tunnel code on a CIM is the same category of defect as the
    CV28 that used to be quoted there."""
    goods = entries(product(transport_category="2", adr_total_quantity="400"))
    assert "adr_tunnel" in check_compliance(goods, ["ADR"], "nl")
    assert "adr_tunnel" not in check_compliance(goods, ["RID"], "nl")
    assert "adr_tunnel" not in check_compliance(goods, ["ADN"], "nl")
    assert "adr_tunnel" not in check_compliance(goods, ["IMDG"], "nl")


def test_the_result_takes_its_1_1_3_6_answer_from_the_points_check():
    """The two must not disagree. If the points table says the consignment is
    within the exemption, the tunnel section may not go on assigning a code as
    though it were not."""
    goods = entries(product(transport_category="3", adr_total_quantity="200"))
    result = check_compliance(goods, ["ADR"], "nl")
    assert result["adr_points"]["status"] == "exempt_possible"
    assert result["adr_tunnel"]["status"] == "exempt"


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_the_answer_is_written_in_the_language_of_the_screen(language):
    result = check_adr_tunnel(entries(product()), language,
                              points_status="above_threshold")
    assert result["message"]
    assert result["note"]


def test_the_answer_says_what_it_does_not_cover():
    """Carriage in tanks or in bulk is stricter for five of the codes, and which
    tunnels lie on the route is not something this application can know. Both
    belong next to the answer rather than in a manual."""
    result = check_adr_tunnel(entries(product()), "nl", points_status="above_threshold")
    assert "colli" in result["note"]
    assert "1.9.5" in result["note"]


def test_the_load_code_reaches_the_exported_document():
    """The screen is not the only place this may appear. The per-substance code
    has been printed on the transport document for a long time; the code for the
    whole load — the one 8.6.3.2 asks for and the driver acts on — never was."""
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document
    from tests.test_documents import BASE_VALUES, LINES

    goods = entries(product(un_number="1017", transport_category="1",
                            tunnel_code="C/D", adr_total_quantity="400"))
    _errors, warnings = validate_document(
        get_document("cmr"), dict(BASE_VALUES), LINES, goods, "nl"
    )
    said = [w for w in warnings if "8.6.3" in w]
    assert said, warnings
    assert "C/D" in said[0]
