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

# Het raster zoals p627 het werkelijk tekent: tweeëntwintig randen, dus
# eenentwintig cellen. De nummerband zet boven elke cel het kolomnummer uit de
# code, behalve boven de goot tussen de twee helften van de spread.
RULES = [42.5, 65.2, 189.9, 218.3, 255.1, 289.1, 326.0, 362.8, 399.7, 439.4,
         476.2, 515.9, 552.8, 637.8, 654.8, 694.5, 731.3, 771.0, 827.7, 884.4,
         1125.3, 1148.0]
LABELS = ["1", "2", "3", "4", "5", "6", "7a", "7b", "8", "9", "10", "11",
          None, "12", "13", "14", "15", "16a", "16b", "17", "18"]
MARKERS = [((left + right) / 2, label)
           for (left, right), label in zip(zip(RULES, RULES[1:]), LABELS) if label]

BOUNDS = dgl.boundaries(RULES, MARKERS)


# --- De meetkunde -------------------------------------------------------------

def test_every_column_number_names_the_cell_it_stands_over():
    for x, label in MARKERS:
        assert dgl.column_of(x, BOUNDS) == dgl.COLUMN_NAMES[label], label


def test_the_columns_do_not_overlap_and_leave_no_gap():
    for (_, _, right), (_, left, _) in zip(BOUNDS, BOUNDS[1:]):
        assert right == left


def test_the_gutter_between_the_two_halves_stays_nameless():
    """De lijst staat als spread op één liggend vel. Tussen kolom (11) en
    kolom (12) zit vijfentachtig punt wit met een rand aan weerskanten. Dat is
    een cel voor de tekening en geen kolom voor de code; hem meetellen schoof
    elke kolom erna een plaats op."""
    assert dgl.column_of(595.0, BOUNDS).startswith("_unnamed")


def test_the_shipping_name_no_longer_bleeds_into_the_un_column():
    """Waar het op stukliep. De vervoersnaam begint op x 68; de schatting
    'midden tussen twee koppen' legde de grens op 72, en dus belandde het
    eerste woord van elke regel van de naam in de UN-kolom:
    "1354 TRINITROBENZENE, with by G". De getekende rand ligt op 65.2."""
    assert dgl.column_of(49.0, BOUNDS) == "un_number"
    assert dgl.column_of(68.0, BOUNDS) == "proper_shipping_name"


def test_the_right_hand_half_lands_where_it_belongs():
    """De tweede misser: stuwage, scheiding en eigenschappen liepen door elkaar
    heen — 'E SG7 Desensitized SG30 crystals. compartments air.'"""
    assert dgl.column_of(806.6, BOUNDS) == "stowage_and_handling"
    assert dgl.column_of(854.2, BOUNDS) == "segregation"
    assert dgl.column_of(886.4, BOUNDS) == "properties_and_observations"
    assert dgl.column_of(1128.0, BOUNDS) == "_un_number_repeat"
    assert dgl.column_of(644.4, BOUNDS) == "imo_tank_instructions"
    assert dgl.column_of(672.8, BOUNDS) == "tank_instructions"
    assert dgl.column_of(711.0, BOUNDS) == "tank_provisions"


def test_what_lies_outside_the_table_is_dropped_not_rounded_inwards():
    """In de marge staan paginanummers en het driehoekje dat een gewijzigde
    vermelding aanwijst. Dat bij de dichtstbijzijnde kolom optellen zou het als
    gegeven laten doorgaan."""
    assert dgl.column_of(20.0, BOUNDS) == ""
    assert dgl.column_of(1160.0, BOUNDS) == ""


def test_without_rules_or_numbers_no_grid_is_invented():
    """Te weinig randen of geen nummerband betekent een pagina die anders is
    opgemaakt. Die wordt overgeslagen en geteld, niet geraden."""
    assert dgl.boundaries([100.0, 200.0], MARKERS) == []
    assert dgl.boundaries(RULES, []) == []


def test_a_grid_missing_a_column_we_depend_on_is_refused():
    without_segregation = [(x, label) for x, label in MARKERS if label != "16b"]
    assert dgl.boundaries(RULES, without_segregation) == []


