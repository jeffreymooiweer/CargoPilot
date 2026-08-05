"""De LQ/EQ-toets van hoofdstuk 3.4 en 3.5.

De LQ-waarde (kolom 7a) en de E-code (kolom 7b) stonden al jaren in de data en
werden getoond met hun betekenis, maar nooit vergeleken met wat er is
ingevuld. Deze tests leggen die vergelijking vast: de grenswaarden zelf zijn
geverifieerd tegen ADR 3.4.2/3.4.3 (30 kg bruto, 20 kg voor folietrays),
tabel 3.5.1.2 (E-codes) en 3.5.5 (ten hoogste 1000 colli).

Even belangrijk is wat de toets níét doet: een regel binnen de grenzen wordt
gemeld, maar verdwijnt nooit uit de 1.1.3.6-puntentelling — kwalificeren op
hoeveelheid is niet hetzelfde als vrijgesteld zijn.
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.dg.compliance import check_compliance, check_lq_eq


def _entry(products: list[dict]) -> list[dict]:
    return [{"vehicle": "TRAILER-1", "line_id": "1", "products": products}]


def _product(**overrides) -> dict:
    base = {
        "un_number": "1263",
        "proper_shipping_name": "PAINT",
        "class": "3",
        "packing_group": "II",
        "limited_quantity": "5 L",
        "excepted_quantity": "E2",
    }
    base.update(overrides)
    return base


def _single(result: dict) -> dict:
    assert len(result["rows"]) == 1
    return result["rows"][0]


# --- LQ (3.4) -----------------------------------------------------------


def test_lq_within_limits_names_both_boundaries():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="0,5 L",
                         gross_mass_per_package="20 kg")]),
        language="nl", profiles=["ADR"],
    )
    row = _single(result)
    assert row["lq"]["status"] == "within_limits"
    assert "5 L" in row["lq"]["message"]
    assert "30 kg" in row["lq"]["message"]
    # De vrijstelling haalt de regel niet uit de puntentelling.
    assert "1.1.3.6.5" in row["lq"]["message"]
    assert result["status"] == "checked"


def test_lq_points_note_is_absent_without_a_land_profile():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="0,5 L",
                         gross_mass_per_package="20 kg")]),
        language="nl", profiles=["IMDG"],
    )
    row = _single(result)
    assert row["lq"]["status"] == "within_limits"
    assert "1.1.3.6.5" not in row["lq"]["message"]


def test_lq_inner_packaging_above_the_column_7a_limit():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="6 L",
                         gross_mass_per_package="20 kg")]),
        profiles=["ADR"],
    )
    assert _single(result)["lq"]["status"] == "not_within"


def test_lq_gross_mass_above_30_kg_disqualifies_the_package():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="0,5 L",
                         gross_mass_per_package="35 kg")]),
        profiles=["ADR"],
    )
    row = _single(result)
    assert row["lq"]["status"] == "not_within"
    assert "35" in row["lq"]["message"]


def test_lq_zero_means_not_permitted():
    result = check_lq_eq(
        _entry([_product(limited_quantity="0", net_per_inner_packaging="0,5 L")]),
        profiles=["ADR"],
    )
    assert _single(result)["lq"]["status"] == "not_permitted"


def test_lq_without_inner_quantity_is_incomplete_not_silent():
    result = check_lq_eq(_entry([_product()]), profiles=["ADR"])
    row = _single(result)
    assert row["lq"]["status"] == "incomplete"
    assert result["status"] == "incomplete"


def test_a_number_without_a_unit_is_not_guessed_at():
    # "0,5" kan 0,5 g of 0,5 kg betekenen; raden is hier gevaarlijker dan vragen.
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="0,5",
                         gross_mass_per_package="20 kg")]),
        profiles=["ADR"],
    )
    assert _single(result)["lq"]["status"] == "incomplete"


def test_mass_input_against_a_volume_limit_is_flagged_not_compared():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="500 g",
                         gross_mass_per_package="20 kg")]),
        profiles=["ADR"],
    )
    row = _single(result)
    assert row["lq"]["status"] == "incomplete"
    assert "5 L" in row["lq"]["message"]


def test_lq_alternative_limits_match_the_kind_of_the_input():
    # UN 3175-stijl: "500 ml oder 500 g" — de variant van de ingevoerde eenheid telt.
    result = check_lq_eq(
        _entry([_product(limited_quantity="500 ml oder 500 g",
                         net_per_inner_packaging="300 g",
                         gross_mass_per_package="20 kg")]),
        profiles=["ADR"],
    )
    assert _single(result)["lq"]["status"] == "within_limits"


def test_a_special_provision_reference_is_reported_as_unreadable():
    result = check_lq_eq(
        _entry([_product(limited_quantity="siehe SV 251",
                         net_per_inner_packaging="1 L")]),
        language="en", profiles=["ADR"],
    )
    row = _single(result)
    assert row["lq"]["status"] == "no_data"
    assert "special provision" in row["lq"]["message"]


# --- EQ (3.5) -----------------------------------------------------------


def test_eq_within_the_e2_limits():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="25 g",
                         net_mass_liters_per_package="400 g",
                         gross_mass_per_package="20 kg")]),
        profiles=["ADR"],
    )
    row = _single(result)
    assert row["eq"]["status"] == "within_limits"
    assert "E2" in row["eq"]["message"]


def test_eq_inner_packaging_above_the_code_limit():
    # E2: ten hoogste 30 g/ml per binnenverpakking (tabel 3.5.1.2).
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="40 g",
                         net_mass_liters_per_package="400 g")]),
        profiles=["ADR"],
    )
    assert _single(result)["eq"]["status"] == "not_within"


def test_eq_outer_packaging_above_the_code_limit():
    # E2: ten hoogste 500 g/ml per buitenverpakking.
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="25 g",
                         net_mass_liters_per_package="600 g")]),
        profiles=["ADR"],
    )
    assert _single(result)["eq"]["status"] == "not_within"


def test_e0_is_not_permitted_as_excepted_quantity():
    result = check_lq_eq(
        _entry([_product(excepted_quantity="E0", net_per_inner_packaging="1 g")]),
        profiles=["ADR"],
    )
    assert _single(result)["eq"]["status"] == "not_permitted"


def test_eq_package_cap_of_3_5_5_raises_a_warning():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="25 g",
                         net_mass_liters_per_package="400 g",
                         gross_mass_per_package="20 kg",
                         quantity_packages="1200")]),
        profiles=["ADR"],
    )
    assert any(w["rule"] == "ADR/IMDG 3.5.5" for w in result["warnings"])


def test_no_warning_when_the_position_stays_under_1000_packages():
    result = check_lq_eq(
        _entry([_product(net_per_inner_packaging="25 g",
                         net_mass_liters_per_package="400 g",
                         gross_mass_per_package="20 kg",
                         quantity_packages="900")]),
        profiles=["ADR"],
    )
    assert result["warnings"] == []


# --- Grondslag en profielen ----------------------------------------------


def test_rid_gets_the_same_basis_note_as_the_points_table():
    result = check_lq_eq(_entry([_product()]), language="en", profiles=["RID"])
    assert result["basis_note"] and "RID" in result["basis_note"]


def test_adr_alone_carries_no_basis_note():
    result = check_lq_eq(_entry([_product()]), profiles=["ADR"])
    assert result["basis_note"] is None


def test_no_dangerous_goods_means_not_checked():
    result = check_lq_eq(_entry([{"description": "geen UN"}]), profiles=["ADR"])
    assert result["status"] == "not_checked"
    assert result["rows"] == []


def test_imdg_profile_fills_a_missing_value_from_the_dgl():
    # UN 1203 staat in de IMDG-lijst met "1 L"/E2; zonder ADR-waarde op het
    # product levert de lijst de grens.
    result = check_lq_eq(
        _entry([{
            "un_number": "1203",
            "proper_shipping_name": "GASOLINE",
            "class": "3",
            "packing_group": "II",
            "net_per_inner_packaging": "0,5 L",
            "gross_mass_per_package": "20 kg",
        }]),
        profiles=["IMDG"],
    )
    row = _single(result)
    assert row["lq"]["value"] == "1 L"  # aangevuld uit de IMDG-lijst
    assert row["lq"]["status"] == "within_limits"
    assert "1 L" in row["lq"]["message"]


def test_a_differing_imdg_value_is_flagged_next_to_the_adr_outcome():
    result = check_lq_eq(
        _entry([_product(un_number="1203", limited_quantity="2 L",
                         net_per_inner_packaging="0,5 L",
                         gross_mass_per_package="20 kg")]),
        language="en", profiles=["IMDG"],
    )
    row = _single(result)
    assert row["lq"]["status"] == "within_limits"
    assert "42-24" in row["lq"]["message"]
    assert "1 L" in row["lq"]["message"]


# --- Integratie met check_compliance en de API ----------------------------


def test_check_compliance_includes_lq_eq_for_land_and_sea_profiles():
    outcome = check_compliance(_entry([_product()]), ["ADR"], "nl")
    assert outcome["lq_eq"]["status"] == "incomplete"

    outcome = check_compliance(_entry([_product()]), ["IMDG"], "nl")
    assert "lq_eq" in outcome


def test_check_compliance_omits_lq_eq_for_air_only():
    # De lucht kent met de Y-verpakkingsinstructies een eigen LQ-stelsel dat
    # CargoPilot niet draagt; een ADR-uitkomst tonen zou een claim zijn.
    outcome = check_compliance(_entry([_product()]), ["IATA_DGR"], "nl")
    assert "lq_eq" not in outcome


def test_the_points_table_is_not_reduced_by_a_qualifying_lq_line():
    products = [_product(
        transport_category="2",
        adr_total_quantity="100 L",
        net_per_inner_packaging="0,5 L",
        gross_mass_per_package="20 kg",
    )]
    outcome = check_compliance(_entry(products), ["ADR"], "nl")
    lq_row = outcome["lq_eq"]["rows"][0]
    assert lq_row["lq"]["status"] == "within_limits"
    # 100 L × factor 3 blijft gewoon in de telling staan.
    assert outcome["adr_points"]["total_points"] == 300.0


def _post(payload: dict):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="test", role="admin", active=True
    )
    try:
        with TestClient(app) as client:
            return client.post("/api/dg/compliance", json=payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_the_api_returns_the_lq_eq_result_for_the_road_wizard_payload():
    response = _post({
        "entries": _entry([_product(net_per_inner_packaging="0,5 L",
                                    gross_mass_per_package="20 kg")]),
        "profiles": ["ADR"],
        "language": "en",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lq_eq"]["status"] == "checked"
    assert body["lq_eq"]["rows"][0]["lq"]["status"] == "within_limits"


def test_a_zero_inner_quantity_is_rejected_at_the_boundary():
    response = _post({
        "entries": _entry([_product(net_per_inner_packaging="0 L")]),
        "profiles": ["ADR"],
        "language": "en",
    })
    assert response.status_code == 422
