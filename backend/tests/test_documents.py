import openpyxl

from app.services.documents import (
    export_document,
    get_document,
    get_registry,
    resolve_sections,
    validate_document,
)

BASE_VALUES = {
    "consignor_name": "Firma A",
    "consignor_address": "Straat 1, 1234 AB Utrecht, NL",
    "consignee_name": "Firma B",
    "consignee_address": "Weg 2, 10115 Berlin, DE",
    "loading_point": "Utrecht",
    "discharge_point": "Berlijn",
}

LINES = [
    {
        "include": True,
        "description": "Stalen hoekprofiel 80x80x8x6000",
        "output_description": "Stalen hoekprofiel 80x80x8x6000",
        "quantity": 8,
        "unit": "stuks",
        "weight_total_kg": 462.7,
        "transport_volume_m3": 0.31,
        "length_cm": 600,
        "width_cm": 8,
        "height_cm": 8,
    }
]


def test_registry_modalities_reference_existing_documents():
    registry = get_registry()
    doc_keys = {doc["key"] for doc in registry["documents"]}
    modality_keys = [m["key"] for m in registry["modalities"]]
    assert modality_keys == ["road", "rail", "sea", "inland", "air", "multimodal"]
    for modality in registry["modalities"]:
        for key in modality["documents"]:
            assert key in doc_keys, f"{modality['key']} verwijst naar onbekend document {key}"


def test_registry_multimodal_offers_all_generic_documents():
    registry = get_registry()
    multimodal = next(m for m in registry["modalities"] if m["key"] == "multimodal")
    assert set(multimodal["documents"]) == {doc["key"] for doc in registry["documents"]}


def test_registry_sections_resolve_and_have_required_labels():
    registry = get_registry()
    for doc in registry["documents"]:
        for section in resolve_sections(doc):
            assert section.get("label"), f"sectie zonder label in {doc['key']}"
            for field in section.get("fields", []):
                assert field.get("label", {}).get("nl")
                assert field.get("label", {}).get("en")
                assert field.get("status")


def test_validate_blocks_missing_required_fields():
    cmr = get_document("cmr")
    errors, _ = validate_document(cmr, {}, LINES, None)
    assert errors
    assert any("Afzender" in e for e in errors)


def test_validate_cmr_passes_with_required_fields():
    cmr = get_document("cmr")
    values = dict(
        BASE_VALUES,
        freight_payment="prepaid",
        established_place="Utrecht",
        established_date="2026-07-12",
    )
    errors, warnings = validate_document(cmr, values, LINES, None)
    assert errors == []
    assert warnings == []


def test_validate_iata_blocks_incomplete_dg_classification():
    iata = get_document("iata_dgd")
    values = dict(
        BASE_VALUES,
        aircraft_limitation="cargo_only",
        shipment_type="non_radioactive",
        emergency_contact="+31 6 12345678",
        signatory_name="J. Jansen",
        declaration_place="Utrecht",
        declaration_date="2026-07-12",
    )
    dg = [{"a1_line_id": 1, "vehicle": "Accu's", "products": [{"un_number": "3480"}]}]
    errors, _ = validate_document(iata, values, LINES, dg)
    assert errors
    assert any("packing_instruction" in e for e in errors)


def test_validate_iata_requires_dg_entries():
    iata = get_document("iata_dgd")
    errors, _ = validate_document(iata, BASE_VALUES, LINES, [])
    assert any("gevaarlijke" in e.lower() or "dangerous" in e.lower() for e in errors)


def test_validate_vgm_method2_sum_warning():
    vgm = get_document("vgm")
    values = dict(
        BASE_VALUES,
        container_number="MSKU1234567",
        vgm_kg="1000",
        vgm_method="method2",
        cargo_mass_kg="800",
        packaging_mass_kg="20",
        pallets_mass_kg="50",
        securing_mass_kg="10",
        container_tare_kg="2200",
        responsible_name="J. JANSEN",
        determination_place="Rotterdam",
        determination_date="2026-07-12",
    )
    errors, warnings = validate_document(vgm, values, LINES, None)
    assert errors == []
    assert warnings and "VGM" in warnings[0]


def test_export_cmr_generates_workbook_with_goods_and_signature_note():
    values = dict(
        BASE_VALUES,
        freight_payment="prepaid",
        established_place="Utrecht",
        established_date="2026-07-12",
    )
    path = export_document("cmr", values, LINES, None, "nl")
    try:
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        text = "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
        assert "CMR-vrachtbrief" in text
        assert "Stalen hoekprofiel" in text
        assert "Firma A" in text
        assert "vak 8" in text.lower() or "Vak 8" in text
        assert "Franco" in text
    finally:
        path.unlink(missing_ok=True)


def test_export_iata_includes_dg_table_and_operational_markers():
    values = dict(
        BASE_VALUES,
        aircraft_limitation="cargo_only",
        shipment_type="non_radioactive",
        emergency_contact="+31 6 12345678",
        signatory_name="J. Jansen",
        declaration_place="Utrecht",
        declaration_date="2026-07-12",
    )
    dg = [
        {
            "a1_line_id": 1,
            "vehicle": "Lithium batteries",
            "products": [
                {
                    "un_number": "3480",
                    "proper_shipping_name": "Lithium ion batteries",
                    "class": "9",
                    "packing_instruction": "965",
                    "quantity_packages": "2",
                    "type_of_package": "4G box",
                    "net_mass_liters_per_package": "5 kg",
                    "cargo_aircraft_only": "Y",
                }
            ],
        }
    ]
    path = export_document("iata_dgd", values, LINES, dg, "en")
    try:
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        text = "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
        assert "Lithium ion batteries" in text
        assert "IATA_DGR" in text
        assert "carrier/forwarder" in text
    finally:
        path.unlink(missing_ok=True)


def test_export_unknown_document_raises():
    try:
        export_document("bestaat_niet", {}, [], None)
        assert False, "expected ValueError"
    except ValueError:
        pass