def test_numbers_that_do_not_line_up_with_the_rules_are_refused():
    """Twee nummers in één cel betekent dat randen en nummerband niet bij
    elkaar horen. Dan is de hele indeling verdacht."""
    crowded = [(100.0 + 3.0 * n, label) for n, (_x, label) in enumerate(MARKERS)]
    assert dgl.boundaries(RULES, crowded) == []


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


def test_the_change_marker_starts_a_new_entry_and_is_kept_as_a_fact():
    """42-24 zet een driehoekje voor elk gewijzigd UN-nummer, en de PDF levert
    dat als één woord: "△1361". Zolang dat niet als UN-nummer gold, telde de
    rij als vervolgregel en schoof zij bij de stof erboven naar binnen: UN 1360
    kreeg "4.3 4.2 4.2 4.2" als klasse en vier EmS-codes achter elkaar."""
    entries = dgl.merge_rows([
        line(un_number="1360", proper_shipping_name="CALCIUM PHOSPHIDE",
             **{"class": "4.3"}, ems="F-G, S-N"),
        line(un_number="△1361", proper_shipping_name="CARBON",
             **{"class": "4.2"}, ems="F-A, S-J"),
    ])
    assert [e["un_number"] for e in entries] == ["1360", "1361"]
    assert entries[0]["class"] == "4.3"
    assert entries[1]["amended"] == "42-24"
    assert "amended" not in entries[0]


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


def test_the_alignment_no_longer_has_to_be_guessed():
    """Draagt de eerste gevonden lijn de buitenrand van de tabel of al de
    eerste kolomscheiding? Zolang de kolommen op volgorde geteld werden,
    scheelde dat één plaats voor elke kolom en moest het geraden worden. Met
    de nummerband is er niets meer te raden: elke cel krijgt de naam van het
    nummer dat erboven staat, waar de reeks ook begint."""
    extra_rule = sorted(RULES + [595.0])  # een streep in de goot
    shifted = dgl.boundaries(extra_rule, MARKERS)
    assert dgl.column_of(854.2, shifted) == "segregation"
    assert dgl.column_of(68.0, shifted) == "proper_shipping_name"


def test_rules_that_fit_no_numbers_yield_nothing():
    """Randen die nergens op de nummerband aansluiten zijn geen kolomindeling.
    Dan liever niets dan een raster dat er alleen precies uitziet."""
    nonsense = [float(100 + 40 * n) for n in range(25)]
    assert dgl.boundaries(nonsense, MARKERS) == []


# --- Rijbanden ----------------------------------------------------------------

class FakeHRect:
    """Een dunne horizontale rand rond een gegeven midden."""

    def __init__(self, centre, width, height=0.7, x0=40.0):
        self.y0, self.y1 = centre - height / 2, centre + height / 2
        self.x0, self.x1 = x0, x0 + width
        self.width, self.height = width, height


class FakeWordPage:
    def __init__(self, words, rects=()):
        self._words, self._rects = words, list(rects)

    def get_text(self, kind):
        assert kind == "words"
        return self._words

    def get_drawings(self):
        return [{"rect": r} for r in self._rects]


def test_the_column_numbers_are_read_from_the_band_above_the_table():
    """Op y 131.7 staat '(1) (2) (3) …', op y 140.5 staan de verwijzingen naar
    de secties die elke kolom regelen. Alleen de eerste band draagt namen."""
    words = [
        (44.0, 131.7, 52.0, 140.0, "(1)", 0, 0, 0),
        (120.0, 131.7, 130.0, 140.0, "(2)", 0, 0, 1),
        (330.0, 131.7, 344.0, 140.0, "(7a)", 0, 0, 2),
        (840.0, 131.7, 858.0, 140.0, "(16b)", 0, 0, 3),
        (60.0, 140.5, 80.0, 148.0, "3.1.2", 0, 1, 0),
        (49.0, 205.0, 60.0, 215.0, "1203", 0, 2, 0),
    ]
    assert dgl.column_markers(FakeWordPage(words)) == [
        (48.0, "1"), (125.0, "2"), (337.0, "7a"), (849.0, "16b")]


def test_every_column_number_has_a_name():
    """Een nummer dat de tabel wel draagt maar deze parser niet kent zou als
    '_column_19' wegvallen zonder dat iemand het merkt."""
    for label in LABELS:
        if label is not None:
            assert label in dgl.COLUMN_NAMES


