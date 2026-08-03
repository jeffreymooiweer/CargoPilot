"""Het manifest moet kloppen met wat de app werkelijk gebruikt.

Een manifest dat losstaat van de gegevens is erger dan geen manifest: het wekt
vertrouwen dat nergens op steunt. Deze tests binden het aan de seeds die er
echt zijn, en leggen vast dat een verlopen editie zichtbaar wordt in plaats van
stilletjes door te rekenen.
"""

from datetime import date

import pytest

from app.services.regulatory_manifest import (
    RULE_SETS,
    build_manifest,
    expired_rule_sets,
    rule_set_status,
    summary,
)


def rule_set(key: str) -> dict:
    return next(r for r in RULE_SETS if r["key"] == key)


def test_every_rule_set_names_its_edition_and_where_it_came_from():
    for entry in RULE_SETS:
        assert entry["edition"], entry["key"]
        assert entry["source"], entry["key"]
        assert entry["valid_from"], entry["key"]
        assert entry["covers"], entry["key"]


def test_every_file_a_rule_set_claims_actually_exists():
    """Een controlesom over een bestand dat er niet is, is geen controle."""
    manifest = build_manifest()
    for entry, reported in zip(RULE_SETS, manifest["rule_sets"]):
        assert len(reported["datasets"]) == len(entry["files"]), entry["key"]


def test_the_checksum_covers_the_content_and_not_the_timestamp():
    """Twee installaties met dezelfde gegevens moeten hetzelfde id melden;
    een build-tijdstempel zou ze verschillend laten lijken."""
    assert build_manifest()["manifest_id"] == build_manifest()["manifest_id"]


def test_the_dangerous_goods_list_is_the_edition_the_manifest_claims():
    """Het manifest en het gegevensbestand mogen niet uit elkaar lopen."""
    from app.services.dg import dangerous_goods_list as dgl

    assert dgl.source()["amendment"] == "42-24"
    assert "42-24" in rule_set("imdg")["edition"]


def test_the_iata_edition_matches_the_compliance_rules():
    """De regels citeren hun editie in de tekst; die moet dezelfde zijn."""
    from app.services.dg.compliance import get_compliance_rules

    sources = get_compliance_rules()["sources"]
    assert any("67" in str(v) for v in sources.values())
    assert "67" in rule_set("iata")["edition"]


# --- Geldigheid ----------------------------------------------------------------

def test_a_rule_set_is_current_between_its_dates():
    entry = {"valid_from": "2026-01-01", "valid_until": "2026-12-31"}
    assert rule_set_status(entry, date(2026, 6, 1)) == "current"


def test_a_rule_set_that_has_not_started_says_so():
    entry = {"valid_from": "2027-01-01", "valid_until": None}
    assert rule_set_status(entry, date(2026, 8, 3)) == "not_yet_in_force"


def test_an_expired_rule_set_is_reported_rather_than_used_quietly():
    """De IATA DGR wordt jaarlijks vervangen. Op 1 januari 2027 rekent deze
    app met een verlopen editie; dat hoort zichtbaar te zijn."""
    assert rule_set_status(rule_set("iata"), date(2026, 12, 31)) == "current"
    assert rule_set_status(rule_set("iata"), date(2027, 1, 1)) == "expired"
    assert "iata" in expired_rule_sets(date(2027, 1, 1))


def test_a_circular_without_an_end_date_never_expires():
    """De EmS Guide is een circulaire: zij geldt tot er een Rev.4 komt, niet
    tot een datum."""
    assert rule_set("ems")["valid_until"] is None
    assert rule_set_status(rule_set("ems"), date(2099, 1, 1)) == "current"


def test_the_un_cards_are_openly_marked_as_superseded():
    """41-22 liep eind 2025 af en de kaarten worden nog maar voor twee dingen
    gebruikt. Dat verzwijgen zou de indruk wekken dat alles 42-24 is."""
    cards = rule_set("imdg_un_cards")
    assert rule_set_status(cards, date(2026, 8, 3)) == "expired"
    assert any("16a" in note for note in cards["errata"])
    assert any("2984" in note for note in cards["errata"])


# --- Wat de endpoints uitdragen -------------------------------------------------

def test_the_summary_is_small_enough_for_the_health_endpoint():
    compact = summary()
    assert set(compact) == {"manifest_id", "editions", "expired"}
    assert len(str(compact)) < 800


def test_the_summary_and_the_full_manifest_agree():
    today = date(2026, 8, 3)
    assert summary(today)["manifest_id"] == build_manifest(today)["manifest_id"]
    assert summary(today)["expired"] == expired_rule_sets(today)


def test_the_manifest_carries_the_application_version():
    from app.version import get_version

    assert build_manifest()["application_version"] == get_version()


def test_the_manifest_repeats_that_the_published_code_is_what_counts():
    assert "leidend" in build_manifest()["disclaimer"]


@pytest.mark.parametrize("key", [entry["key"] for entry in RULE_SETS])
def test_no_rule_set_key_is_duplicated(key):
    assert [entry["key"] for entry in RULE_SETS].count(key) == 1
