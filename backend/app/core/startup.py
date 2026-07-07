import json
import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.core.config import get_settings as _get_settings
from app.models.user import Material, Profile, ReferenceItem, User
from app.services.catalog_sync import sync_catalogs

logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    settings = get_settings()
    for path in [settings.data_dir, settings.templates_dir, settings.exports_dir, settings.logs_dir]:
        path.mkdir(parents=True, exist_ok=True)
    template_name = "Appendix_A1D_template.xlsx"
    dest = settings.templates_dir / template_name
    if not dest.exists():
        candidates = [
            Path("/workspace/templates") / template_name,
            settings.repo_templates_dir.resolve() / template_name,
        ]
        for src in candidates:
            if src.exists():
                shutil.copy2(src, dest)
                logger.info("Copied template to %s", dest)
                break


def seed_catalogs(db: Session) -> None:
    settings = get_settings()
    if db.query(Material).count() == 0:
        materials_path = settings.seed_dir / "materials.json"
        for item in json.loads(materials_path.read_text(encoding="utf-8")):
            db.add(
                Material(
                    canonical_name=item["canonical_name"],
                    category=item["category"],
                    density_kg_m3=item["density_kg_m3"],
                    density_min_kg_m3=item.get("density_min_kg_m3"),
                    density_max_kg_m3=item.get("density_max_kg_m3"),
                    condition=item.get("condition"),
                    language_labels_json=json.dumps(item.get("language_labels", {})),
                    aliases_json=json.dumps(item.get("aliases", [])),
                    source=item.get("source"),
                    notes=item.get("notes"),
                )
            )
    if db.query(Profile).count() == 0:
        for item in json.loads((settings.seed_dir / "profiles.json").read_text(encoding="utf-8")):
            db.add(
                Profile(
                    profile_type=item["profile_type"],
                    size_label=item["size_label"],
                    kg_per_meter=item["kg_per_meter"],
                    material=item.get("material", "steel"),
                    standard=item.get("standard"),
                    aliases_json=json.dumps(item.get("aliases", [])),
                    source=item.get("source"),
                    notes=item.get("notes"),
                )
            )
    if db.query(ReferenceItem).count() == 0:
        for item in json.loads((settings.seed_dir / "reference_items.json").read_text(encoding="utf-8")):
            db.add(
                ReferenceItem(
                    canonical_name=item["canonical_name"],
                    category=item.get("category", "electrical"),
                    reference_weight_kg=item["reference_weight_kg"],
                    reference_volume_m3=item.get("reference_volume_m3"),
                    aliases_json=json.dumps(item.get("aliases", [])),
                    language_labels_json=json.dumps(item.get("language_labels", {})),
                    notes=item.get("notes"),
                )
            )
    db.commit()


def bootstrap_admin(db: Session) -> bool:
    settings = get_settings()
    admin = db.query(User).filter(User.role == "admin").first()
    if admin:
        return True
    if settings.admin_username and settings.admin_email and settings.admin_password:
        db.add(
            User(
                username=settings.admin_username,
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                active=True,
            )
        )
        db.commit()
        logger.info("Bootstrap admin created: %s", settings.admin_username)
        return True
    logger.warning("No admin exists and ADMIN_* env vars are not set")
    return False


def sync_catalogs_on_startup(db: Session) -> None:
    settings = _get_settings()
    if not settings.catalog_auto_sync:
        logger.info("Catalog auto-sync disabled (CATALOG_AUTO_SYNC=false)")
        return
    try:
        sync_catalogs(db)
    except Exception:
        logger.exception("Catalog sync failed during startup")


def init_app() -> bool:
    ensure_directories()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_catalogs(db)
        sync_catalogs_on_startup(db)
        return bootstrap_admin(db)
    finally:
        db.close()