def test_row_rules_come_from_a_line_that_spans_the_table():
    page = FakeWordPage([], [FakeHRect(200.0, 1100.0), FakeHRect(260.0, 1100.0),
                             FakeHRect(230.0, 40.0)])  # deelvakje, geen rijrand
    assert dgl.find_row_rules(page) == [200.0, 260.0]


def test_a_row_rule_drawn_in_pieces_counts_just_the_same():
    """Deze tabel zet haar rijranden per cel neer, net als de kolomranden.
    Eisen dat één rechthoek de halve pagina beslaat vond er nul, en toen werd
    de hele pagina één band met twaalf stoffen erin. Wat telt is hoeveel
    breedte de stukjes op dezelfde hoogte samen bestrijken."""
    pieces = []
    for y in (200.0, 260.0):
        pieces += [FakeHRect(y, 60.0, x0=40.0 + 60 * n) for n in range(18)]
    pieces.append(FakeHRect(230.0, 40.0, x0=300.0))  # streepje binnen één cel
    assert dgl.find_row_rules(FakeWordPage([], pieces)) == [200.0, 260.0]


def test_a_word_lands_in_the_band_its_y_falls_in():
    assert dgl.band_of(180.0, [200.0, 260.0]) == 0
    assert dgl.band_of(210.0, [200.0, 260.0]) == 1
    assert dgl.band_of(300.0, [200.0, 260.0]) == 2


def test_two_entries_in_adjacent_bands_do_not_merge():
    """De y-tolerantie plakte UN 0291 en UN 0292 tot één vermelding met
    'ems': '- F-B, S-X - F-B, S-X'. Met de rijranden erbij blijft het twee."""
    words = [
        (49.0, 205.0, 60.0, 215.0, "0291", 0, 0, 0),
        (95.0, 205.0, 140.0, 215.0, "BOMBS", 0, 0, 1),
        (49.0, 265.0, 60.0, 275.0, "0292", 0, 1, 0),
        (95.0, 265.0, 150.0, 275.0, "GRENADES", 0, 1, 1),
    ]
    page = FakeWordPage(words)
    lines = dgl.page_lines(page, BOUNDS, row_rules=[200.0, 260.0, 320.0])
    entries = dgl.merge_rows(lines)
    assert [e["un_number"] for e in entries] == ["0291", "0292"]


def test_a_name_running_over_two_lines_stays_in_one_band():
    """Binnen één band mag de naam over meerdere tekstregels lopen; de woorden
    komen dan in leesvolgorde achter elkaar."""
    words = [
        (49.0, 205.0, 60.0, 215.0, "1203", 0, 0, 0),
        (95.0, 205.0, 140.0, 215.0, "GASOLINE", 0, 0, 1),
        (95.0, 218.0, 130.0, 228.0, "or", 0, 1, 0),
        (110.0, 218.0, 150.0, 228.0, "PETROL", 0, 1, 1),
    ]
    lines = dgl.page_lines(FakeWordPage(words), BOUNDS, row_rules=[200.0, 260.0])
    entries = dgl.merge_rows(lines)
    assert len(entries) == 1
    assert entries[0]["proper_shipping_name"] == "GASOLINE or PETROL"


def test_words_outside_the_body_window_are_ignored():
    words = [
        (49.0, 131.7, 60.0, 140.0, "(1)", 0, 0, 0),      # kolomnummerband
        (49.0, 205.0, 60.0, 215.0, "1203", 0, 1, 0),
        (49.0, 801.6, 60.0, 810.0, "579", 0, 2, 0),      # voettekst
    ]
    lines = dgl.page_lines(FakeWordPage(words), BOUNDS, row_rules=[200.0, 260.0])
    assert [c.get("un_number") for c in lines] == ["1203"]


class FakeVRect:
    """Een verticaal celrandje dat precies één rijband beslaat."""

    def __init__(self, x, y0, y1, width=0.7):
        self.x0, self.x1 = x - width / 2, x + width / 2
        self.y0, self.y1 = y0, y1
        self.width, self.height = width, y1 - y0


