"""The eFTI common data set as a seed, and the export's place in it.

Three things are pinned. The seed is what the Official Journal says: the
counts of Table 1 and Table 2 as measured on the text, no identifier twice,
every subset row naming an element Table 1 has. The mapping names only
elements that exist and only export fields that exist — a mapping onto a
field the wizard does not write is the silent failure the exercise is
meant to prevent. And the coverage the document states is the coverage
the code measures, so the two cannot drift apart.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.schemas.dg_compliance import DangerousGoodsProduct
from app.services import efti
from app.services.documents.registry import get_registry

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "efti-mapping.md"


def test_the_seed_is_the_annex_as_measured():
    elements = efti.elements()
    assert len(elements) == 681
    kinds = {}
    for e in elements:
        kinds[e["type"]] = kinds.get(e["type"], 0) + 1
    assert kinds == {"ABIE": 1, "ASBIE": 148, "BBIE": 409, "SC": 123}
    ids = [e["id"] for e in elements]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"(eFTI\d+|ASBIE\d+)", i) for i in ids)
    rows = efti.subset_rows()
    assert len(rows) == 378
    assert set(rows) <= set(ids)
    assert efti.source()["eli"] == "http://data.europa.eu/eli/reg_del/2024/2024/oj"


def test_the_subsets_ask_what_the_annex_says():
    """The counts per status, measured on the text and pinned."""
    asked = {s: len(efti.asked_by(s)) for s in efti.SUBSETS}
    assert asked == {"EU01": 50, "EU05a": 124, "EU05b": 122, "EU05c": 128}
    assert efti.element("eFTI581")["name"] == "Mode code"
    assert efti.subset_rows()["eFTI581"]["EU05a"]["status"] == "M"
    assert efti.code_list("CL-037")["allowed"].startswith("Allowed codes: 1 = Maritime")
    assert "1.1.3.6" in efti.business_rule("BR-007")["rule"]


def test_a_supplementary_component_is_not_counted_as_an_element():
    """eFTI40 follows eFTI39 with status D*; it is neither asked nor missing."""
    ids = {e["id"] for e in efti.asked_by("EU01")}
    assert "eFTI39" in ids and "eFTI40" not in ids


def registry_keys() -> set[str]:
    registry = get_registry()
    keys = {f["key"] for s in registry["shared_sections"] for f in s["fields"]}
    for document in registry["documents"]:
        for section in document["sections"]:
            for field in section.get("fields", []) or []:
                keys.add(field["key"])
    return keys


LINE_KEYS = {"description", "quantity", "unit", "weight_each_kg", "weight_total_kg",
             "length_cm", "width_cm", "height_cm", "material", "package_content"}
COMPLIANCE_KEYS = {"adr_points", "labels", "package_marking"}


@pytest.mark.parametrize("entry", efti.mapping(), ids=lambda m: m["efti"])
def test_every_mapping_entry_names_an_element_and_a_field_that_exist(entry):
    element = efti.element(entry["efti"])
    assert element is not None and element["type"] in ("BBIE", "SC"), entry["efti"]
    assert entry["kind"] in ("field", "derived", "translated")
    products = set(DangerousGoodsProduct.model_fields) | {"class", "labels", "tunnel_code", "hazard_number",
                                                          "limited_quantity", "excepted_quantity",
                                                          "environmentally_hazardous", "additional_information",
                                                          "quantity_packages", "type_of_package",
                                                          "gross_mass_per_package", "technical_name",
                                                          "specific_gas_name", "firework_classification"}
    # "goods[].length_cm, width_cm, height_cm": the bare names that follow a
    # source share its prefix.
    prefix = ""
    for source in re.split(r",\s*", entry["source"]):
        source = source.strip()
        if source in ("modality", "documents[]"):
            continue
        head, dot, key = source.rpartition(".")
        if dot:
            prefix = head
        key = key.split()[0]
        if prefix == "consignment":
            assert key in registry_keys(), source
        elif prefix == "goods[]":
            assert key in LINE_KEYS, source
        elif prefix == "dangerous_goods[].products[]":
            assert key in products, source
        elif prefix.startswith("compliance"):
            assert key in COMPLIANCE_KEYS or prefix.split(".")[1] in COMPLIANCE_KEYS, source
        else:
            raise AssertionError(f"unknown source shape: {source}")


def test_no_element_is_mapped_twice():
    ids = [m["efti"] for m in efti.mapping()]
    assert len(ids) == len(set(ids))


def test_what_the_mapping_cannot_answer_is_the_party_model_and_the_class_7_data():
    """The account in the document names two gaps; the measurement agrees."""
    missing = {e["id"] for e in efti.coverage("EU05a")["missing_elements"]}
    # The structured consignor address: postcode, street, city ... (eFTI54-62).
    assert {"eFTI54", "eFTI56", "eFTI57"} <= missing
    # Class 7: transport index, isotope, activity (eFTI287-292).
    assert {"eFTI288", "eFTI290", "eFTI292"} <= missing
    # And what is answered: the UN number, the name, the mode.
    answered = {e["id"] for e in efti.coverage("EU05a")["answered_elements"]}
    assert {"eFTI232", "eFTI251", "eFTI581", "eFTI258", "eFTI255"} <= answered


def test_the_document_states_the_measured_coverage():
    """docs/efti-mapping.md carries a table "EU05a | 124 | 63" and so on; the
    numbers there are the numbers here."""
    text = DOC.read_text(encoding="utf-8")
    for subset in efti.SUBSETS:
        cov = efti.coverage(subset)
        pattern = rf"\|\s*{subset}\s*\|[^|]*\|\s*{cov['asked']}\s*\|\s*{cov['answered']}\s*\|"
        assert re.search(pattern, text), (subset, cov["asked"], cov["answered"])
    for entry in efti.mapping():
        assert entry["efti"] in text, entry["efti"]
