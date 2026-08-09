"""Wie "broccoli" intikte kreeg bloem, en wie "cashew" intikte kreeg essenhout.

De zoekfunctie normaliseert een query eerst met een synoniementabel. Die tabel
is niet klein en niet handgeschreven: naast `search_synonyms.json` wordt **elke
alias van elk goed** er als sleutel in gezet. Bij 400 goederen waren dat al ruim
tweeduizend sleutels, bij 1.093 zijn het er ruim vierduizend.

De vervanging ging op letterreeksen en niet op woorden. Gemeten op de oude
gegevensbestand, vóór de reparatie:

    "broccoli"        ->  "meel / bloem / bloemsteenkool (kisten)"   -> Meel / bloem
    "cashew"          ->  "cessenew"                                 -> Essen
    "Kupferkathoden"  ->  "koperkathoden"                            -> Koper

"cashew" bevat "as", en "as" is een alias van essenhout. Daarmee werd de query
tot iets anders herschreven en kwam het goed dat de gebruiker letterlijk intikte
niet eens in de lijst voor. Dit is dus geen gevolg van de uitbreiding — het stond
er al — maar het wordt er wel erger van: hoe meer goederen, hoe meer korte
aliassen, hoe groter de kans dat er één toevallig middenin een ander woord staat.

Twee dingen die deze tests vastleggen:

1. **Een synoniem vervangt alleen een heel woord.** Ook met accenten: `\\b` van
   de re-module rekent ü en é niet tot de woordtekens, zodat "kupfer" middenin
   "Kupferkathoden" er zonder eigen randvoorwaarde alsnog uit gehaald zou worden.
2. **De goedkope voorfilter blijft staan.** De eerste reparatie liet de
   substring-test vallen en draaide een regex over alle vierduizend sleutels;
   dat kostte 1,4 seconde per zoekopdracht, tegen ongeveer 20 milliseconde
   ervoor. Correct en onbruikbaar is ook stuk.
"""

import time

import pytest

from app.core.database import Base, SessionLocal, engine
from app.core.startup import seed_catalogs
from app.services.catalog_sync import sync_catalogs
from app.services.catalog_search import normalize_synonyms, search_catalog


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_catalogs(session)
    # `seed_catalogs` vult alleen een lége tabel; wat er al staat blijft staan.
    # Een installatie die al draait krijgt nieuwe en gewijzigde goederen via de
    # catalogussynchronisatie bij het opstarten, en dat is ook de weg waarlangs
    # het foutieve alias "broccoli" bij bloemkool verdwijnt. Zonder deze stap
    # test dit bestand tegen een gegevensbestand van een vorige versie.
    sync_catalogs(session, use_network=False)
    yield session
    session.close()


@pytest.mark.parametrize("query", ["pineapple", "plexiglasplaat", "splitsing", "alufolie"])
def test_een_woord_wordt_niet_van_binnenuit_herschreven(db, query):
    """Vier woorden die een synoniem als letterreeks in zich dragen.

    "pineapple" bevat "pine" (→ hout), "plexiglasplaat" bevat "plexiglas",
    "splitsing" bevat "split" (→ grind) en "alufolie" bevat "alu" (→ aluminium).
    Alle vier komen uit `search_synonyms.json`, zodat deze test niet meebeweegt
    met de goederendatabase. Ze horen geen van alle te vuren: het synoniem staat
    er wel, maar niet als woord.
    """
    normalised, applied = normalize_synonyms(query, db)

    assert normalised.lower() == query.lower(), f"herschreven door {applied}"


def test_een_alias_wordt_wel_naar_zijn_eigen_goed_vertaald(db):
    """Wat de normalisatie wél hoort te doen, zodat de reparatie niet te ver gaat.

    "cashew" is een alias van cashewnoten en mag daar naartoe worden herschreven.
    Dat is geen verminking maar precies het nut van de tabel; de fout zat in het
    herschrijven middenin een woord, niet in het herschrijven zelf.
    """
    normalised, _ = normalize_synonyms("cashew", db)

    assert normalised.lower() == "cashewnoten"


def test_de_eigen_naam_van_een_goed_wint_van_andermans_alias(db):
    """Bloemkool droeg "broccoli" als alias en kaapte daarmee de zoekopdracht.

    De synoniementabel wordt in twee ronden gevuld — eerst alle namen, dan pas
    alle aliassen — juist om dit te voorkomen. Zonder die volgorde bepaalt de
    volgorde van de rijen in de database wie er wint, en dat is geen antwoord
    maar toeval.
    """
    normalised, _ = normalize_synonyms("broccoli", db)

    assert "bloemkool" not in normalised.lower()


def test_een_synoniem_op_woordgrens_werkt_gewoon(db):
    """De reparatie mag de tabel niet uitschakelen; hele woorden gaan wel om."""
    normalised, applied = normalize_synonyms("stalen plaat", db)

    assert applied, "er hoort hier wél een synoniem te vuren"
    assert "plaat" in normalised.lower()


def test_een_synoniem_aan_het_eind_van_de_query_telt_ook(db):
    """Zonder rechterrandvoorwaarde zou het laatste woord buiten schot blijven."""
    normalised, _ = normalize_synonyms("plaat inox", db)

    assert "rvs" in normalised.lower()


@pytest.mark.parametrize(
    "query,expected",
    [
        ("broccoli", "Broccoli"),
        ("cashew", "Cashewnoten"),
        ("spruitjes", "Spruitjes"),
        ("merbau", "Merbau"),
        ("betonstaal", "Betonstaal"),
    ],
)
def test_wat_de_gebruiker_intikt_staat_bovenaan(db, query, expected):
    """De uitkomst waar het om gaat: het goed zelf, niet iets wat erop lijkt."""
    hits = search_catalog(db, query, language="nl", limit=5)

    assert hits, f"geen enkele treffer voor {query!r}"
    assert (hits[0].get("label") or hits[0].get("value")) == expected


def test_zoeken_blijft_binnen_een_tiende_seconde(db):
    """Een bovengrens die de eerste reparatie ruim overschreed (1,4 s).

    De wizard herberekent met een debounce van 600 ms en zoekt tijdens het
    typen. Deze grens is bewust ruim — hij vangt een orde van grootte, geen
    tiende procent, en op een trage bouwmachine mag het best twee keer zo lang
    duren als hier gemeten.
    """
    search_catalog(db, "opwarmen", language="nl", limit=5)

    start = time.perf_counter()
    for query in ("broccoli", "stalen plaat 20 mm", "Kupferkathoden", "iron ore pellets"):
        search_catalog(db, query, language="nl", limit=5)
    average_ms = (time.perf_counter() - start) / 4 * 1000

    assert average_ms < 500, f"{average_ms:.0f} ms per zoekopdracht"
