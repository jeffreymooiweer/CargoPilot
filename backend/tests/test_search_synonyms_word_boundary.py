"""Whoever typed "broccoli" got flour, and whoever typed "cashew" got ash wood.

The search normalises a query first with a synonym table. That table is not
small and not handwritten: alongside `search_synonyms.json`, **every alias of
every commodity** is put into it as a key. With 400 commodities that was already
well over two thousand keys; with 1,093 it is well over four thousand.

The replacement worked on runs of letters and not on words. Measured on the old
data file, before the repair:

    "broccoli"        ->  "meel / bloem / bloemsteenkool (kisten)"   -> Meel / bloem
    "cashew"          ->  "cessenew"                                 -> Essen
    "Kupferkathoden"  ->  "koperkathoden"                            -> Koper

"cashew" contains "as", and "as" is an alias of ash wood. The query was thereby
rewritten into something else and the commodity the user typed literally did not
even appear in the list. So this is not a consequence of the expansion — it was
already there — but the expansion makes it worse: the more commodities, the more
short aliases, the greater the chance that one happens to sit inside another word.

Two things these tests record:

1. **A synonym replaces a whole word only.** Including with accents: the re
   module's `\\b` does not count ü and é as word characters, so "kupfer" in the
   middle of "Kupferkathoden" would still be pulled out without a boundary of its
   own.
2. **The cheap pre-filter stays.** The first repair dropped the substring test
   and ran a regex over all four thousand keys; that cost 1.4 seconds per search,
   against roughly 20 milliseconds before. Correct and unusable is broken too.
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
    # `seed_catalogs` only fills an *empty* table; what is already there stays.
    # An installation that is already running gets new and changed commodities
    # via the catalogue synchronisation at startup, and that is also the route by
    # which the faulty alias "broccoli" disappears from cauliflower. Without this
    # step this file tests against a data file from a previous version.
    sync_catalogs(session, use_network=False)
    yield session
    session.close()


@pytest.mark.parametrize("query", ["pineapple", "plexiglasplaat", "splitsing", "alufolie"])
def test_een_woord_wordt_niet_van_binnenuit_herschreven(db, query):
    """Four words carrying a synonym as a run of letters.

    "pineapple" contains "pine" (→ timber), "plexiglasplaat" contains
    "plexiglas", "splitsing" contains "split" (→ gravel) and "alufolie" contains
    "alu" (→ aluminium). All four come from `search_synonyms.json`, so this test
    does not move along with the goods database. None of them should fire: the
    synonym is there, but not as a word.
    """
    normalised, applied = normalize_synonyms(query, db)

    assert normalised.lower() == query.lower(), f"herschreven door {applied}"


def test_een_alias_wordt_wel_naar_zijn_eigen_goed_vertaald(db):
    """What the normalisation *should* do, so the repair does not go too far.

    "cashew" is an alias of cashew nuts and may be rewritten to those. That is
    not mutilation but precisely the point of the table; the fault was in
    rewriting inside a word, not in rewriting itself.
    """
    normalised, _ = normalize_synonyms("cashew", db)

    assert normalised.lower() == "cashewnoten"


def test_de_eigen_naam_van_een_goed_wint_van_andermans_alias(db):
    """Cauliflower carried "broccoli" as an alias and hijacked the search with it.

    The synonym table is filled in two passes — first all the names, only then
    all the aliases — precisely to prevent this. Without that order the order of
    the rows in the database decides who wins, and that is not an answer but
    coincidence.
    """
    normalised, _ = normalize_synonyms("broccoli", db)

    assert "bloemkool" not in normalised.lower()


def test_een_synoniem_op_woordgrens_werkt_gewoon(db):
    """The repair must not switch the table off; whole words are still converted."""
    normalised, applied = normalize_synonyms("stalen plaat", db)

    assert applied, "er hoort hier wél een synoniem te vuren"
    assert "plaat" in normalised.lower()


def test_een_synoniem_aan_het_eind_van_de_query_telt_ook(db):
    """Without a right-hand boundary the last word would escape."""
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
    """The outcome that matters: the commodity itself, not something resembling it."""
    hits = search_catalog(db, query, language="nl", limit=5)

    assert hits, f"geen enkele treffer voor {query!r}"
    assert (hits[0].get("label") or hits[0].get("value")) == expected


def test_zoeken_blijft_binnen_een_tiende_seconde(db):
    """An upper bound the first repair exceeded by a wide margin (1.4 s).

    The wizard recalculates with a 600 ms debounce and searches while you type.
    This bound is deliberately generous — it catches an order of magnitude, not a
    tenth of a percent, and on a slow build machine it may well take twice as
    long as measured here.
    """
    search_catalog(db, "opwarmen", language="nl", limit=5)

    start = time.perf_counter()
    for query in ("broccoli", "stalen plaat 20 mm", "Kupferkathoden", "iron ore pellets"):
        search_catalog(db, query, language="nl", limit=5)
    average_ms = (time.perf_counter() - start) / 4 * 1000

    assert average_ms < 500, f"{average_ms:.0f} ms per zoekopdracht"
