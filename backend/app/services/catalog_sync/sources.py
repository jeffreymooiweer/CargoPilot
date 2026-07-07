from pathlib import Path

STEEL_PROFILES_REPO = "timskovjacobsen/steelprofiles_api"
STEEL_PROFILES_BRANCH = "main"
STEEL_PROFILE_TYPES = ("UPN", "IPE", "HEA", "HEB", "HEM", "IPN")

EUROCODEPY_REPO = "kristapsfreibergs/eurocodepy"
EUROCODEPY_BRANCH = "master"
EUROCODE_DATA_BASE = (
    f"https://raw.githubusercontent.com/{EUROCODEPY_REPO}/{EUROCODEPY_BRANCH}/src/eurocodepy/data"
)
EUROCODE_MATERIALS_URL = f"{EUROCODE_DATA_BASE}/eurocodes.json"

HOLLOW_PROFILE_FILES = ("shs_profiles_euro", "rhs_profiles_euro", "chs_profiles_euro")

STEEL_PROFILE_SOURCE = f"github:{STEEL_PROFILES_REPO} (EN 10365, kg/m kolom G)"
EUROCODE_MATERIAL_SOURCE = f"github:{EUROCODEPY_REPO} (Eurocode materiaalparameters)"
EUROCODE_HOLLOW_SOURCE = f"github:{EUROCODEPY_REPO} (EN 10210/10219 hollow sections)"


def steel_profile_remote_url(profile_type: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{STEEL_PROFILES_REPO}/{STEEL_PROFILES_BRANCH}"
        f"/assets/{profile_type}.csv"
    )


def eurocode_hollow_remote_url(name: str) -> str:
    return f"{EUROCODE_DATA_BASE}/{name}.json"


def bundled_steel_csv(profile_type: str, seed_dir: Path) -> Path:
    return seed_dir / "external" / "steel" / f"{profile_type}.csv"


def bundled_eurocode_materials(seed_dir: Path) -> Path:
    return seed_dir / "external" / "eurocode_materials.json"


def bundled_eurocode_hollow(seed_dir: Path, name: str) -> Path:
    return seed_dir / "external" / "eurocode" / f"{name}.json"


def bundled_seed_materials(seed_dir: Path) -> Path:
    return seed_dir / "materials.json"
