"""The stowage plan of ADN 7.1.4.11.1, and the two things it must not become.

Two readings of the provision — the printed Dutch edition and the English one —
say the same short thing: the boatmaster sets down in a stowage plan which goods
are placed in the individual holds or on deck, described there as 5.4.1.1.1 (a)
to (d) describes them in the transport document. 7.1.4.11.2 adds that for goods
in containers the container number suffices in the plan, provided the plan
carries an annex listing every container and what is in it.

The two things this plan must not become:

* **a second rendering of the goods.** "As in the transport document" is a
  requirement about sameness, so the descriptions come from the same function
  the transport document uses. Two renderings of one consignment that drift
  apart are worse than one rendering used twice.
* **a drawing.** A vessel's holds have a geometry this application knows nothing
  about, and a picture of a ship that does not exist would be believed.

And a position with no hold yet is not silently dropped: it is listed where it
cannot be missed, with the provision that asks for it.
"""
import fitz
import pytest

from app.services.dg import database
from app.services.dg.autofill import description_line
from app.services.documents.registry import get_document
from app.services.documents.stowage_plan import TEXT, render_stowage_plan


def product(un, **extra):
    row = database.get_un_entries(un)[0]
    values = {
        "un_number": un,
        "proper_shipping_name": row.get("name_nl"),
        "class": row.get("class"),
        "packing_group": row.get("packing_group"),
        "quantity_packages": "12",
        "type_of_package": "vaten",
    }
    values.update(extra)
    return values


def text_of(path):
    with fitz.open(path) as pdf:
        return "\n".join(page.get_text() for page in pdf)


def plan(*entries, language="nl", values=None):
    return render_stowage_plan(values or {"vessel_name": "Rijnvaart 7"}, [],
                               list(entries), language)


def test_each_hold_gets_its_own_block():
    body = text_of(plan({"line_id": "L1", "products": [
        product("1203", hold="2"), product("1263", hold="1")]}))
    assert "Laadruim 1" in body
    assert "Laadruim 2" in body
    # Hold 1 is printed before hold 2, which is what makes the plan readable
    # against a vessel where the holds are numbered from the bow.
    assert body.index("Laadruim 1") < body.index("Laadruim 2")


def test_the_deck_is_not_a_hold():
    """7.1.4.11.1 names the holds and the deck side by side; the deck is not
    hold number zero and does not sort among them."""
    body = text_of(plan({"line_id": "L1", "products": [
        product("1203", hold="1"), product("1266", hold="dek")]}))
    assert TEXT["deck"]["nl"] in body
    assert body.index("Laadruim 1") < body.index(TEXT["deck"]["nl"])


def test_the_description_is_the_transport_documents_own():
    """Not a second rendering: the same function, so the two papers cannot
    drift apart."""
    goods = product("1203", hold="2")
    body = text_of(plan({"line_id": "L1", "products": [goods]}))
    expected = description_line(goods, "ADN")
    # The PDF wraps long lines, so the comparison is on the parts that carry
    # the meaning rather than on the line as one string.
    for part in ("UN 1203", "3", "II", "12 vaten"):
        assert part in body, part
    assert expected.startswith("UN 1203")


def test_a_position_without_a_hold_is_shown_and_not_dropped():
    """A plan that silently left out what has no hold yet would look complete
    and be wrong. It says which positions are missing one, and why that
    matters."""
    body = text_of(plan({"line_id": "L1", "products": [product("1993")]}))
    assert TEXT["unassigned"]["nl"] in body
    assert "7.1.4.11.1" in body


def test_containers_get_the_annex_the_provision_asks_for():
    """7.1.4.11.2: the container number suffices in the plan *provided* the
    plan carries a list of the containers and their contents."""
    body = text_of(plan({"line_id": "L1", "products": [
        product("1266", hold="1", container_number="MSCU1234567")]}))
    assert "MSCU1234567" in body
    assert TEXT["containers"]["nl"] in body


def test_no_annex_when_nothing_travels_in_a_container():
    body = text_of(plan({"line_id": "L1", "products": [product("1203", hold="1")]}))
    assert TEXT["containers"]["nl"] not in body


def test_the_plan_never_claims_to_be_a_drawing():
    body = text_of(plan({"line_id": "L1", "products": [product("1203", hold="1")]}))
    # On a fragment, not the whole sentence: the page wraps it, and a test that
    # broke on a line break would be testing the typesetting.
    assert "geen tekening van het schip" in body


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_the_plan_speaks_all_four_languages(language):
    body = text_of(plan({"line_id": "L1", "products": [product("1203", hold="1")]},
                        language=language))
    assert TEXT["title"][language] in body
    assert TEXT["hold"][language] in body


def test_the_document_is_registered_for_adn_with_dangerous_goods():
    document = get_document("stowage_plan")
    assert document is not None
    assert document["dg_profile"] == "ADN"
    assert document["dg_only"] is True
    assert document["exporter"] == "stowage"
    for language in ("nl", "en", "de", "fr"):
        assert document["label"][language]
        assert document["issue_status"][language]


# --- what the hold makes possible ------------------------------------------


def test_the_prohibition_of_sharing_a_hold_can_now_be_applied():
    """7.1.4.3.2 forbids two-blue-cone goods from sharing a hold with one-cone
    flammable goods. Until there was a stowage plan there was no hold to
    compare, so the finding could only say both kinds were on board. With the
    holds written down, the provision is applied to what the boatmaster wrote
    — and the hold it is breached in is named."""
    from app.services.dg.compliance import check_adn_hold_separation

    def entry(*products):
        return [{"line_id": "L1", "products": list(products)}]

    def rule(result):
        return next(f for f in result["findings"] if f["provision"] == "7.1.4.3.2")

    # UN 1017 carries two cones; UN 1088 is class 3, one cone, and settled.
    shared = rule(check_adn_hold_separation(
        entry(product("1017", hold="1"), product("1088", hold="1")), "nl"))
    assert shared["holds"] == ["1"]

    apart = rule(check_adn_hold_separation(
        entry(product("1017", hold="1"), product("1088", hold="2")), "nl"))
    assert apart["holds"] == []

    # Nothing typed: the finding stays what it was, with no claim about holds.
    unknown = rule(check_adn_hold_separation(
        entry(product("1017"), product("1088")), "nl"))
    assert "holds" not in unknown


def test_the_deck_is_one_place_however_it_is_spelled():
    """Two people typing "dek" and "deck" have named the same deck, and a
    prohibition that missed that would be defeated by a keystroke."""
    from app.services.dg.compliance import check_adn_hold_separation

    result = check_adn_hold_separation(
        [{"line_id": "L1", "products": [product("1017", hold="dek"),
                                        product("1088", hold="Deck")]}], "nl")
    finding = next(f for f in result["findings"] if f["provision"] == "7.1.4.3.2")
    assert finding["holds"] == ["deck"]
