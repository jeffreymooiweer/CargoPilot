"""If the app computes with an expired rule set, it should say so.

The manifest has known since v1.26.0 that the IATA DGR runs out on 31 December
2026, but said it only to whoever asked `/api/regulatory`. A user making an air
freight declaration in 2027 saw nothing.

The difference these tests guard sits between "expired" and "expired *and*
replaced". The 41-22 UN cards have expired, but columns 16a and 16b have come
from the 42-24 list since v1.23.0 and what the cards still supply did not change
with the edition. Warning about that on *every* check would make the warning
itself worthless: whoever dismisses a message every time will dismiss the one
that matters too.
"""

from datetime import date

from app.services.dg.compliance import check_compliance
from app.services.documents.exporter import validate_document
from app.services.documents.registry import get_document
from app.services.regulatory_manifest import expired_rule_sets, stale_rule_sets
from tests.test_documents import BASE_VALUES, LINES

ENTRIES = [{
    "line_id": 1,
    "vehicle": "COLLO-1",
    "products": [{
        "un_number": "1203",
        "proper_shipping_name": "BENZINE",
        "class": "3",
        "packing_group": "II",
        "quantity_packages": "1",
    }],
}]


def test_an_expired_but_superseded_rule_set_does_not_warn():
    """The UN cards have expired and that is known and accounted for."""
    assert "imdg_un_cards" in expired_rule_sets(date(2026, 8, 3))
    assert stale_rule_sets(["IMDG"], date(2026, 8, 3)) == []


def test_an_expired_rule_set_with_nothing_in_its_place_does_warn():
    stale = stale_rule_sets(["IATA"], date(2027, 1, 1))
    assert [item["key"] for item in stale] == ["iata"]
    assert stale[0]["expired_on"] == "2026-12-31"


def test_a_warning_only_reaches_the_profiles_that_lean_on_it():
    """Whoever carries by road has no use for a message about air freight."""
    assert stale_rule_sets(["ADR"], date(2027, 1, 1)) == []
    assert stale_rule_sets(["IATA"], date(2027, 1, 1))


def test_today_nothing_is_reported_at_all():
    """Silence is the right outcome here; everything that applies is valid."""
    assert stale_rule_sets(["ADR", "IMDG", "IATA"]) == []


# --- Wat de controle ermee doet -------------------------------------------------

def test_the_compliance_result_carries_the_manifest_it_computed_with():
    """A bug report can use this to say what that installation computed with."""
    result = check_compliance(ENTRIES, ["IATA"], "nl")
    manifest = result["regulatory_manifest"]
    assert manifest["manifest_id"]
    assert manifest["editions"]["iata"].startswith("67")


def test_no_rule_set_warning_appears_while_everything_is_current():
    result = check_compliance(ENTRIES, ["ADR", "IMDG", "IATA"], "nl")
    assert not result.get("rule_set_warnings")


def test_the_warning_says_what_expired_and_when(monkeypatch):
    """The message has to be usable without the documentation alongside."""
    monkeypatch.setattr(
        "app.services.dg.compliance.stale_rule_sets",
        lambda profiles=None, today=None: [{
            "key": "iata",
            "name": "IATA DGR — luchtvracht",
            "edition": "67e editie (2026)",
            "expired_on": "2026-12-31",
            "profiles": ["IATA"],
        }],
    )
    result = check_compliance(ENTRIES, ["IATA"], "nl")
    warning = result["rule_set_warnings"][0]
    assert warning["severity"] == "warning"
    assert "67e editie" in warning["message"]
    assert "2026-12-31" in warning["message"]


def test_the_warning_is_translated(monkeypatch):
    monkeypatch.setattr(
        "app.services.dg.compliance.stale_rule_sets",
        lambda profiles=None, today=None: [{
            "key": "iata", "name": "IATA DGR", "edition": "67th edition (2026)",
            "expired_on": "2026-12-31", "profiles": ["IATA"],
        }],
    )
    result = check_compliance(ENTRIES, ["IATA"], "en")
    assert "expired on" in result["rule_set_warnings"][0]["message"]


# --- What ends up on the document -----------------------------------------------

def test_an_expired_rule_set_reaches_the_export(monkeypatch):
    """A document outlives the session it was made in; the screen does not.

    That is why this message belongs on the export and not only in the wizard.
    """
    monkeypatch.setattr(
        "app.services.dg.compliance.stale_rule_sets",
        lambda profiles=None, today=None: [{
            "key": "iata", "name": "IATA DGR — luchtvracht",
            "edition": "67e editie (2026)", "expired_on": "2026-12-31",
            "profiles": ["IATA"],
        }],
    )
    _errors, warnings = validate_document(
        get_document("cmr"), BASE_VALUES, LINES, ENTRIES, "ADR"
    )
    assert any("67e editie" in w for w in warnings), warnings


def test_an_expired_rule_set_does_not_block_the_export(monkeypatch):
    """Expired is not forbidden. The consignment may go ahead, provided somebody
    picks up the current edition — stopping it would force the user to work
    around the check."""
    monkeypatch.setattr(
        "app.services.dg.compliance.stale_rule_sets",
        lambda profiles=None, today=None: [{
            "key": "iata", "name": "IATA DGR", "edition": "67e editie (2026)",
            "expired_on": "2026-12-31", "profiles": ["IATA"],
        }],
    )
    errors, _warnings = validate_document(
        get_document("cmr"), BASE_VALUES, LINES, ENTRIES, "ADR"
    )
    assert not any("editie" in e for e in errors), errors
