"""The package label sheet: the right content at the right size, and honest
about the two things it will not do.

The size assertions here are not decoration. A label built to the other reading
of "100 mm x 100 mm" is 71 mm on a side where the regulation asks for 100, on
every package, and it looks entirely correct. So the printed geometry is
measured out of the produced PDF rather than trusted.
"""
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.dg import database
from app.services.documents.package_label_sheet import (
    FULL_SIZE_MM,
    artwork_for,
    render_package_label_sheet,
)

CONSIGNMENT = {"reference": "CP-2026-500", "consignor_name": "Afzender BV"}


def goods(un, **extra):
    rows = database.get_un_entries(un)
    row = rows[0] if rows else {}
    item = {
        "un_number": un,
        "proper_shipping_name": row.get("name_nl") or "",
        "class": row.get("class") or "",
        "labels": row.get("labels") or "",
        "packing_group": row.get("packing_group") or "",
    }
    item.update(extra)
    return item


def sheet(*products, profiles=("ADR",), language="nl"):
    entries = [{"line_id": "1", "products": list(products)}]
    return render_package_label_sheet(
        CONSIGNMENT, [], entries, language, list(profiles))


def pages(path):
    with pymupdf.open(str(path)) as document:
        return [page.get_text() for page in document]


# --- the size, measured off the page ---


def test_a_label_is_printed_at_one_hundred_millimetres_on_each_side():
    """5.2.2.2.1.1.2, read as 49 CFR 172.407(c)(1) spells it out.

    The artwork is the diamond's bounding box — its points touch the canvas
    edges — so a box of 141.42 mm gives a side of exactly 100 mm. Measured out
    of the PDF because an off-by-root-two here is invisible on screen and wrong
    on every package.
    """
    path = sheet(goods("1263"))
    with pymupdf.open(str(path)) as document:
        page = document[1]
        rects = [rect for image in page.get_images(full=True)
                 for rect in page.get_image_rects(image[0])]
    assert rects, "the label page carries no artwork"
    width_mm = rects[0].width / 72 * 25.4
    assert round(width_mm, 1) == round(FULL_SIZE_MM, 1)
    assert round(width_mm / 2 ** 0.5) == 100


def test_the_page_is_a4_and_carries_cut_marks():
    path = sheet(goods("1263"))
    with pymupdf.open(str(path)) as document:
        page = document[1]
        assert round(page.rect.width / 72 * 25.4) == 210
        assert round(page.rect.height / 72 * 25.4) == 297
        drawn = sum(len(item["items"]) for item in page.get_drawings())
    # Two strokes at each of four corners.
    assert drawn >= 8


def test_one_label_per_page_and_the_arithmetic_that_says_so():
    """Two full-size labels need 283 mm, against A4's 210 by 297.

    Side by side is impossible. Stacked is not impossible — 282.84 mm does fit
    inside 297 mm — and the first version of this test claimed otherwise, which
    is why the claim is now written as arithmetic rather than as a verdict.
    What rules it out is what is left: 14 mm for both margins, the caption and
    the cut marks together.
    """
    two = FULL_SIZE_MM * 2
    assert two > 210, "side by side does not fit across the page"
    assert two < 297, "stacked fits on the paper; margins are what rule it out"
    assert round(297 - two) == 14


# --- which artwork answers for which model ---


@pytest.mark.parametrize("model,expected", [
    ("3", "3.png"),
    ("6.1", "6_1.png"),
    ("9A", "9A.png"),
    ("2.1", "2_1.png"),
])
def test_a_model_maps_to_its_own_artwork(model, expected):
    found = artwork_for(model)
    assert found is not None and found.name == expected


@pytest.mark.parametrize("division", ["1.1D", "1.2B", "1.3C"])
def test_divisions_one_one_to_one_three_share_model_one(division):
    """The regulation prints one model for those three, with a place on it for
    the division and the compatibility group."""
    found = artwork_for(division)
    assert found is not None and found.name == "1.png"


