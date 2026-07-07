from pathlib import Path

STEEL_PROFILES_REPO = "timskovjacobsen/steelprofiles_api"
STEEL_PROFILES_BRANCH = "main"
STEEL_PROFILE_TYPES = ("UPN", "IPE", "HEA", "HEB", "HEM", "IPN")

EUROCODEPY_REPO = "kristapsfreibergs/eurocodepy"
EUROCODEPY_BRANCH = "master"
EUROCODE_MATERIALS_URL = (
    f"https://raw.githubusercontent.com/{EUROCODEPY_REPO}/{EUROCODEPY_BRANCH}"
    "/src/eurocodepy/data/eurocodes.json"
)

STEEL_PROFILE_SOURCE = f"github:{STEEL_PROFILES_REPO} (EN 10365, kg/m kolom G)"
EUROCODE_MATERIAL_SOURCE = f"github:{EUROCODEPY_REPO} (Eurocode materiaalparameters)"


def steel_profile_remote_url(profile_type: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{STEEL_PROFILES_REPO}/{STEEL_PROFILES_BRANCH}"
        f"/assets/{profile_type}.csv"
    )


def bundled_steel_csv(profile_type: str, seed_dir: Path) -> Path:
    return seed_dir / "external" / "steel" / f"{profile_type}.csv"


def bundled_eurocode_materials(seed_dir: Path) -> Path:
    return seed_dir / "external" / "eurocode_materials.json"
