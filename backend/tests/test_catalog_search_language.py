"""De cataloguszoeker sprak altijd Nederlands.

`search_catalog` had helemaal geen taalparameter: de goederennamen kwamen er
onveranderlijk als `labels["nl"]` uit. Dat trof een Engelse gebruiker net zo
hard als een Duitse — het scherm in het Engels, de suggesties in het
Nederlands.

Het is geen cosmetisch punt. De suggestie die de gebruiker aanklikt wordt de
omschrijving in de goederenkolom van zijn vrachtbrief; wat hier uit komt staat
straks op een CMR.

Het zoeken zelf blijft over alle talen heen gaan — wie "Stahl" typt terwijl hij
Nederlands leest, hoort gewoon staal te vinden. Alleen wat er wordt teruggegeven
volgt de taal.
"""

import pytest

from app.core.database import Base, SessionLocal, engine
from app.core.startup import seed_catalogs
from app.core.languages import SUPPORTED
from app.services.catalog_search import (
    MATERIAL_LABELS,
    PRODUCT_LABELS,
    material_label,
    product_label,
    search_catalog,
)


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_catalogs(session)
    yield session
    session.close()


def labels(db, query, language):
    return [hit["label"] for hit in search_catalog(db, query, limit=5, language=language)]


@pytest.mark.parametrize("language,expected", [
    ("nl", "Staal"),
    ("en", "Steel"),
    ("de", "Stahl"),
])
def test_a_material_comes_back_in_the_language_you_asked_for(db, language, expected):
    assert expected in labels(db, "staal", language)


@pytest.mark.parametrize("query", ["staal", "steel", "Stahl"])
def test_the_search_itself_keeps_understanding_every_language(db, query):
    """Wie in het Duits leest maar een Nederlandse artikellijst plakt, moet
    zijn materiaal nog steeds vinden."""
    assert "Stahl" in labels(db, query, "de")


def test_a_german_name_that_exists_only_as_a_label_is_findable(db):
    """De Duitse benamingen staan als label in de seed, niet als alias. Als
    het zoeken alleen op aliassen zou kijken, zou de gebruiker de term die op
    zijn scherm staat niet terugvinden."""
    assert "Edelstahl" in labels(db, "Edelstahl", "de")
    assert "Quecksilber" in labels(db, "Quecksilber", "de")


def test_a_template_suggestion_follows_the_language_too(db):
    """De sjabloonsuggestie ("hoekprofiel 80x80x8x6000") is juist de tekst die
    ongewijzigd op het document belandt."""
    assert any("Winkelprofil" in label for label in labels(db, "Winkelprofil", "de"))
    assert any("Hoekprofiel" in label for label in labels(db, "hoekprofiel", "nl"))
    assert any("Angle Profile" in label for label in labels(db, "hoekprofiel", "en"))


def test_the_hint_under_a_suggestion_is_translated(db):
    hits = search_catalog(db, "hoekprofiel", limit=5, language="de")
    template = next(h for h in hits if h["source"] == "template")
    assert "Abmessungen" in template["sublabel"]


def test_an_unknown_language_falls_back_rather_than_returning_nothing(db):
    """Een label mag nooit leeg zijn; dan staat er straks niets in de
    goederenkolom."""
    assert all(hit["label"] for hit in search_catalog(db, "staal", limit=5, language="fr"))


# --- De labeltabellen -----------------------------------------------------


def test_every_product_type_speaks_every_language():
    """Meegroeien met SUPPORTED in plaats van drie talen bij naam te noemen.

    Deze twee tests eisten letterlijk {"nl", "en", "de"}. Toen het Frans erbij
    kwam faalden ze niet omdat er iets miste, maar omdat er iets bij was — een
    bewaker die een nieuwe taal als fout ziet, bewaakt die taal niet.
    """
    for product_type, names in PRODUCT_LABELS.items():
        assert set(names) == set(SUPPORTED), product_type
        assert all(names.values()), product_type


def test_every_fallback_material_speaks_every_language():
    for name, names in MATERIAL_LABELS.items():
        assert set(names) == set(SUPPORTED), name
        assert all(names.values()), name


def test_product_label_never_returns_an_internal_key():
    assert product_label("angle_profile", "de") == "Winkelprofil"
    # Een type dat de tabel niet kent mag geen "angle_profile" op het scherm
    # zetten.
    assert product_label("mystery_type", "de") == "mystery type"


def test_material_label_prefers_the_database_over_the_fallback_table(db):
    from app.models.user import Material

    steel = db.query(Material).filter(Material.canonical_name == "steel").one()
    assert material_label(steel, "de") == "Stahl"