@pytest.mark.parametrize("division,expected", [
    ("1.4S", "1_4.png"), ("1.5D", "1_5.png"), ("1.6N", "1_6.png")])
def test_divisions_one_four_to_one_six_have_their_own_models(division, expected):
    found = artwork_for(division)
    assert found is not None and found.name == expected


def test_an_unknown_model_gets_nothing_rather_than_a_neighbour():
    """Substituting a nearby model would print the wrong hazard. Printing
    nothing leaves the label named on the working page and not drawn."""
    assert artwork_for("42") is None
    assert artwork_for("") is None


# --- what the sheet says, and what it refuses to say ---


def test_the_working_page_lists_the_regime_beside_every_line():
    """A consignment going by road and then by sea gets both answers, because
    they differ, and a packer who sees only one packs the wrong box."""
    text = pages(sheet(goods("1263"), profiles=("ADR", "IMDG")))[0]
    assert "ADR" in text and "IMDG" in text


def test_the_sea_leg_shows_the_name_the_land_leg_does_not():
    """IMDG 5.2.1.1 marks the proper shipping name on every package; ADR asks
    for it on Class 1 and Class 7 only. Paint is neither."""
    text = pages(sheet(goods("1263"), profiles=("ADR", "IMDG")))[0]
    assert "shipping name" in text.replace("\n", " ")


def test_the_sheet_says_paper_is_not_the_material():
    """5.2.1.2 wants a mark that survives the weather, and the IMDG Code one
    that survives three months in the sea. Neither is a laser print, and a
    sheet that stays quiet about that invites exactly that mistake."""
    text = pages(sheet(goods("1263")))[0].replace("\n", " ")
    assert "drie maanden" in text or "three months" in text


def test_the_orientation_arrows_are_named_as_not_assessed():
    text = pages(sheet(goods("1263")))[0].replace("\n", " ")
    assert "5.2.1.10" in text


def test_the_battery_mark_is_named_but_not_drawn():
    """Its official artwork was never cut from the edition the way the class
    labels were, so it is listed and not redrawn."""
    path = sheet(goods("3480"))
    text = pages(path)[0].replace("\n", " ")
    assert "5.2.1.9" in text
    assert "battery" in text.lower()


def test_a_consignment_without_dangerous_goods_says_so_on_one_page():
    path = render_package_label_sheet(CONSIGNMENT, [], [], "nl", ["ADR"])
    body = pages(path)
    assert len(body) == 1
    assert "geen gevaarlijke goederen" in body[0].replace("\n", " ")


def test_the_same_label_is_not_printed_twice_for_one_line():
    """Two products on one line that carry the same model get one page."""
    path = sheet(goods("1263"), goods("1263"))
    assert len(pages(path)) == 2


def test_every_language_renders():
    for language in ("nl", "en", "de", "fr"):
        body = pages(sheet(goods("1263"), language=language))
        assert len(body) >= 2
        assert body[0].strip()


# --- through the route a wizard actually calls ---


def user():
    from types import SimpleNamespace
    return SimpleNamespace(id=1, username="verify", role="admin", active=True)


def test_the_export_route_produces_the_sheet():
    app.dependency_overrides[get_current_user] = user
    with TestClient(app) as api:
        response = api.post("/api/documents/export", json={
            "document_key": "package_label_sheet",
            "values": CONSIGNMENT,
            "lines": [],
            "dangerous_goods": [{"line_id": "1", "products": [goods("1263")]}],
            "output_language": "nl",
            "profiles": ["ADR", "IMDG"],
        })
    app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 200, response.text
    assert response.content[:4] == b"%PDF"


def test_the_registry_offers_it_on_every_mode_that_carries_packages():
    """Air is out: the IATA marking rules have not been read."""
    from app.services.documents.registry import get_registry
    registry = get_registry()
    per_mode = {mode["key"]: mode["documents"] for mode in registry["modalities"]}
    for mode in ("road", "rail", "sea", "inland"):
        assert "package_label_sheet" in per_mode[mode]
    assert "package_label_sheet" not in per_mode["air"]
