import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import Material, Profile, ReferenceItem, User
from app.schemas import MaterialBase, MaterialOut, ProfileBase, ProfileOut, ReferenceItemBase, ReferenceItemOut

materials_router = APIRouter(prefix="/materials", tags=["materials"])
profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])
reference_router = APIRouter(prefix="/reference-items", tags=["reference-items"])


def _material_out(m: Material) -> MaterialOut:
    return MaterialOut(
        id=m.id,
        canonical_name=m.canonical_name,
        category=m.category,
        density_kg_m3=m.density_kg_m3,
        density_min_kg_m3=m.density_min_kg_m3,
        density_max_kg_m3=m.density_max_kg_m3,
        unit=m.unit,
        condition=m.condition,
        language_labels=json.loads(m.language_labels_json or "{}"),
        aliases=json.loads(m.aliases_json or "[]"),
        source=m.source,
        notes=m.notes,
        active=m.active,
    )


@materials_router.get("", response_model=list[MaterialOut])
def list_materials(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_material_out(m) for m in db.query(Material).order_by(Material.canonical_name).all()]


@materials_router.post("", response_model=MaterialOut)
def create_material(payload: MaterialBase, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = Material(
        canonical_name=payload.canonical_name,
        category=payload.category,
        density_kg_m3=payload.density_kg_m3,
        density_min_kg_m3=payload.density_min_kg_m3,
        density_max_kg_m3=payload.density_max_kg_m3,
        unit=payload.unit,
        condition=payload.condition,
        language_labels_json=json.dumps(payload.language_labels),
        aliases_json=json.dumps(payload.aliases),
        source=payload.source,
        notes=payload.notes,
        active=payload.active,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _material_out(m)


@materials_router.patch("/{material_id}", response_model=MaterialOut)
def update_material(
    material_id: int,
    payload: MaterialBase,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Not found")
    m.canonical_name = payload.canonical_name
    m.category = payload.category
    m.density_kg_m3 = payload.density_kg_m3
    m.density_min_kg_m3 = payload.density_min_kg_m3
    m.density_max_kg_m3 = payload.density_max_kg_m3
    m.unit = payload.unit
    m.condition = payload.condition
    m.language_labels_json = json.dumps(payload.language_labels)
    m.aliases_json = json.dumps(payload.aliases)
    m.source = payload.source
    m.notes = payload.notes
    m.active = payload.active
    db.commit()
    db.refresh(m)
    return _material_out(m)


def _profile_out(p: Profile) -> ProfileOut:
    return ProfileOut(
        id=p.id,
        profile_type=p.profile_type,
        size_label=p.size_label,
        kg_per_meter=p.kg_per_meter,
        material=p.material,
        standard=p.standard,
        aliases=json.loads(p.aliases_json or "[]"),
        source=p.source,
        notes=p.notes,
        active=p.active,
    )


@profiles_router.get("", response_model=list[ProfileOut])
def list_profiles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_profile_out(p) for p in db.query(Profile).order_by(Profile.profile_type, Profile.size_label).all()]


@profiles_router.post("", response_model=ProfileOut)
def create_profile(payload: ProfileBase, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    p = Profile(
        profile_type=payload.profile_type,
        size_label=payload.size_label,
        kg_per_meter=payload.kg_per_meter,
        material=payload.material,
        standard=payload.standard,
        aliases_json=json.dumps(payload.aliases),
        source=payload.source,
        notes=payload.notes,
        active=payload.active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _profile_out(p)


@profiles_router.patch("/{profile_id}", response_model=ProfileOut)
def update_profile(
    profile_id: int,
    payload: ProfileBase,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(Profile).filter(Profile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    p.profile_type = payload.profile_type
    p.size_label = payload.size_label
    p.kg_per_meter = payload.kg_per_meter
    p.material = payload.material
    p.standard = payload.standard
    p.aliases_json = json.dumps(payload.aliases)
    p.source = payload.source
    p.notes = payload.notes
    p.active = payload.active
    db.commit()
    db.refresh(p)
    return _profile_out(p)


def _reference_out(r: ReferenceItem) -> ReferenceItemOut:
    return ReferenceItemOut(
        id=r.id,
        canonical_name=r.canonical_name,
        category=r.category,
        reference_weight_kg=r.reference_weight_kg,
        reference_volume_m3=r.reference_volume_m3,
        aliases=json.loads(r.aliases_json or "[]"),
        language_labels=json.loads(r.language_labels_json or "{}"),
        notes=r.notes,
        active=r.active,
    )


@reference_router.get("", response_model=list[ReferenceItemOut])
def list_reference_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_reference_out(r) for r in db.query(ReferenceItem).order_by(ReferenceItem.canonical_name).all()]


@reference_router.post("", response_model=ReferenceItemOut)
def create_reference_item(
    payload: ReferenceItemBase,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    r = ReferenceItem(
        canonical_name=payload.canonical_name,
        category=payload.category,
        reference_weight_kg=payload.reference_weight_kg,
        reference_volume_m3=payload.reference_volume_m3,
        aliases_json=json.dumps(payload.aliases),
        language_labels_json=json.dumps(payload.language_labels),
        notes=payload.notes,
        active=payload.active,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _reference_out(r)
