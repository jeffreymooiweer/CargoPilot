"""The export bundle: one archive, and nothing in it silently missing.

"Download all" used to fire one download per document; since v1.130.0 it is
one archive that also carries the UN cards and the instructions in writing
for the journey's regimes. The rules these tests hold to:

* every document in the archive is rendered by the same code path as the
  per-document button — the bundle can never contain a different paper;
* a document that is still incomplete stays out, and the archive says so in
  its README instead of hiding the gap;
* the UN cards come only from the installed store, the instructions only as
  the edition prints them; what is not there is named, never substituted.
"""
import io
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.main import app
from app.services.documents import un_card_store

from test_un_card_store import make_package


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="test", role="admin", active=True)
    return TestClient(app)


def release():
    app.dependency_overrides.pop(get_current_user, None)


CONSIGNMENT = {
    "consignor_name": "Afzender BV",
    "consignor_address": "Havenweg 1, 3011 Rotterdam, Nederland",
    "consignee_name": "Ontvanger GmbH",
    "consignee_address": "Hafenstrasse 4, 47119 Duisburg, Duitsland",
    "loading_point": "Rotterdam",
    "discharge_point": "Duisburg",
    "freight_payment": "Franco",
    "established_place": "Rotterdam",
    "established_date": "2026-08-15",
    "vehicle_registration": "12-BXG-3",
    "reference": "CP-2026-100",
    "emergency_contact": "+31 10 123 4567",
}

PRODUCT = {
    "un_number": "1203", "proper_shipping_name": "Benzine", "class": "3",
    "classification_code": "F1", "packing_group": "II", "labels": "3",
    "hazard_number": "33", "tunnel_code": "(D/E)", "transport_category": "2",
    "quantity_packages": "4", "type_of_package": "vaten",
    "adr_total_quantity": "800 kg",
}

DG = [{"line_id": "1", "vehicle": "UNIT-1", "products": [PRODUCT]}]


def doc(key, **overrides):
    payload = {"document_key": key, "values": dict(CONSIGNMENT),
               "lines": [], "dangerous_goods": DG, "output_language": "nl"}
    payload.update(overrides)
    return payload


def bundle(payload):
    with client() as api:
        response = api.post("/api/documents/export/bundle", json=payload)
    release()
    return response


def names_in(response) -> list[str]:
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        return archive.namelist()


def read_member(response, name) -> bytes:
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        return archive.read(name)


def test_the_bundle_holds_every_document_once(data_dir):
    response = bundle({
        "documents": [doc("cmr"), doc("placarding_sheet")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    assert response.status_code == 200, response.text
    names = names_in(response)
    assert sum(1 for n in names if n.startswith("cmr_")) == 1
    assert sum(1 for n in names if n.startswith("placarding_sheet_")) == 1
    for name in names:
        if name.endswith(".pdf"):
            assert read_member(response, name)[:5] == b"%PDF-"


def test_the_instructions_ride_along_in_the_document_language(data_dir):
    response = bundle({
        "documents": [doc("cmr")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "de",
    })
    names = names_in(response)
    assert "instructions/adr-instructions-de.pdf" in names
    assert read_member(response, "instructions/adr-instructions-de.pdf")[:5] == b"%PDF-"


def test_the_un_cards_come_from_the_installed_store(data_dir, tmp_path):
    package = make_package(tmp_path / "p.zip", cards=(("1203", "ADR"),))
    un_card_store.import_package(package)
    response = bundle({
        "documents": [doc("cmr")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    names = names_in(response)
    assert "un-cards/UN1203_ADR.pdf" in names


def test_without_a_card_set_the_readme_says_so(data_dir):
    response = bundle({
        "documents": [doc("cmr")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    names = names_in(response)
    assert not any(n.startswith("un-cards/") for n in names)
    assert "README.txt" in names
    assert b"no card set is installed" in read_member(response, "README.txt")


def test_an_incomplete_document_stays_out_and_is_named(data_dir):
    incomplete = doc("cmr", values={})
    response = bundle({
        "documents": [doc("placarding_sheet"), incomplete],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    assert response.status_code == 200, response.text
    names = names_in(response)
    assert not any(n.startswith("cmr_") for n in names)
    assert b"cmr" in read_member(response, "README.txt")


def test_nothing_bundleable_refuses_instead_of_an_empty_archive(data_dir):
    response = bundle({
        "documents": [doc("cmr", values={})],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    assert response.status_code == 422
    assert bundle({"documents": []}).status_code == 422


def test_without_dangerous_goods_no_cards_and_no_instructions(data_dir):
    response = bundle({
        "documents": [doc("cmr", dangerous_goods=None)],
        "output_language": "nl",
    })
    assert response.status_code == 200, response.text
    names = names_in(response)
    assert not any(n.startswith(("un-cards/", "instructions/")) for n in names)
