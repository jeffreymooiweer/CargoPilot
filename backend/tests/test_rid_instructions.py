"""The RID's own instructions in writing, served like the ADR's and ADN's.

RID 5.4.3.4 prints a four-page model of its own — INSTRUCTIONS IN WRITING
ACCORDING TO RID, addressed to the train driver — and 5.4.3.1 requires it in
the driver's cab. 5.4.3.2 makes providing it the carrier's duty, in a language
the driver can read; the application serves the model so the consignor can
hand it over, and the duty stays the carrier's. The page ranges were measured
on all four editions in the store by scripts/find_instructions_pages.py
(fetch-regulations run 32275442072); the English model title sits on page 856
of the OTIF edition, the German on 916, the French on 910, the Dutch on 981.
"""

from app.services import regulations


def test_rid_is_a_regime_of_its_own():
    assert regulations.REGIMES == ("adr", "rid", "adn")


def test_the_four_rid_models_are_registered():
    docs = [d for d in regulations.instruction_documents()
            if d["model_of"]["regime"] == "rid"]
    assert [d["model_of"]["language"] for d in docs] == ["nl", "en", "de", "fr"]
    for doc in docs:
        cut = doc["cut_from"]
        assert cut["document"] in ("rid", "rid_de", "rid_fr", "rid_nl_2025")
        assert len(cut["pages"]) == 2 and cut["pages"][1] - cut["pages"][0] == 3


def test_the_status_is_honest_where_the_store_lacks_the_edition():
    """The development container's store has no RID PDFs; the status says
    what is missing rather than pretending or crashing."""
    status = regulations.instruction_status("rid", "en")
    assert status["provision"] == "5.4.3"
    if not status["available"]:
        assert status["reason"] == "missing_in_store"
        assert status["needs"] == "rid"
