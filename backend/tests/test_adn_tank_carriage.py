"""May these goods travel that way on the water — and does the application say so?

The road got this answer in v1.66.0. The water did not, and the gap had a shape
worth naming: every ADN check in the compliance layer implements **chapter 7.1**,
which is the ADN's chapter for dry cargo vessels. A consignment declared as a
cargo tank was measured against that chapter anyway — separation in the holds,
blue cones off table A, the exemption of 1.1.3.6.1 — and came back with answers
that looked exactly like answers.

Column (8) of the ADN's table A is where the regulation says which way is open,
and it is a short list: empty means carriage in packages only, ``B`` adds bulk
and points at 7.1.1.11, ``T`` adds tank vessels and points at 7.2.1.21, where
table C takes over. Two further provisions fix what the modes mean here:

- **7.1.1.21** forbids carriage in cargo tanks on a dry cargo vessel, so a cargo
  tank load is a tank vessel and belongs to chapter 7.2.
- **7.1.1.18** goes the other way for tank containers and portable tanks: their
  carriage must meet the requirements for carriage of packages, so they sail on
  a dry cargo vessel and chapter 7.1 is the right chapter for them.

That second one is why this file spends as much space on what did *not* change.
Withholding an answer is safe when the chapter really does not apply and costly
when it does, and a check that treated a tank container like a cargo tank would
take away the cone count, the hold separation and the exemption for a carriage
that is entitled to all three.

Table C itself entered the repository in v1.73.0, read twice. Where column (8)
permits a tank vessel the admission now names the vessel type of column (6) —
or the variants, where the type is a property of the variant — and the signals
come from column (19) under 7.2.5. What is still not checked is the vessel
itself, and the conditions note says so.
"""

import json
from pathlib import Path

import pytest

from app.services.dg.compliance import (
    check_adn_carriage_admission,
    check_adn_exemption,
    check_adn_hold_separation,
    check_adn_signals,
    check_compliance,
)

CONFIG = Path(__file__).resolve().parents[1] / "app" / "config" / "dg_compliance.json"
LANGUAGES = ("nl", "en", "de", "fr")


def line(*products):
    return [{"line_id": "L1", "products": list(products)}]


def product(un, mode=None, **extra):
    row = {"un_number": un, "adr_total_quantity": 100, **extra}
    if mode:
        row["carriage_mode"] = mode
    return row


def admission(un, mode, language="en"):
    return check_adn_carriage_admission(line(product(un, mode)), language)


# --- column (8) itself -----------------------------------------------------


def test_de_kolom_zwijgt_over_colli():
    """A packages consignment asks no admission question, and getting a card
    about it would only teach that the card means something."""
    assert admission("1203", "packages")["status"] == "not_checked"
    assert admission("1203", None)["status"] == "not_checked"


def test_los_gestort_vereist_de_code_b():
    """UN 1942 carries B; UN 1202 does not, and the reason is physical — gas oil
    is a liquid and a liquid in bulk on the water is a tank vessel."""
    assert admission("1942", "bulk")["status"] == "ok"

    refused = admission("1202", "bulk")
    assert refused["status"] == "not_permitted"
    assert refused["items"][0]["permitted"] is False
    assert refused["items"][0]["provision"] == "7.1.1.11"


def test_het_tankschip_vereist_de_code_t():
    permitted = admission("1203", "tank")
    assert permitted["status"] == "ok"
    assert permitted["items"][0]["provision"] == "7.2.1.21"

    refused = admission("0004", "tank")
    assert refused["status"] == "not_permitted"
    assert refused["items"][0]["provision"] == "7.1.1.21"


def test_geen_enkele_ontplofbare_stof_gaat_in_een_ladingtank():
    """Class 1 has column (8) empty throughout, which is the regulation saying
    packages and nothing else. One case would pass by luck; the sweep is the
    point."""
    entries = json.loads(
        (Path(__file__).resolve().parents[1] / "seed" / "dg" / "adn_table_a.json")
        .read_text(encoding="utf-8"))["entries"]
    class1 = [row for row in entries if row["class"] == "1"]
    assert len(class1) > 100
    assert all(not row["carriage_permitted"] for row in class1)


def test_de_tabel_c_spreekt_nu_zelf():
    """v1.71.0 could only admit to not having read table C. The table is in
    the repository now, with two readings, and the admission names what the
    row settles: petrol's six variants split between vessel types N and C, so
    the type is a property of the variant and the message says so."""
    permitted = admission("1203", "tank")
    item = permitted["items"][0]
    assert item["vessel_types"] == ["C", "N"]
    assert "6" in item["vessel_message"]

    # Anhydrous ammonia has one row and one answer.
    single = admission("1005", "tank")
    assert single["items"][0]["vessel_type"] == "G"

    # What is still not checked is the vessel itself, and the note says that
    # instead of claiming the table is absent.
    assert "conditions_note" in permitted
    assert "not_assessed" not in permitted
    assert "conditions_note" not in admission("1942", "bulk")


def test_geen_rij_rust_nog_op_een_lezing():
    """UN 1977 is genuinely in table C — the UNECE edition prints it — but the
    Dutch export omits it. It rested on one reading until the French edition
    was read as the third; it now has two, and the warning that used to name it
    is silent. The seed's own record says the same, and the two are pinned
    together: the day an edition brings a one-reading row back, this fails and
    the warning has to be looked at again."""
    import json
    from pathlib import Path
    seed = json.loads((Path(__file__).resolve().parents[1] / "seed" / "dg"
                       / "adn_table_c.json").read_text(encoding="utf-8"))
    assert seed["cross_check"]["rows_read_once"] == 0

    result = admission("1977", "tank")
    assert result["items"][0]["permitted"] is True
    assert "single_reading_note" not in result
    assert "single_reading_note" not in admission("1005", "tank")


