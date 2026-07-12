import openpyxl
from pypdf import PdfReader

from app.services.documents import (
    export_document,
    fill_pdf_document,
    get_document,
    get_registry,
    has_pdf_template,
    render_appendix_pdf,
    render_document_pdf,
    resolve_sections,
    validate_document,
)


def _pdf_bytes_start(path) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(5)

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


def test_official_forms_use_fillable_pdf_templates():
    registry = get_registry()
    docs = {doc["key"]: doc for doc in registry["documents"]}
    for key in ("cmr", "iata_dgd", "cim"):
        assert docs[key]["exporter"] == "pdf_template"
        assert has_pdf_template(key), key


def test_fill_cim_pdf_populates_boxes():
    values = dict(
        BASE_VALUES,
        place_of_delivery="Berlin Hbf",
        payment_instruction="franco",
        nhm_code="721650",
        established_place="Rotterdam",
        established_date="2026-07-13",
    )
    path = fill_pdf_document("cim", values, LINES, None, "nl")
    try:
        v = {k: str(val.get("/V") or "") for k, val in PdfReader(str(path)).get_fields().items()}
        assert "Firma A" in v["Expéditeur1"]  # vak 1
        assert "Firma B" in v["Destinataire4"]  # vak 4
        assert v["NHM Code0"] == "721650"  # vak 24
        assert "Stalen hoekprofiel" in v["Description21"]  # vak 21
        assert "Rotterdam" in v["Lieu et date d'établissement29"]  # vak 29
    finally:
        path.unlink(missing_ok=True)


def test_fill_cmr_pdf_populates_official_boxes():
    values = dict(
        BASE_VALUES,
        place_of_delivery="Berlin Hafen",
        freight_payment="prepaid",
        sender_instructions="Niet overladen.",
        carrier_name="Trans-Euro Logistics",
        established_place="Utrecht",
        established_date="2026-07-12",
    )
    path = fill_pdf_document("cmr", values, LINES, None, "nl")
    try:
        fields = PdfReader(str(path)).get_fields()
        values_by_field = {k: str(v.get("/V") or "") for k, v in fields.items()}
        assert "Firma A" in values_by_field["VakRood01"]  # box 1 sender
        assert "Firma B" in values_by_field["VakRood02"]  # box 2 consignee
        assert values_by_field["VakRood16"] == "Trans-Euro Logistics"  # box 16 carrier
        assert values_by_field["VakRood14"] == "Franco"  # box 14 payment
        assert "Stalen hoekprofiel" in values_by_field["VakRood06Regel01Kolom06"]
        assert values_by_field["VakRood06Regel01Kolom11"] == "462.7"
        # Handtekeningvakken 22/23/24 blijven leeg.
        assert values_by_field.get("VakRood23", "") == ""
    finally:
        path.unlink(missing_ok=True)


def test_fill_iata_pdf_strikes_non_applicable_and_lists_dg():
    values = dict(
        BASE_VALUES,
        awb_number="020-12345675",
        aircraft_limitation="cargo_only",
        shipment_type="non_radioactive",
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
                    "packing_group": "II",
                    "packing_instruction": "965",
                    "quantity_packages": "2",
                    "type_of_package": "4G box",
                    "net_mass_liters_per_package": "5 kg",
                }
            ],
        }
    ]
    path = fill_pdf_document("iata_dgd", values, LINES, dg, "en")
    try:
        fields = PdfReader(str(path)).get_fields()
        v = {k: str(val.get("/V") or "") for k, val in fields.items()}
        assert v["Air Waybill No"] == "020-12345675"
        # cargo_only -> passenger+cargo doorgestreept, cargo-only leeg
        assert v["Passenger and Cargo Aircraft"].strip() == "XXX"
        assert v["Cargo Aircraft Only"].strip() == ""
        # non_radioactive -> radioactive doorgestreept
        assert v["radioactive ship type"].strip() == "XXXXXXXXXXX"
        assert v["non-rad ship type"].strip() == ""
        dg_block = v["Nature and Quantity of Dangerous Goods"]
        assert "UN 3480" in dg_block
        assert "Lithium ion batteries" in dg_block
        assert "965" in dg_block
        # Handtekeningveld blijft leeg.
        assert v.get("Name-title", "") == "J. Jansen"
    finally:
        path.unlink(missing_ok=True)


