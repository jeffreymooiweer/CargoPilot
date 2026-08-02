"""De parser die de 16a- en 16b-codes uit hoofdstuk 7 van de IMDG-code leest.

De invoer is een PDF die deze omgeving niet kan ophalen en die hier ook niet
hoort te staan — alleen afgeleide gegevens komen in de repo, niet de
regelgevingstekst. Daarom draaien deze tests op nagebouwde pagina's met
verzonnen codes: ze leggen de *opmaak* vast waar de parser tegenaan loopt, niet
de inhoud van de code.

Wat er misgaat bij het lezen van een PDF-tabel is namelijk voorspelbaar: kop- en
voetregels midden in de tabel, omschrijvingen over meerdere regels, een tab
achter het sectienummer, een kolom die samentrekt. Dat is precies wat hier
wordt afgedwongen.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "extract_imdg_codes.py"
_spec = importlib.util.spec_from_file_location("extract_imdg_codes", _PATH)
extractor = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = extractor
_spec.loader.exec_module(extractor)

SPECS = {section["key"]: section for section in extractor.SECTIONS}


def lines(text: str) -> list[str]:
    """Dezelfde opschoning als op een echte pagina."""
    out = []
    for raw in text.splitlines():
        line = raw.replace("\t", " ").replace("\xa0", " ").strip()
        if line and not extractor.NOISE.match(line):
            out.append(line)
    return out


# Een nagebootste pagina: sectienummer met tab, tabelkop, een paginawissel
# middenin met alle kop- en voetregels, en een omschrijving over drie regels.
STOWAGE_PAGE = """Part 7 – Provisions concerning transport operations
482
IMDG Code (Amendment 42-24)  2024 EDITION
7
7.1.5\t
Stowage codes
\tThe stowage codes given in column 16a of the Dangerous Goods List are as specified below:
Stowage
code
Description
SW1
First description.
SW2
Second description, which runs on
across a second line
and a third.
MSC 108/20/Add.2
Annex 8, page 493
Chapter 7.1 – General stowage provisions
483
IMDG Code (Amendment 42-24)  2024 EDITION
Stowage
code
Description
SW3
Third description.
SW31
Last description.
■
7.1.6 \t
Handling codes
\tThe handling codes given in column 16a of the Dangerous Goods List are as specified below:
H1
A handling description.
Chapter 7.2
"""

SEGREGATION_PAGE = """7.2.8\t
Segregation codes
\tThe segregation codes given in column 16b of the Dangerous Goods List are as specified below:
Segregation
code
Description
SG1
Something about division 1.3.
SG2
[Reserved]
SG78
Stow "separated longitudinally" from division 1.1, 1.2, and 1.5.
Annex
Segregation flow chart
SG99
This comes after the stop marker and must not be read.
"""


def test_a_code_and_its_description_are_paired():
    codes = extractor.parse_codes(lines(STOWAGE_PAGE), SPECS["stowage_codes"])
    assert codes["SW1"] == "First description."


def test_a_description_spanning_several_lines_is_joined():
    codes = extractor.parse_codes(lines(STOWAGE_PAGE), SPECS["stowage_codes"])
    assert codes["SW2"] == "Second description, which runs on across a second line and a third."


def test_headers_and_footers_inside_the_table_are_dropped():
    """De uitgave zet haar kop- en voetregels middenin de tabel. Die mogen
    nooit als omschrijving bij de vorige code belanden."""
    codes = extractor.parse_codes(lines(STOWAGE_PAGE), SPECS["stowage_codes"])
    for text in codes.values():
        assert "MSC 108" not in text
        assert "IMDG Code (Amendment" not in text
        assert "Annex 8, page" not in text
        assert "Description" not in text


def test_the_series_stops_at_the_next_section():
    codes = extractor.parse_codes(lines(STOWAGE_PAGE), SPECS["stowage_codes"])
    assert set(codes) == {"SW1", "SW2", "SW3", "SW31"}
    assert "H1" not in codes


def test_a_two_digit_code_is_not_read_as_a_one_digit_code():
    """SW31 mag niet als SW3 gelezen worden; dat zou de laatste omschrijving
    over de eerdere heen schrijven."""
    codes = extractor.parse_codes(lines(STOWAGE_PAGE), SPECS["stowage_codes"])
    assert codes["SW3"] == "Third description."
    assert codes["SW31"] == "Last description."


def test_the_handling_codes_are_read_from_their_own_section():
    codes = extractor.parse_codes(lines(STOWAGE_PAGE), SPECS["handling_codes"])
    assert codes == {"H1": "A handling description."}


def test_nothing_after_the_annex_marker_is_read():
    codes = extractor.parse_codes(lines(SEGREGATION_PAGE), SPECS["segregation_codes"])
    assert "SG99" not in codes
    assert set(codes) == {"SG1", "SG2", "SG78"}


def test_a_reserved_code_is_recognised_as_such():
    codes = extractor.parse_codes(lines(SEGREGATION_PAGE), SPECS["segregation_codes"])
    assert extractor.RESERVED.match(codes["SG2"])
    assert not extractor.RESERVED.match(codes["SG1"])


def test_codes_sort_numerically_not_alphabetically():
    assert sorted(["SW31", "SW3", "SW1"], key=extractor.sort_key) == ["SW1", "SW3", "SW31"]


# --- De controle die weigert stilzwijgend onvolledig te zijn -----------------

def full(prefix: str, highest: int, skip: set[int] = frozenset()) -> dict:
    return {"section": "x", "reserved": [],
            "codes": {f"{prefix}{n}": "a description" for n in range(1, highest + 1)
                      if n not in skip}}


def complete() -> dict:
    return {"stowage_codes": full("SW", 31), "handling_codes": full("H", 5),
            "segregation_codes": full("SG", 78, {75})}


def test_a_complete_reading_passes():
    assert extractor.sanity_check(complete()) == []


def test_a_reserved_code_still_counts_as_read():
    data = complete()
    data["segregation_codes"]["codes"].pop("SG64")
    data["segregation_codes"]["reserved"] = ["SG64"]
    assert extractor.sanity_check(data) == []


def test_a_missing_final_code_is_reported():
    data = complete()
    data["stowage_codes"]["codes"].pop("SW31")
    assert any("SW31" in problem for problem in extractor.sanity_check(data))


def test_a_long_run_of_missing_codes_is_reported():
    """Eén gat is de code; een reeks gaten is een leesfout."""
    data = complete()
    for number in range(10, 20):
        data["segregation_codes"]["codes"].pop(f"SG{number}")
    assert any("SG10" in problem for problem in extractor.sanity_check(data))


@pytest.mark.parametrize("text", ["", "x"])
def test_a_suspiciously_short_description_is_reported(text):
    data = complete()
    data["stowage_codes"]["codes"]["SW7"] = text
    assert any("SW7" in problem for problem in extractor.sanity_check(data))


# --- Het patroon dat de Dangerous Goods List moet vinden ---------------------
#
# Dit patroon is twee keer stukgegaan op dezelfde manier: een `^` zonder
# re.MULTILINE, waardoor alleen het begin van de héle paginatekst matchte. De
# tweede keer kwam er nog bij dat `re.M` als tweede argument aan finditer van
# een gecompileerd patroon geen vlag is maar `pos` — het zoeken sloeg dan ook
# nog de eerste acht tekens over. Beide keren was de uitkomst "niets gevonden"
# terwijl de gegevens er wel stonden. Dat is de gevaarlijkste soort fout hier,
# dus hij staat vast.

_PROBE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "probe_dg_sources.py"
_probe_spec = importlib.util.spec_from_file_location("probe_dg_sources", _PROBE_PATH)
probe = importlib.util.module_from_spec(_probe_spec)
sys.modules[_probe_spec.name] = probe
_probe_spec.loader.exec_module(probe)

# Zoals de PDF een lijstpagina uitlevert: elke cel op een eigen regel.
DGL_PAGE = """Chapter 3.1 – General
13
IMDG Code (Amendment 42-24)  2024 EDITION
0135\t
Mercury fulminate, wetted with not less than 20% water
1347\t
Silver picrate, wetted with not less than 30% water, by mass
1389\t
Alkali metal amalgam, liquid
MSC 108/20/Add.2
Annex 8, page 579
"""


def test_the_row_pattern_matches_lines_below_the_first():
    """De bug: zonder re.MULTILINE matcht ^ alleen het begin van de tekst."""
    found = [m.group(1) for m in probe.DGL_ROW.finditer(DGL_PAGE)]
    assert found == ["0135", "1347", "1389"]


def test_the_row_pattern_carries_the_multiline_flag():
    assert probe.DGL_ROW.flags & re.MULTILINE


def test_the_row_pattern_ignores_a_number_inside_a_line():
    """'not less than 20% water' mag geen rij worden, en '13' evenmin: het
    paginanummer is drie cijfers te kort en staat los."""
    found = [m.group(1) for m in probe.DGL_ROW.finditer(DGL_PAGE)]
    assert "2024" not in found  # staat midden in de voettekst
    assert all(len(un) == 4 for un in found)
