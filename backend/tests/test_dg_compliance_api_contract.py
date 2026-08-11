"""Integration tests for the profile contract between wizard, API and engine.

These tests deliberately go through FastAPI's request validation. Unit tests of
``check_compliance`` cannot catch a profile name that the frontend sends but
Pydantic rejects, or a profile accepted by Pydantic that the engine ignores.
"""
from copy import deepcopy
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app


def _user():
    return SimpleNamespace(id=1, username="test", role="admin", active=True)


def _payload(profiles: list[str]) -> dict:
    return {
        "entries": [
            {
                "line_id": "1",
                "vehicle": "COLLO-1",
                "products": [
                    {
                        "un_number": "1263",
                        "proper_shipping_name": "PAINT",
                        "class": "3",
                        "packing_group": "II",
                        "q_net_quantity": "1",
                        "q_max_net_quantity": "5",
                    },
                    {
                        "un_number": "1866",
                        "proper_shipping_name": "RESIN SOLUTION",
                        "class": "3",
                        "packing_group": "II",
                        "q_net_quantity": "1",
                        "q_max_net_quantity": "5",
                    },
                ],
            }
        ],
        "profiles": profiles,
        "language": "en",
    }


def _post(payload: dict):
    app.dependency_overrides[get_current_user] = _user
    try:
        with TestClient(app) as client:
            return client.post("/api/dg/compliance", json=payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_the_exact_air_wizard_profile_reaches_the_iata_engine():
    response = _post(_payload(["IATA_DGR"]))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profiles"] == ["IATA_DGR"]
    assert "iata_segregation" in body
    assert body["q_values"][0]["status"] == "ok"
    assert body["q_check_status"]["status"] == "checked"
    assert "67th edition (2026)" in body["regulatory_manifest"]["editions"]["iata"]


def test_the_exact_multimodal_wizard_profiles_are_accepted():
    response = _post(_payload(["ADR", "IATA_DGR", "IMDG"]))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profiles"] == ["ADR", "IATA_DGR", "IMDG"]
    assert "adr_points" in body
    assert "imdg_segregation" in body
    assert "iata_segregation" in body
    assert "q_values" in body


def test_the_old_iata_alias_is_normalised_for_existing_clients():
    response = _post(_payload(["IATA"]))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profiles"] == ["IATA_DGR"]
    assert "iata_segregation" in body
    assert "q_values" in body


def test_missing_q_input_is_reported_instead_of_looking_passed():
    payload = deepcopy(_payload(["IATA_DGR"]))
    for product in payload["entries"][0]["products"]:
        product.pop("q_net_quantity")
        product.pop("q_max_net_quantity")

    response = _post(payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["q_check_status"]["status"] == "not_checked"
    findings = body["iata_segregation"]
    assert any(finding["rule"] == "IATA DGR 5.0.2.11 — Q" for finding in findings)
    assert any(finding["severity"] == "warning" for finding in findings)


def test_an_unknown_profile_is_rejected_instead_of_skipping_checks():
    response = _post(_payload(["IDMG"]))

    assert response.status_code == 422


def test_the_numeric_line_id_of_the_wizard_is_accepted():
    """buildDgEntries sends line_id as a number; that must not give a 422.

    Since the schemas of v1.30.0, 'line_id: 1' was refused and every live check
    from the wizard failed before anything was computed.
    """
    payload = deepcopy(_payload(["ADR"]))
    payload["entries"][0]["line_id"] = 1

    response = _post(payload)

    assert response.status_code == 200, response.text
    assert "adr_points" in response.json()
