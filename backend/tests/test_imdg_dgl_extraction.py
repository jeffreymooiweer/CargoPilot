"""De parser voor de Dangerous Goods List van IMDG 42-24.

De lijst is een raster van achttien kolommen op 170 liggende pagina's. Wat er
misgaat is niet dat zo'n parser omvalt, maar dat hij een kolom opschuift of een
vervolgregel als nieuwe stof leest — en dan staan er 2.300 stoffen met een
verkeerde scheidingscode in de app zonder dat het opvalt.

Deze tests draaien op nagebouwde pagina's met verzonnen stoffen op de echte
x-posities. Ze leggen de meetkunde en de rijlogica vast, niet de inhoud van de
code; die hoort niet in deze repo.
"""

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "extract_imdg_dgl.py"
_spec = importlib.util.spec_from_file_location("extract_imdg_dgl", _PATH)
dgl = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = dgl
_spec.loader.exec_module(dgl)

BOUNDS = dgl.boundaries()


# --- De meetkunde -------------------------------------------------------------

def test_every_column_heading_lands_in_its_own_column():
    """De grens ligt halverwege twee koppen; elke kop hoort links daarvan."""
    for name, x in dgl.COLUMNS:
        assert dgl.column_of(x, BOUNDS) == name, name


def test_the_columns_do_not_overlap_and_leave_no_gap():
    for (_, _, right), (_, left, _) in zip(BOUNDS, BOUNDS[1:]):
        assert right == left


def test_the_drawn_rules_win_over_the_heading_midpoints():
    """De reden dat deze parser de getekende lijnen leest en niet het midden
    tussen twee koppen: x 806.6 draagt 409 woorden en viel bij die schatting
    net aan de verkeerde kant. Met echte grenzen valt het waar het hoort."""
    fallback = dgl.boundaries()
    assert dgl.column_of(806.6, fallback) == "segregation"  # de misser

    # Zoals de tabel werkelijk is verdeeld: een lijn tussen stuwage en scheiding
    # ligt rechts van 806.6, niet links ervan.
    rules = [40.0, 90.0, 188.0, 216.0, 255.0, 292.0, 328.0, 363.0, 397.0, 438.0,
             473.0, 514.0, 639.0, 668.0, 731.0, 768.0, 833.0, 958.0, 1123.0, 1160.0]
    measured = dgl.boundaries(rules)
    assert dgl.column_of(806.6, measured) == "stowage_and_handling"
    assert dgl.column_of(854.0, measured) == "segregation"
    assert dgl.column_of(963.1, measured) == "properties_and_observations"
    assert dgl.column_of(644.2, measured) == "tank_instructions"


def test_without_enough_rules_the_parser_falls_back_rather_than_inventing():
    """Te weinig lijnen betekent een pagina die anders is opgemaakt. Dan de
    schatting gebruiken en niet een verschoven raster doorvoeren."""
    assert dgl.boundaries([100.0, 200.0]) == dgl.boundaries()


# --- De rijlogica -------------------------------------------------------------

def line(**cells) -> dict[str, str]:
    return cells


def test_a_continuation_line_joins_the_entry_above_it():
    """Een lange vervoersnaam loopt door op de volgende tekstregel terwijl de
    kolom met het UN-nummer leeg blijft. Dat is geen nieuwe stof."""
    entries = dgl.merge_rows([
        line(un_number="1203", proper_shipping_name="GASOLINE or PETROL or", **{"class": "3"}),
        line(proper_shipping_name="MOTOR SPIRIT"),
        line(un_number="1263", proper_shipping_name="PAINT", **{"class": "3"}),
    ])
    assert len(entries) == 2
    assert entries[0]["proper_shipping_name"] == "GASOLINE or PETROL or MOTOR SPIRIT"
    assert entries[1]["proper_shipping_name"] == "PAINT"


def test_a_continuation_line_can_extend_any_column():
    entries = dgl.merge_rows([
        line(un_number="2031", proper_shipping_name="NITRIC ACID", segregation="SG6 SG16"),
        line(segregation="SG17 SG36"),
    ])
    assert entries[0]["segregation"] == "SG6 SG16 SG17 SG36"


def test_two_packing_groups_stay_two_entries():
    """UN 1361 staat twee keer in de lijst, één keer per verpakkingsgroep. Die
    mogen niet tot één regel samensmelten."""
    entries = dgl.merge_rows([
        line(un_number="1361", proper_shipping_name="CARBON", packing_group="II"),
        line(un_number="1361", proper_shipping_name="CARBON", packing_group="III"),
    ])
    assert [e["packing_group"] for e in entries] == ["II", "III"]


def test_a_continuation_before_any_entry_is_discarded():
    """Boven aan een pagina kan een restregel staan van de vorige pagina. Die
    aan de eerste stof van deze pagina plakken zou fout zijn."""
    entries = dgl.merge_rows([
        line(proper_shipping_name="leftover from the previous page"),
        line(un_number="1203", proper_shipping_name="GASOLINE"),
    ])
    assert len(entries) == 1
    assert entries[0]["proper_shipping_name"] == "GASOLINE"


def test_the_repeated_un_column_is_dropped():
    """De lijst herhaalt het UN-nummer rechts op de pagina. Dat is opmaak."""
    entries = dgl.merge_rows([
        line(un_number="1203", proper_shipping_name="GASOLINE", _un_number_repeat="1203"),
    ])
    assert "_un_number_repeat" not in entries[0]


