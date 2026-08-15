"""The packing certificate of 5.4.2 and the on-board lists of 8.1.2.

The certificate's nine declarations are the IMDG's, printed in the ADR's own
footnote to 5.4.2 (official Dutch edition, printed pages 1002-1004) — which is
what makes this document buildable from a free official text. The on-board
lists come from ADR 8.1.2.1/8.1.2.2 (printed page 1431) and ADN 8.1.2.1/8.1.2.2
of the official Dutch edition.

The one property worth pinning hardest: **nothing is pre-ticked**. Every
declaration concerns what was established at the ramp, and a certificate this
application had already ticked would claim knowledge it cannot have.
"""
import fitz
import pytest

from app.services.documents.onboard_pack import (
    DECLARATIONS,
    render_onboard_documents,
    render_packing_certificate,
)


def text_of(path):
    try:
        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc)
    finally:
        path.unlink(missing_ok=True)


VALUES = {"container_number": "MSKU 123456-7", "vehicle_registration": "12-BXG-4"}


def test_the_certificate_carries_all_nine_declarations():
    """IMDG 5.4.2.1 lists nine conditions and the certificate reproduces every
    one — a certificate with eight is a different document."""
    assert len(DECLARATIONS) == 9
    text = text_of(render_packing_certificate(VALUES, [], [], "nl"))
    assert "5.4.2" in text
    assert text.count("[") >= 9
    assert "rechtop gestuwd" in text          # drums upright (4)
    assert "IMDG 7.4.6" in text               # class 1 structural (6)
    assert "UN 1845" in text                  # asphyxiation marking (8)


def test_nothing_is_pre_ticked():
    text = text_of(render_packing_certificate(VALUES, [], [], "nl"))
    assert "☑" not in text and "☒" not in text


def test_the_unit_number_is_the_certificates_anchor():
    """5.4.2.1 asks for the container/vehicle identification number(s)."""
    text = text_of(render_packing_certificate(VALUES, [], [], "en"))
    assert "MSKU 123456-7" in text


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_the_certificate_speaks_four_languages(language):
    assert text_of(render_packing_certificate(VALUES, [], [], language))


def test_the_road_list_splits_made_from_bring():
    """The split is the point: the certificate of approval and the driver's
    ADR certificate can never come from this application, and saying so next
    to the generated papers is what makes the list honest."""
    text = text_of(render_onboard_documents({}, [], [], "en", regime="ADR"))
    assert "8.1.2" in text
    assert "5.4.3" in text            # instructions in writing — made
    assert "9.1.3" in text            # certificate of approval — bring
    assert "8.2.1" in text            # driver certificate — bring
    assert "1.10.1.4" in text         # photo ID — bring


def test_the_vessel_list_is_the_adn_own():
    text = text_of(render_onboard_documents({}, [], [], "nl", regime="ADN"))
    assert "1.16.1.1" in text         # vessel certificate of approval
    assert "7.1.4.11" in text         # stowage plan — made by the app
    assert "8.2.1.2" in text          # ADN expert
    assert "ADN" in text


def test_both_documents_are_registered_with_their_modality():
    from app.services.documents.registry import get_document, get_registry

    registry = get_registry()
    road = next(m for m in registry["modalities"] if m["key"] == "road")
    inland = next(m for m in registry["modalities"] if m["key"] == "inland")
    assert "packing_certificate" in road["documents"]
    assert "onboard_documents_adr" in road["documents"]
    assert "onboard_documents_adn" in inland["documents"]
    assert get_document("packing_certificate")["exporter"] == "packing_certificate"
    assert get_document("onboard_documents_adn")["exporter"] == "onboard_adn"