# --- 7.1.1.18: a tank container is not a cargo tank -------------------------


def test_de_tankcontainer_vaart_als_colli_mee():
    result = admission("1203", "portable_tank")
    assert result["status"] == "ok"
    assert result["items"][0]["provision"] == "7.1.1.18"


def test_de_tankcontainer_houdt_zijn_kegels_en_zijn_afstanden():
    """The whole risk of this release is taking answers away from a carriage
    that is entitled to them. 7.1.1.18 puts a tank container under the
    requirements for packages, so chapter 7.1 keeps answering for it."""
    # Pinned against the packages answer rather than against a literal, so this
    # says the one thing meant: the mode changed nothing. (UN 1203's own cone
    # count is unsettled in column (12), which is a different silence and one
    # this release must leave exactly as it was.)
    for check in (check_adn_signals, check_adn_hold_separation):
        assert (check(line(product("1203", "portable_tank")), "en")
                == check(line(product("1203", "packages")), "en"))
        assert (check(line(product("1263", "portable_tank")), "en")
                == check(line(product("1263", "packages")), "en"))


# --- chapter 7.1 is for dry cargo vessels ----------------------------------


def test_hoofdstuk_71_zwijgt_over_ladingtanks():
    result = check_adn_hold_separation(line(product("1203", "tank")), "en")
    assert result["status"] == "not_available_for_mode"
    assert "chapter 7.2" in result["mode_note"]
    assert "UN 1203" in result["mode_note"]


def test_de_seinvoering_komt_nu_uit_tabel_c():
    """v1.71.0 withheld the cones for a cargo tank load because table A is not
    the tank vessel's table. Table C is, and its column (19) settles petrol at
    one cone across all six variant rows — so the answer exists again, under
    the tank vessel's own provision."""
    result = check_adn_signals(line(product("1203", "tank")), "en")
    assert result["status"] == "ok"
    assert result["provision"] == "7.2.5.0.1"
    assert result["cones"] == 1


def test_de_zwaarste_seinvoering_wint_op_een_tankschip():
    """7.2.5.0.2 ranks the options: two blue cones or lights before one.
    Ammonia (2 cones) sets the signals over molten sulphur (0)."""
    entries = line(product("1005", "tank"), product("2448", "tank"))
    result = check_adn_signals(entries, "en")
    assert result["cones"] == 2
    assert result["set_by"] == ["UN 1005"]
    assert "7.2.5.0.2" in result["highest_wins"]


def test_gemengde_wijzen_krijgen_geen_tankantwoord():
    """A consignment mixing cargo tanks with packages is not one vessel under
    either chapter, and inventing a vessel to answer for would be worse than
    the honest note."""
    entries = line(product("1203", "tank"), product("1263", "packages"))
    result = check_adn_signals(entries, "en")
    assert result["status"] == "not_available_for_mode"


def test_een_gemengde_lading_valt_ook_buiten_71():
    """A vessel is one vessel. If any position travels in a cargo tank it is not
    a dry cargo vessel, and 7.1.4.3 has nothing to say about its holds."""
    entries = line(product("1203", "tank"), product("1263", "packages"))
    assert check_adn_hold_separation(entries, "en")["status"] == "not_available_for_mode"


# --- 1.1.3.6.1 is for carriage in packages ---------------------------------


@pytest.mark.parametrize("mode", ["tank", "portable_tank", "bulk"])
def test_de_vrijstelling_geldt_alleen_voor_colli(mode):
    """The note under this result has said "carriage in tanks is never exempt"
    since v1.32.0 while the arithmetic granted the exemption anyway. A sentence
    to the reader is not a rule."""
    result = check_adn_exemption(line(product("1942", mode, **{"class": "5.1"})), "en")
    assert result["status"] == "not_available_for_mode"
    assert "in packages" in result["mode_note"]


def test_colli_houden_hun_vrijstelling():
    result = check_adn_exemption(
        line(product("1942", "packages", **{"class": "5.1"})), "en")
    assert result["status"] == "exempt_possible"
    assert "mode_note" not in result


# --- through the whole result ----------------------------------------------


def test_de_uitkomst_bereikt_het_paneel():
    result = check_compliance(
        [{"position": 1, "products": [product("1202", "bulk", **{"class": "3"})]}],
        ["ADN"], "en")
    assert result["adn_carriage_admission"]["status"] == "not_permitted"
    assert result["adn_exemption"]["status"] == "not_available_for_mode"


def test_colli_krijgen_geen_extra_kaart():
    result = check_compliance(
        [{"position": 1, "products": [product("1203", "packages", **{"class": "3"})]}],
        ["ADN"], "en")
    assert "adn_carriage_admission" not in result


# --- the wording, in four languages ----------------------------------------


def test_elke_melding_bestaat_in_vier_talen():
    block = json.loads(CONFIG.read_text(encoding="utf-8"))["adn_carriage_admission"]
    messages = [value for key, value in block.items()
                if isinstance(value, dict) and not key.startswith("_")]
    assert len(messages) == 12
    for message in messages:
        assert set(message) == set(LANGUAGES)
        assert all(message[language].strip() for language in LANGUAGES)


@pytest.mark.parametrize("language", LANGUAGES)
def test_de_melding_noemt_de_positie(language):
    result = admission("1202", "bulk", language)
    assert "UN 1202" in result["items"][0]["message"]