def test_a_line_whose_first_cell_is_not_a_un_number_is_a_continuation():
    """Een cel met '1,000 L' in de eerste kolom bestaat niet, maar een getal
    dat toevallig vier cijfers heeft mag geen nieuwe stof beginnen als het
    ergens anders staat."""
    entries = dgl.merge_rows([
        line(un_number="1202", proper_shipping_name="DIESEL FUEL"),
        line(properties_and_observations="Flashpoint 3000 C"),
    ])
    assert len(entries) == 1
    assert "3000" in entries[0]["properties_and_observations"]


# --- De zelfcontrole ----------------------------------------------------------

def test_a_shifted_column_shows_up_as_disagreement():
    """Het vangnet: als de klasse-kolom verschuift, moet de vergelijking met de
    kaartgegevens dat melden in plaats van het door te laten."""
    good = [{"un_number": "1203", "class": "3", "ems": "F-E, S-E"}]
    shifted = [{"un_number": "1203", "class": "II", "ems": "F-E, S-E"}]
    assert dgl.cross_check(good)["class"]["differs"] == 0
    assert dgl.cross_check(shifted)["class"]["differs"] == 1


def test_the_cross_check_reports_an_agreement_ratio():
    result = dgl.cross_check([{"un_number": "1203", "class": "3"}])
    assert result["class"]["agreement"] == 1.0


def test_normalise_collapses_the_whitespace_a_pdf_leaves_behind():
    assert dgl.normalise({"a": "  two   words \n"}) == {"a": "two words"}
    assert dgl.normalise({"a": "   "}) == {}


# --- Wat de eerste proefrun aan het licht bracht ------------------------------

class FakeRect:
    """Een dunne verticale streep rond een gegeven midden.

    find_rules kijkt naar het midden van de rechthoek, niet naar haar
    linkerrand — een echte streep heeft breedte en staat symmetrisch om de
    grens die zij markeert.
    """

    def __init__(self, centre, height, width=0.7):
        self.x0, self.x1 = centre - width / 2, centre + width / 2
        self.width, self.height = width, height


class FakePage:
    def __init__(self, rects):
        self._rects = rects

    def get_drawings(self):
        return [{"rect": r} for r in self._rects]


def test_short_cell_borders_still_reveal_the_columns():
    """De lijst trekt geen kolomlijn over de pagina maar omrandt elk rijblok:
    de hoogste verticaal is een punt of tachtig. Eisen dat een lijn de halve
    pagina beslaat leverde er nul op — precies de eerste mislukte proefrun."""
    rects = []
    for x in (65.2, 189.9, 218.3, 255.1, 289.1):
        rects += [FakeRect(x, 78.1) for _ in range(20)]
    assert dgl.find_rules(FakePage(rects)) == [65.2, 189.9, 218.3, 255.1, 289.1]


def test_a_stray_line_is_not_mistaken_for_a_column_edge():
    """Een echte grens komt door de hele tabel terug; een losse streep niet."""
    rects = [FakeRect(65.2, 78.1) for _ in range(40)]
    rects += [FakeRect(190.0, 78.1) for _ in range(40)]
    rects.append(FakeRect(400.0, 20.0))
    assert 400.0 not in dgl.find_rules(FakePage(rects))


def test_borders_a_hair_apart_count_as_one_edge():
    rects = [FakeRect(189.9, 78.1) for _ in range(20)]
    rects += [FakeRect(190.6, 78.1) for _ in range(20)]
    assert dgl.find_rules(FakePage(rects)) == [189.9]  # het eerste midden telt


def test_a_page_without_drawings_yields_no_rules():
    assert dgl.find_rules(FakePage([])) == []


def test_the_body_window_clears_the_column_number_band():
    """Op y 131.7 staan de kolomnummers '(1) (2) (3)' en op y 140.5 de
    verwijzingen naar de secties. Die kwamen als gegevens binnen."""
    assert dgl.BODY_TOP > 140.5


def test_a_cell_that_runs_past_its_column_is_flagged_not_swallowed():
    """'0289 CORD,' betekent dat de vervoersnaam over de grens is gelezen. Zo'n
    rij overslaan zou hem verbergen; hem gewoon meenemen zou een afgekapte naam
    opleveren. Hij blijft herkenbaar zodat de telling hem meldt."""
    assert dgl.UN_OVERFLOW.match("0289 CORD,")
    assert not dgl.UN_OVERFLOW.match("0289")
    entries = dgl.merge_rows([line(un_number="0289 CORD,", proper_shipping_name="DETONATING,")])
    assert len(entries) == 1
    assert entries[0]["un_number"] == "0289 CORD,"


def test_the_alignment_is_verified_not_assumed():
    """Draagt de eerste gevonden lijn de buitenrand van de tabel of al de
    eerste kolomscheiding? Dat scheelt één plek voor elke kolom. Beide worden
    geprobeerd; de uitlijning waarbij elke kop in haar eigen kolom valt wint."""
    inner = [65.2, 189.9, 218.3, 255.1, 289.1, 326.0, 362.8, 397.0, 438.0, 473.0,
             514.0, 639.0, 668.0, 731.0, 768.0, 833.0, 958.0, 1123.0, 1160.0]
    assert dgl._headings_land_correctly(dgl.boundaries(inner))
    assert dgl._headings_land_correctly(dgl.boundaries([42.0] + inner))


def test_rules_that_fit_no_alignment_fall_back_to_the_estimate():
    """Randen die nergens op de koppen aansluiten zijn geen kolomindeling.
    Dan liever de schatting dan een raster dat er alleen precies uitziet."""
    nonsense = [float(100 + 40 * n) for n in range(25)]
    assert dgl.boundaries(nonsense) == dgl.boundaries()
