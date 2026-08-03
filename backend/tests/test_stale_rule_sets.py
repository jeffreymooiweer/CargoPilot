"""Rekent de app met een verlopen regelset, dan hoort zij dat te zeggen.

Het manifest wist sinds v1.26.0 al dat de IATA DGR op 31 december 2026 afloopt,
maar zei het alleen tegen wie `/api/regulatory` opvroeg. Een gebruiker die in
2027 een luchtvrachtverklaring maakt, zag niets.

Het verschil dat deze tests bewaken zit tussen "verlopen" en "verlopen én
vervangen". De UN-kaarten van 41-22 zijn verlopen, maar kolom 16a en 16b komen
sinds v1.23.0 uit de lijst van 42-24 en wat de kaarten nog leveren is niet met
de editie meeveranderd. Daar bij élke controle over waarschuwen zou het
waarschuwen zelf waardeloos maken: wie elke keer een melding wegklikt, klikt
straks ook de melding weg die er wél toe doet.
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
    """De UN-kaarten zijn verlopen en dat is bekend en opgevangen."""
    assert "imdg_un_cards" in expired_rule_sets(date(2026, 8, 3))
    assert stale_rule_sets(["IMDG"], date(2026, 8, 3)) == []


def test_an_expired_rule_set_with_nothing_in_its_place_does_warn():
    stale = stale_rule_sets(["IATA"], date(2027, 1, 1))
    assert [item["key"] for item in stale] == ["iata"]
    assert stale[0]["expired_on"] == "2026-12-31"


def test_a_warning_only_reaches_the_profiles_that_lean_on_it():
    """Wie over de weg vervoert heeft niets aan een melding over luchtvracht."""
    assert stale_rule_sets(["ADR"], date(2027, 1, 1)) == []
    assert stale_rule_sets(["IATA"], date(2027, 1, 1))


def test_today_nothing_is_reported_at_all():
    """Stilte is hier de juiste uitkomst; alles wat geldt is geldig."""
    assert stale_rule_sets(["ADR", "IMDG", "IATA"]) == []


# --- Wat de controle ermee doet -------------------------------------------------

def test_the_compliance_result_carries_the_manifest_it_computed_with():
    """Een bugmelding kan hiermee zeggen waar die installatie mee rekende."""
    result = check_compliance(ENTRIES, ["IATA"], "nl")
    manifest = result["regulatory_manifest"]
    assert manifest["manifest_id"]
    assert manifest["editions"]["iata"].startswith("67")


def test_no_rule_set_warning_appears_while_everything_is_current():
    result = check_compliance(ENTRIES, ["ADR", "IMDG", "IATA"], "nl")
    assert not result.get("rule_set_warnings")


def test_the_warning_says_what_expired_and_when(monkeypatch):
    """De melding moet bruikbaar zijn zonder de documentatie erbij."""
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


# --- Wat er op het document terechtkomt -----------------------------------------

def test_an_expired_rule_set_reaches_the_export(monkeypatch):
    """Een document overleeft de sessie waarin het is gemaakt; het scherm niet.

    Daarom hoort deze melding op de export en niet alleen in de wizard.
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
    """Verlopen is geen verbod. De zending mag doorgaan, mits iemand de
    actuele uitgave erbij pakt — tegenhouden zou de gebruiker dwingen om de
    controle te omzeilen."""
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
