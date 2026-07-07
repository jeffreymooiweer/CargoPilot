import pytest
from app.core.database import Base, SessionLocal, engine
from app.core.startup import seed_catalogs
from app.services.catalog_sync import sync_catalogs
from app.services.pipeline import parse_and_calculate

STEEL_INPUT = """Stalen hoekprofiel 80x80x8x6000 | 8 | stuks
staal hoekprofiel 50x50x5x6000mm | 38 | stuks
Staal kokerprofiel 60x60x6x6000mm | 32 | stuks
Staal kokerprofiel 40x40x3x6000 | 12 | stuks
UNP 220 mml=5700mm gegalvaniseerd | 24 | stuks"""

EXPECTED = [458, 850, 1953, 251, 4022]
TOTAL_EXPECTED = 7534


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_catalogs(session)
    sync_catalogs(session, use_network=False)
    yield session
    session.close()


def test_regression_steel_weights(db):
    result = parse_and_calculate(STEEL_INPUT, db, output_language="nl", mode="continue")
    assert result["success"]
    lines = result["lines"]
    assert len(lines) == 5
    for line, expected in zip(lines, EXPECTED):
        actual = line["weight_total_kg"]
        assert actual is not None
        margin = expected * 0.02
        assert abs(actual - expected) <= margin, f"{line['description']}: {actual} vs {expected}"
    total = result["totals"]["total_weight_kg"]
    assert abs(total - TOTAL_EXPECTED) <= TOTAL_EXPECTED * 0.02