def banded_page(bands, columns=18):
    rects = []
    for y0, y1 in bands:
        rects += [FakeVRect(65.0 + 60 * n, y0, y1) for n in range(columns)]
    return FakeWordPage([], rects)


def test_row_bands_come_from_the_vertical_segments_own_extents():
    """Elk verticaal celrandje loopt over precies één rij, en er staan er
    achttien naast elkaar. Hun boven- en onderkant zijn dus de rijgrenzen —
    informatie die de eerste versie weggooide om horizontale lijnen te zoeken
    die er nauwelijks zijn, waarna de hele pagina één band werd."""
    page = banded_page([(150.0, 228.0), (228.0, 306.0), (306.0, 384.0)])
    assert dgl.find_row_rules(page) == [150.0, 228.0, 306.0, 384.0]


def test_the_column_edges_still_come_out_of_the_same_rectangles():
    page = banded_page([(150.0, 228.0), (228.0, 306.0)])
    assert dgl.find_rules(page)[:3] == [65.0, 125.0, 185.0]


def test_the_change_marker_does_not_push_the_un_number_out_of_the_table():
    """Het driehoekje staat vóór het nummer, dus "△1361" begint links van de
    buitenrand op x 42.5. Op de linkerrand afgaan liet die rijen zonder
    UN-nummer achter en dus als vervolgregel bij UN 1360 introkken. Het midden
    van het woord ligt wel in de kolom."""
    words = [
        (49.0, 205.0, 62.0, 215.0, "1360", 0, 0, 0),
        (36.0, 225.0, 62.0, 235.0, "△1361", 0, 1, 0),
    ]
    lines = dgl.page_lines(FakeWordPage(words), BOUNDS, row_rules=[200.0, 220.0, 260.0])
    assert [c.get("un_number") for c in lines] == ["1360", "△1361"]


def test_a_band_holding_several_short_entries_is_split_at_each_un_number():
    """De getekende randen omranden een blók rijen zodra de vermeldingen kort
    zijn. Op p627 zaten UN 1360, UN 1361 (twee verpakkingsgroepen) en UN 1362
    zo in één band, en kwamen ze als één vermelding met klasse '4.3 4.2 4.2
    4.2' naar buiten. Elke rij begint met een UN-nummer, dus daarboven hoort
    een grens — ook waar de tabel er geen tekent."""
    words = [
        (49.0, 205.0, 62.0, 215.0, "1360", 0, 0, 0),
        (200.0, 205.0, 212.0, 215.0, "4.3", 0, 0, 1),
        (49.0, 225.0, 66.0, 235.0, "△1361", 0, 1, 0),
        (200.0, 225.0, 212.0, 235.0, "4.2", 0, 1, 1),
        (49.0, 245.0, 62.0, 255.0, "1362", 0, 2, 0),
        (200.0, 245.0, 212.0, 255.0, "4.2", 0, 2, 1),
    ]
    page = FakeWordPage(words, [FakeVRect(65.2, 200.0, 280.0) for _ in range(18)])
    entries = dgl.merge_rows(dgl.page_lines(page, BOUNDS,
                                            dgl.row_rules_for(page, BOUNDS)))
    assert [e["un_number"] for e in entries] == ["1360", "1361", "1362"]
    assert [e["class"] for e in entries] == ["4.3", "4.2", "4.2"]


def test_a_drawn_row_rule_and_a_un_number_do_not_make_two_boundaries():
    """De getekende rand valt samen met het begin van de rij eronder. Twee
    grenzen vlak na elkaar zouden een lege band tussen elke twee rijen
    zetten."""
    words = [(49.0, 202.0, 62.0, 212.0, "1360", 0, 0, 0)]
    page = FakeWordPage(words, [FakeVRect(65.2, 200.0, 280.0) for _ in range(18)])
    assert dgl.row_rules_for(page, BOUNDS) == [199.0, 280.0]


def test_horizontal_rules_remain_the_fallback():
    """Een pagina zonder verticale segmenten mag alsnog op haar horizontale
    randen worden verdeeld."""
    page = FakeWordPage([], [FakeHRect(200.0, 1100.0), FakeHRect(260.0, 1100.0)])
    assert dgl.find_row_rules(page) == [200.0, 260.0]
