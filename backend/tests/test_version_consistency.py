"""Het versienummer staat op vier plaatsen en die moeten het eens zijn.

Dit is geen theoretisch risico. Een externe review van CargoPilot kwam met een
lijst problemen die grotendeels al opgelost waren, omdat de reviewer
`frontend/package.json` op 1.14.1 zag terwijl de rest van het project al ver
daarvoorbij was. Uren werk aan bevindingen die niet meer bestonden.

Eén plek die achterblijft is ook operationeel vervelend: `GET /api/health`
meldt dan een andere versie dan de Docker-tag, en een gebruiker die een bug
meldt geeft een nummer op dat niet klopt met de code waar de bug in zit.
"""

import json
import re
from pathlib import Path

from app.version import get_version

ROOT = Path(__file__).resolve().parents[2]

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def test_the_four_places_the_version_lives_agree():
    root_version = read(ROOT / "VERSION")
    backend_version = read(ROOT / "backend" / "VERSION")
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))

    assert SEMVER.match(root_version), f"VERSION is geen semver: {root_version!r}"
    assert backend_version == root_version, (
        f"backend/VERSION ({backend_version}) loopt achter op VERSION ({root_version})"
    )
    assert package["version"] == root_version, (
        f"frontend/package.json ({package['version']}) loopt achter op "
        f"VERSION ({root_version})"
    )
    # Wat de applicatie zelf uitdraagt — dit is het nummer dat in een bugmelding
    # terechtkomt.
    assert get_version() == root_version


def test_the_changelog_documents_the_current_version():
    """Een versiebump zonder changelog-regel is een release waarvan niemand
    kan zien wat erin zit."""
    version = read(ROOT / "VERSION")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{version}]" in changelog, (
        f"CHANGELOG.md heeft geen kop voor {version}"
    )


def test_the_changelog_leads_with_the_current_version():
    """De nieuwste versie hoort bovenaan; anders is een oudere kop blijven
    staan of is er onder de verkeerde kop geschreven."""
    version = read(ROOT / "VERSION")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## \[([^\]]+)\]", changelog, re.M)
    assert headings, "CHANGELOG.md heeft geen versiekoppen"
    assert headings[0] == version, (
        f"bovenste changelog-kop is {headings[0]}, verwacht {version}"
    )
