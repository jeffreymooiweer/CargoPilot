"""Two explosives in one consignment gave a server error instead of an answer.

Reported behaviour: a consignment with two class 1 packages — detonators
(compatibility group B) next to an explosive (group D), which is an everyday
combination — produced no compliance result but an error. Both the panel in the
wizard and the export run through `check_compliance`, so no document came out
either.

The cause sat on the seam, as it often does here. In v1.38.0 `class1_products`
went from a list of labels to a list of tuples `(label, UN number)`, because the
footnotes of 7.5.2.1 need the UN number. The message of 7.5.2.2 a few lines
further on kept doing `", ".join(class1_products)` and was offered tuples from
that moment on: `TypeError`. Not a single test noticed, and that is where the
second defect sits.

Because why did nobody notice? Because the group was read from the *class field*
with a tight anchor (`^1\\.\\d([A-S])$`), and ADR Table A puts only "1" in the
class column for explosives — the division with its compatibility group is in the
classification code. For every row that comes straight from the seed, that check
therefore never found a group, 7.5.2.2 never fired, and the broken line stayed
unreachable. A check that did not run looked like a check with nothing to report.

Two defects covering for each other: the silent one masked the loud one. That is
why they are in one file, and why there is a sweep at the bottom that does not
look at any specific rule but only demands that no consignment can make the check
stumble.

Measured on the real data before the repair: 344 out of 4,000 random consignments
of two to five UN numbers ended in an exception (8.6%).
"""

import json
import random
from pathlib import Path

import pytest

from app.services.dg.autofill import derive_product
from app.services.dg.compliance import check_adr_mixed_loading, check_compliance

# UN 0027 black powder is 1.1D, UN 0029 detonators are 1.1B. Loading them
# together is allowed only as far as table 7.5.2.2 permits — the question the
# application has to ask instead of breaking on it.
BLACK_POWDER = {
    "un_number": "0027",
    "proper_shipping_name": "BLACK POWDER",
    "class": "1.1D",
    "classification_code": "1.1D",
}
DETONATORS = {
    "un_number": "0029",
    "proper_shipping_name": "DETONATORS, NON-ELECTRIC",
    "class": "1.1B",
    "classification_code": "1.1B",
}
# As Table A actually delivers it: class "1", group in the classification code.
DETONATORS_TABLE_A = dict(DETONATORS, **{"class": "1"})


def load(*products, language="nl"):
    return check_adr_mixed_loading([{"line_id": "L1", "products": list(products)}], language)


def compat_warnings(warnings):
    return [w for w in warnings if w["rule"].startswith("ADR 7.5.2.2")]


def test_twee_compatibiliteitsgroepen_geven_een_antwoord_en_geen_fout():
    """The crash itself: until v1.40.1 this raised `TypeError` instead of reporting.

    Since v1.41.0 the table is actually read, so what comes out is the cell B × D
    — footnote (a) — and no longer the question handed back.
    """
    found = compat_warnings(load(BLACK_POWDER, DETONATORS))

    assert len(found) == 1
    assert found[0]["rule"] == "ADR 7.5.2.2 (B × D) (a)"
    assert found[0]["severity"] == "warning"


def test_de_melding_noemt_de_betrokken_colli():
    """`products` carried tuples; what the user is looking for is which packages
    are concerned."""
    found = compat_warnings(load(BLACK_POWDER, DETONATORS))[0]

    assert found["products"] == "UN 0029 DETONATORS, NON-ELECTRIC, UN 0027 BLACK POWDER"


def test_de_groep_komt_uit_de_classificatiecode_niet_uit_de_klassekolom():
    """Table A says "1" in the class column; the group is in the classification code.

    This is the silent defect. As long as the group was read from the class field
    only, 7.5.2.2 never fired on real seed data — and the crash above was never
    reached.
    """
    found = compat_warnings(load(BLACK_POWDER, DETONATORS_TABLE_A))

    assert len(found) == 1
    assert found[0]["rule"] == "ADR 7.5.2.2 (B × D) (a)"


def test_een_enkele_groep_geeft_geen_melding():
    """7.5.2.2 is about *different* groups; twice D is nothing to worry about."""
    assert compat_warnings(load(BLACK_POWDER, dict(BLACK_POWDER, un_number="0028"))) == []


def test_klasse_1_naast_klasse_1_met_nevengevaar_laat_de_zeecontrole_staan():
    """IMDG 7.2.4: a "*" refers on to 7.2.7 and must not displace a digit.

    For class 1 against class 1 the table gives a "*". If that came first, the
    next cell compared `int(value) > int("*")` and the check fell over. UN 0018
    carries subsidiary risks 6.1 and 8, so a second class 1 package produces
    exactly that order: first the "*", then a digit.
    """
    entries = [{"line_id": "L1", "products": [
        {"un_number": "0018", "class": "1.2G", "classification_code": "1.2G",
         "subsidiary_risks": "6.1+8", "proper_shipping_name": "AMMUNITION, TOXIC"},
        {"un_number": "0183", "class": "1.1D", "classification_code": "1.1D",
         "proper_shipping_name": "ROCKETS, INERT HEAD"},
    ]}]

    findings = check_compliance(entries, ["IMDG"], "nl")["imdg_segregation"]

    table = [f for f in findings if f["rule"].startswith("IMDG 7.2.4")]
    assert table, "de klassescheidingstabel hoort een uitspraak te doen"
    # The digit beats the "*": 4 is "separated longitudinally by an intervening
    # complete compartment or hold from".
    assert table[0]["code"] == "4"


def _seed_un_numbers() -> list[str]:
    seed = Path(__file__).resolve().parents[1] / "seed" / "dg" / "un_numbers.json"
    return sorted({str(row["un"]) for row in json.loads(seed.read_text(encoding="utf-8"))})


@pytest.mark.parametrize("profile", ["ADR", "RID", "ADN", "IMDG", "IATA_DGR"])
def test_geen_enkele_zending_laat_de_nalevingscontrole_struikelen(profile):
    """A sweep over the real data, along the path the wizard also takes.

    Both defects above were found this way and not by reading. They can also only
    be found this way: on the bare seed row the class column says "1" and nothing
    happens; only *after* `derive_product` — what the interface fills in as soon
    as somebody picks a UN number — does the product carry the division.

    Seeded with a fixed value, so that a fault of today is the same fault
    tomorrow.
    """
    uns = _seed_un_numbers()
    rng = random.Random(20260808)
    cache: dict[str, dict] = {}

    def product(un: str) -> dict:
        if un not in cache:
            base = {
                "un_number": un,
                "net_mass_liters_per_package": "5 kg",
                "quantity_packages": "3",
                "gross_mass": "40 kg",
            }
            base.update(derive_product(base, "nl", [profile]).get("patch", {}))
            cache[un] = base
        return dict(cache[un])

    for _ in range(300):
        picks = rng.sample(uns, rng.choice([2, 3, 4, 5]))
        entries = [{"line_id": "L1", "products": [product(un) for un in picks]}]
        try:
            check_compliance(entries, [profile], "nl")
        except Exception as exc:  # pragma: no cover - de melding ís de test
            pytest.fail(f"{profile} viel om op {picks}: {type(exc).__name__}: {exc}")