def test_render_packing_list_pdf():
    values = dict(BASE_VALUES, document_date="2026-07-14", remarks="Breekbaar.")
    path = render_document_pdf(get_document("packing_list"), values, LINES, None, "nl")
    try:
        assert _pdf_bytes_start(path) == b"%PDF-"
        reader = PdfReader(str(path))
        assert len(reader.pages) >= 1
    finally:
        path.unlink(missing_ok=True)


def test_render_imo_pdf_contains_declaration_and_dg():
    values = dict(
        BASE_VALUES,
        declarant_name="J. Jansen",
        declaration_place="Rotterdam",
        declaration_date="2026-07-14",
    )
    dg = [
        {
            "a1_line_id": 1,
            "vehicle": "Accu",
            "products": [
                {
                    "un_number": "3480",
                    "proper_shipping_name": "Lithium ion batteries",
                    "class": "9",
                    "quantity_packages": "2",
                    "type_of_package": "4G box",
                }
            ],
        }
    ]
    path = render_document_pdf(get_document("imo_dgd"), values, LINES, dg, "en")
    try:
        assert _pdf_bytes_start(path) == b"%PDF-"
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        # Vaste teksten (Paragraphs) worden betrouwbaar geëxtraheerd door pypdf.
        assert "fully and accurately" in text  # verplichte IMO-verklaring
        assert "Apache License 2.0" in text  # disclaimer
        assert "IMO Multimodal Dangerous Goods Form" in text
    finally:
        path.unlink(missing_ok=True)


def test_export_vgm_workbook_still_available_with_disclaimer():
    values = dict(
        BASE_VALUES,
        container_number="MSKU1234567",
        vgm_kg="1000",
        vgm_method="method1",
        responsible_name="J. JANSEN",
        determination_place="Rotterdam",
        determination_date="2026-07-12",
    )
    path = export_document("vgm", values, LINES, None, "nl")
    try:
        wb = openpyxl.load_workbook(path)
        text = "\n".join(str(c.value) for row in wb.active.iter_rows() for c in row if c.value is not None)
        assert "MSKU1234567" in text
        assert "Apache License 2.0" in text
    finally:
        path.unlink(missing_ok=True)


def test_render_appendix_pdf_lists_lines_and_dg():
    dg = [
        {
            "a1_line_id": 1,
            "vehicle": "Accu",
            "products": [{"un_number": "3480", "proper_shipping_name": "Lithium ion batteries", "class": "9"}],
        }
    ]
    path = render_appendix_pdf(LINES, dg, {"date": "2026-07-14", "route": "Utrecht - Berlijn"}, "nl")
    try:
        assert _pdf_bytes_start(path) == b"%PDF-"
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        assert "Appendix A1" in text
        assert "Stalen hoekprofiel" in text
    finally:
        path.unlink(missing_ok=True)


def test_appendix_xlsx_keeps_only_a1_and_d_sheets(tmp_path):
    from app.services.exporter.appendix_exporter import export_appendix

    path = export_appendix(LINES, {"date": "2026-07-14"}, "nl", job_ref="cp-test")
    try:
        wb = openpyxl.load_workbook(path)
        assert set(wb.sheetnames) == {" A1", "D"}
    finally:
        path.unlink(missing_ok=True)


def test_export_unknown_document_raises():
    try:
        export_document("bestaat_niet", {}, [], None)
        assert False, "expected ValueError"
    except ValueError:
        pass
