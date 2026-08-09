"""What is gone must not quietly come back.

The clear-out of v1.43.0 removed four unused functions, four unused schemas,
twelve unused imports and two scripts. Things like that grow back by themselves:
a function is written for a caller that never arrives, an import stays behind
when the code under it disappears, and nothing falls over.

Two of those findings were more than tidying:

**`calc_solid_block` had no caller at all.** The calculation engine carries a
function for the solid block, and the pipeline worked it out itself in two
places — `w * h * length_m`, and then times the density. The same formula in
three places, two of them out of reach of the tests that check the engine.
Exactly the pattern that has already cost this project four times over: the bug
sits on the seam, and a function nobody calls is a seam nobody sees.

**`amendment_42_24.py` was accidentally truncated during the clear-out.** A
removal without an end boundary took everything after it along, including
`not_covered()`. 117 tests fell over and the mistake was found within a minute.
That is exactly what that suite is for, and it is worth recording: the danger in
a clear-out is not what you remove but what you take along by accident.
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
    """Coming back is fine — but with a caller, not as a forgotten remnant."""
    assert symbol not in top_level_names(BACKEND / relative)


@pytest.mark.parametrize("name", REMOVED_SCRIPTS)
def test_een_opgeruimd_script_blijft_weg(name):
    assert not (ROOT / "scripts" / name).exists()


def test_de_pijplijn_rekent_het_massieve_blok_via_de_rekenkern():
    """One formula in one place, and that place has tests.

    The pipeline must not write out `w * h * length` again; `calc_solid_block`
    should be called for that, just as with the round bar, the tube and the
    angle.
    """
    source = (BACKEND / "app/services/pipeline.py").read_text(encoding="utf-8")

    assert "calc_solid_block(" in source
    assert "material_vol = w * h * length_m" not in source


def test_de_rekenkern_wordt_ook_werkelijk_gebruikt():
    """Every calc_ function in the engine has a caller outside the engine.

    This is the generic version of the previous test, and the reason it exists:
    `calc_round_bar` and `calc_round_tube` were sitting there without a caller in
    v1.37.0 too, and that cost a round bar 27% too much weight.
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
    """Pyflakes over backend/app; when the tool is missing, we skip."""
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
