from app.services.dg.database import (
    get_un_entries,
    offline_lookup,
    search_packagings,
    search_un_numbers,
)


def test_search_by_exact_un():
    results = search_un_numbers("1203")
    assert results[0]["un"] == "1203"
    assert results[0]["name_en"] == "Gasoline"
    assert results[0]["class"] == "3"
    assert results[0]["packing_group"] == "II"
    assert results[0]["transport_category"] == "2"
    assert results[0]["tunnel_code"] == "D/E"
    assert "P001" in results[0]["packing_instructions"]


def test_search_by_un_prefix():
    results = search_un_numbers("120")
    assert any(r["un"] == "1202" for r in results)


def test_search_by_name():
    results = search_un_numbers("acetone")
    assert any(r["un"] == "1090" for r in results)


def test_search_by_german_name_diacritics():
    # "Gasöl" (diesel) has to be findable via "gasol" as well
    results = search_un_numbers("gasol")
    assert any(r["un"] == "1202" for r in results)


def test_lithium_batteries_present():
    entries = get_un_entries("3480")
    assert entries and entries[0]["class"] == "9"
    assert any("P903" in e["packing_instructions"] for e in entries)


def test_offline_lookup_shape():
    result = offline_lookup("1090")
    # The default language is Dutch, and a Dutch document carries both names.
    assert result["proper_shipping_name"] == "ACETON (ACETONE)"
    assert result["packing_instruction"] == "P001"
    assert result["tunnel_restriction_code"] == "(D/E)"


def test_offline_lookup_unknown():
    assert offline_lookup("9999") is None


def test_packagings_full_list():
    results = search_packagings()
    codes = {r["code"] for r in results}
    assert {"1A1", "4G", "3H1", "5M1", "6HA1", "11A", "13H3", "31HZ1", "50H"} <= codes
    assert len(results) >= 100


def test_packagings_search_by_code_and_name():
    assert search_packagings("4G")[0]["code"] == "4G"
    assert any(r["code"].startswith("13H") for r in search_packagings("big bag"))
