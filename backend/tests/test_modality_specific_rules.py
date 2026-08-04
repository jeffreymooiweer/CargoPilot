"""Wat voor de weg geldt, geldt niet vanzelf voor het spoor of het water.

CargoPilot behandelde ADR, RID en ADN als één ding. Dat is begrijpelijk — de
drie regimes lijken sterk op elkaar en delen hun structuur — maar het levert
twee soorten fout op, en de tweede is de ergste.

**Een verzonnen vermelding op een officieel document.** De
tunnelbeperkingscode komt uit kolom 15 van ADR Tabel A en hoort volgens
5.4.1.1.1 (k) op het wegdocument. RID Tabel A kent die kolom niet en het
ADN-vervoersdocument draagt hem evenmin. Toch zette de app "(D/E)" op een
CIM-vrachtbrief en op een ADN-document. Dat is geen ontbrekende controle maar
onjuiste informatie die de app zelf heeft toegevoegd.

**Een uitkomst die strenger of losser lijkt dan zij is.** De 1.1.3.6-punten en
de samenlading van 7.5.2 worden met de ADR-tabellen berekend. RID en ADN kennen
hun eigen versies van die hoofdstukken, en die staan niet in CargoPilot. De
uitkomst stilzwijgend presenteren als "de RID-uitkomst" geeft de gebruiker een
zekerheid die er niet is. Hij mag hem hebben als indicatie — maar dan wel met
dat etiket erop.
"""

import pytest

from app.services.dg.autofill import description_line
from app.services.dg.compliance import check_compliance

GASOLINE = {
    "un_number": "1203",
    "proper_shipping_name": "GASOLINE",
    "class": "3",
    "packing_group": "II",
    "tunnel_code": "D/E",
    "transport_category": "2",
    "adr_total_quantity": "400",
    "quantity_packages": "10",
    "type_of_package": "jerrycan",
}


def entries():
    return [{"line_id": "L1", "products": [dict(GASOLINE)]}]


# --- De tunnelcode hoort alleen op het wegdocument ------------------------


def test_the_road_document_carries_the_tunnel_code():
    assert "(D/E)" in description_line(dict(GASOLINE), "ADR")


@pytest.mark.parametrize("profile", ["RID", "ADN", "IMDG", "IATA_DGR"])
def test_no_other_document_carries_it(profile):
    """RID Tabel A heeft geen kolom 15 met een tunnelcode, en zee en lucht al
    helemaal niet. Er hoort dus niets tussen haakjes te staan dat daarop lijkt."""
    assert "D/E" not in description_line(dict(GASOLINE), profile)


def test_the_cim_export_does_not_show_a_tunnel_code():
    """De CIM draagt het RID-profiel; de goederenkolom is wat er gedrukt wordt."""
    import openpyxl

    from app.services.documents.exporter import export_document
    from tests.test_documents import BASE_VALUES, LINES

    path = export_document("cim", dict(BASE_VALUES), LINES, entries(), language="nl")
    text = "\n".join(
        str(cell)
        for row in openpyxl.load_workbook(path).active.iter_rows(values_only=True)
        for cell in row
        if cell
    )
    assert "GASOLINE" in text, "de stof hoort er wel op te staan"
    assert "(D/E)" not in text


def test_the_cmr_export_does_show_one():
    import openpyxl

    from app.services.documents.exporter import export_document
    from tests.test_documents import BASE_VALUES, LINES

    path = export_document("cmr", dict(BASE_VALUES), LINES, entries(), language="nl")
    text = "\n".join(
        str(cell)
        for row in openpyxl.load_workbook(path).active.iter_rows(values_only=True)
        for cell in row
        if cell
    )
    assert "(D/E)" in text


# --- En de grondslag van een berekening wordt benoemd ---------------------


def test_a_road_shipment_gets_no_caveat():
    """Voor ADR ís de ADR-tabel de juiste tabel; daar valt niets bij te melden."""
    out = check_compliance(entries(), ["ADR"], "nl")
    assert out["adr_points"]["basis_note"] is None
    assert "adr_mixed_loading_basis_note" not in out


@pytest.mark.parametrize("profile", ["RID", "ADN"])
def test_rail_and_inland_waterway_say_which_tables_were_used(profile):
    out = check_compliance(entries(), [profile], "nl")
    note = out["adr_points"]["basis_note"]
    assert note and profile in note and "ADR" in note
    assert profile in out["adr_mixed_loading_basis_note"]


def test_the_caveat_names_both_when_both_are_selected():
    out = check_compliance(entries(), ["ADR", "RID", "ADN"], "nl")
    note = out["adr_points"]["basis_note"]
    assert "RID" in note and "ADN" in note


def test_the_calculation_itself_is_unchanged():
    """De uitkomst blijft dezelfde — alleen het etiket is nieuw. Anders zou dit
    stilletjes ook de puntentelling van wegvervoer veranderen."""
    road = check_compliance(entries(), ["ADR"], "nl")["adr_points"]
    rail = check_compliance(entries(), ["RID"], "nl")["adr_points"]
    assert road["total_points"] == rail["total_points"] == 1200.0
    assert road["status"] == rail["status"]


def test_the_basis_is_named_in_every_language():
    for language in ("nl", "en", "de"):
        note = check_compliance(entries(), ["RID"], language)["adr_points"]["basis_note"]
        assert note and "ADR" in note and "RID" in note


def test_sea_and_air_never_get_the_land_checks_at_all():
    out = check_compliance(entries(), ["IMDG"], "nl")
    assert "adr_points" not in out
    assert "adr_mixed_loading" not in out
