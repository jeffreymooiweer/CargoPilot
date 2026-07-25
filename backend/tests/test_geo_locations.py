from app.services.geo.locations import location_counts, search_locations


def test_counts_all_types_loaded():
    counts = location_counts()
    assert counts["airport"] > 4000
    assert counts["port"] > 15000
    assert counts["station"] > 700


def test_iata_code_exact_match_first():
    results = search_locations("AMS", types=["airport"])
    assert results[0]["code"] == "AMS"
    assert "Schiphol" in results[0]["name"]


def test_port_search_by_name():
    results = search_locations("rotterdam", types=["port"])
    assert any(r["code"] == "NLRTM" for r in results)


def test_station_search():
    results = search_locations("utrecht", types=["station"])
    assert any("Utrecht" in r["name"] for r in results)


def test_mixed_search_includes_all_types():
    results = search_locations("amsterdam", limit=25)
    types = {r["type"] for r in results}
    assert {"airport", "port", "station"} <= types


def test_country_filter():
    results = search_locations("rotterdam", types=["port"], country="NL")
    assert results and all(r["country"] == "NL" for r in results)


def test_diacritics_insensitive():
    results = search_locations("dusseldorf", types=["airport"])
    assert any("sseldorf" in r["name"] for r in results)


def test_short_query_returns_nothing():
    assert search_locations("a") == []
