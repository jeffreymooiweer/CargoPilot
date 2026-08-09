"""Wat er niet meer is, moet niet stilletjes terugkomen.

De opruiming van v1.43.0 haalde vier ongebruikte functies, vier ongebruikte
schema's, twaalf ongebruikte imports en twee scripts weg. Zulke dingen groeien
vanzelf terug: een functie wordt geschreven voor een aanroeper die er nooit
komt, een import blijft staan als de code eronder verdwijnt, en niets valt om.

Twee van die vondsten waren meer dan opruimen:

**`calc_solid_block` had geen enkele aanroeper.** De rekenkern draagt een
functie voor het massieve blok, en de pijplijn rekende het op twee plaatsen zelf
uit — `w * h * length_m`, en dan maal de dichtheid. Dezelfde formule op drie
plaatsen, waarvan twee buiten bereik van de tests die de rekenkern controleren.
Precies het patroon dat dit project al vier keer heeft gekost: de fout zit op de
naad, en een functie die niemand aanroept is een naad die niemand ziet.

**`amendment_42_24.py` werd tijdens het opruimen per ongeluk afgekapt.** Een
verwijdering zonder eindgrens nam alles mee wat erachter stond, inclusief
`not_covered()`. 117 tests vielen om en de fout was binnen een minuut gevonden.
Dat is precies waar die suite voor is, en het is het vermelden waard: het
gevaarlijke aan opruimen is niet wat je weghaalt maar wat je per ongeluk
meeneemt.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

REMOVED_SYMBOLS = [
    ("app/core/security.py", "decode_access_token"),
    ("app/services/dg/amendment_42_24.py", "stowage_code_text"),
    ("app/services/documents/un_cards.py", "manifest_summary"),
    ("app/schemas/__init__.py", "MaterialOut"),
    ("app/schemas/__init__.py", "ProfileOut"),
]

REMOVED_SCRIPTS = ["cleanup-dockerhub-tags.sh", "purge-history.sh"]


def top_level_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


@pytest.mark.parametrize("relative,symbol", REMOVED_SYMBOLS)
def test_een_opgeruimd_symbool_blijft_weg(relative, symbol):
    """Terug mag — maar dan met een aanroeper, niet als vergeten restant."""
    assert symbol not in top_level_names(BACKEND / relative)


@pytest.mark.parametrize("name", REMOVED_SCRIPTS)
def test_een_opgeruimd_script_blijft_weg(name):
    assert not (ROOT / "scripts" / name).exists()


def test_de_pijplijn_rekent_het_massieve_blok_via_de_rekenkern():
    """Eén formule op één plek, en die plek heeft tests.

    De pijplijn mag `w * h * length` niet opnieuw uitschrijven; daar hoort
    `calc_solid_block` voor te worden aangeroepen, net als bij de ronde staaf,
    de buis en het hoekprofiel.
    """
    source = (BACKEND / "app/services/pipeline.py").read_text(encoding="utf-8")

    assert "calc_solid_block(" in source
    assert "material_vol = w * h * length_m" not in source


def test_de_rekenkern_wordt_ook_werkelijk_gebruikt():
    """Elke calc_-functie in de engine heeft een aanroeper buiten de engine.

    Dit is de generieke versie van de vorige test, en de reden dat hij bestaat:
    `calc_round_bar` en `calc_round_tube` stonden er in v1.37.0 ook al zonder
    aanroeper, en dat kostte een ronde staaf 27% te veel gewicht.
    """
    engine = BACKEND / "app/services/calculator/engine.py"
    formulas = {n for n in top_level_names(engine) if n.startswith("calc_")}

    callers = "".join(
        path.read_text(encoding="utf-8")
        for path in (BACKEND / "app").rglob("*.py")
        if path != engine
    )
    unused = sorted(name for name in formulas if f"{name}(" not in callers)

    assert unused == [], f"geen aanroeper buiten de rekenkern: {unused}"


def test_er_staan_geen_ongebruikte_imports_meer_in_de_applicatie():
    """Pyflakes over backend/app; ontbreekt het gereedschap, dan slaan we over."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pyflakes", str(BACKEND / "app")],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):  # pragma: no cover
        pytest.skip("pyflakes niet beschikbaar")
    if "No module named" in result.stderr:  # pragma: no cover
        pytest.skip("pyflakes niet geïnstalleerd")

    findings = [line for line in result.stdout.splitlines() if "imported but unused" in line]

    assert findings == []
