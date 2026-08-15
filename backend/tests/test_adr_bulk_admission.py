"""ADR 7.3.1.1: may these goods travel in bulk at all, and in what?

The columns have been in the seed since v1.65.0 — BK codes inside column (10),
VC and AP codes in column (17) — and nothing computed with them: a bulk
consignment got no admission answer where a tank load has had one since
v1.66.0. Read in the official Dutch edition (printed pages 1398-1403) and the
UNECE English and French volumes II, which agree.
"""
import pytest

from app.services.dg.compliance import check_adr_bulk_admission


def line(un, **extra):
    return [{"line_id": "L1", "products": [
        {"un_number": un, "carriage_mode": "bulk", **extra}]}]


def only(result):
    assert len(result["items"]) == 1, result["items"]
    return result["items"][0]


def test_packages_are_not_asked_the_bulk_question():
    result = check_adr_bulk_admission(
        [{"line_id": "L1", "products": [{"un_number": "1350"}]}])
    assert result["status"] == "not_checked"


def test_sulphur_is_admitted_by_both_columns():
    """UN 1350: column (10) carries BK1, BK2 and BK3 beside its T code, and
    column (17) carries VC1 and VC2. Every code is named with its meaning, and
    the equipment conditions of 7.3.2/7.3.3 travel as conditions — the
    application cannot see the container."""
    item = only(check_adr_bulk_admission(line("1350"), "en"))
    assert item["permitted"] is True
    assert item["bk_codes"] == ["BK1", "BK2", "BK3"]
    assert item["vc_codes"] == ["VC1", "VC2"]
    assert "7.3.2" in item["message"] and "7.3.3" in item["message"]


def test_petrol_is_refused():
    """UN 1203 carries neither a BK nor a VC code: bulk carriage is not
    permitted, full stop (7.3.1.1)."""
    result = check_adr_bulk_admission(line("1203"), "en")
    assert result["status"] == "not_permitted"
    item = only(result)
    assert item["permitted"] is False
    assert item["provision"] == "7.3.1.1"


def test_ap_codes_travel_as_conditions():
    """Where column (17) carries AP provisions beside the VC codes, they are
    named — their text sets equipment requirements this application cannot
    verify, so they go along as conditions, not as facts."""
    import json
    from pathlib import Path

    seed = json.loads(
        (Path(__file__).resolve().parents[1]
         / "seed" / "dg" / "adr_table_a.json").read_text(encoding="utf-8"))
    carrier = next(row for row in seed["entries"]
                   if "AP" in str(row.get("carriage_bulk") or "")
                   and "VC" in str(row.get("carriage_bulk") or ""))
    item = only(check_adr_bulk_admission(line(carrier["un"]), "en"))
    assert item["ap_codes"], carrier
    assert "7.3.3.2" in item["message"]


def test_empty_uncleaned_names_the_exception_without_granting_it():
    """7.3.1.1 lets empty uncleaned packagings travel in bulk where their
    former contents are admitted. Whether they are is the substance's own
    answer — so the refusal stands, with the exception said beside it."""
    item = only(check_adr_bulk_admission(
        line("1203", empty_uncleaned="yes"), "en"))
    assert item["permitted"] is False
    assert "Empty uncleaned" in item["message"]


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_the_answer_speaks_four_languages(language):
    item = only(check_adr_bulk_admission(line("1350"), language))
    assert item["message"]
    refused = only(check_adr_bulk_admission(line("1203"), language))
    assert refused["message"]


def test_it_reaches_the_document():
    """The tank fit shipped answering on screen only (fixed in v1.87.0); the
    bulk admission must not repeat that arc. Both the refusal and the
    permission travel — the codes are what the loader checks the container
    against."""
    from app.services.documents.exporter import validate_document
    from app.services.documents.registry import get_document

    values = {
        "consignor_name": "Afzender", "consignor_address": "Havenweg 1",
        "consignee_name": "Ontvanger", "consignee_address": "Hafenstrasse 4",
        "loading_point": "Rotterdam", "discharge_point": "Duisburg",
        "freight_payment": "Franco", "established_place": "Rotterdam",
        "established_date": "2026-08-15",
    }
    goods = [{"line_id": "1", "products": [{
        "un_number": "1350", "proper_shipping_name": "ZWAVEL", "class": "4.1",
        "packing_group": "III", "carriage_mode": "bulk"}]}]
    _errors, warnings = validate_document(
        get_document("cmr"), values, [], goods, "nl")
    assert any("7.3.1.1" in w for w in warnings), warnings


def test_the_compliance_result_carries_it():
    from app.services.dg.compliance import check_compliance

    result = check_compliance(line("1350"), ["ADR"], "nl")
    assert result["adr_bulk_admission"]["status"] == "ok"
