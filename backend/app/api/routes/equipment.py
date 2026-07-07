import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import Equipment, User
from app.schemas import EquipmentBase, EquipmentOut, EquipmentUpdate

equipment_router = APIRouter(prefix="/equipment", tags=["equipment"])


def _equipment_out(item: Equipment) -> EquipmentOut:
    return EquipmentOut(
        id=item.id,
        sap_code=item.sap_code,
        specifications=item.specifications,
        length_cm=item.length_cm,
        width_cm=item.width_cm,
        height_cm=item.height_cm,
        weight_kg=item.weight_kg,
        aliases=json.loads(item.aliases_json or "[]"),
        language_labels=json.loads(item.language_labels_json or "{}"),
        source=item.source,
        notes=item.notes,
        active=item.active,
    )


@equipment_router.get("", response_model=list[EquipmentOut])
def list_equipment(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Equipment).order_by(Equipment.specifications).all()
    return [_equipment_out(i) for i in items]


@equipment_router.post("", response_model=EquipmentOut)
def create_equipment(
    payload: EquipmentBase,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = Equipment(
        sap_code=payload.sap_code,
        specifications=payload.specifications,
        length_cm=payload.length_cm,
        width_cm=payload.width_cm,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        aliases_json=json.dumps(payload.aliases),
        language_labels_json=json.dumps(payload.language_labels),
        source=payload.source,
        notes=payload.notes,
        active=payload.active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _equipment_out(item)


@equipment_router.patch("/{item_id}", response_model=EquipmentOut)
def update_equipment(
    item_id: int,
    payload: EquipmentUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(Equipment).filter(Equipment.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    data = payload.model_dump(exclude_unset=True)
    aliases = data.pop("aliases", None)
    labels = data.pop("language_labels", None)
    for key, value in data.items():
        setattr(item, key, value)
    if aliases is not None:
        item.aliases_json = json.dumps(aliases)
    if labels is not None:
        item.language_labels_json = json.dumps(labels)
    db.commit()
    db.refresh(item)
    return _equipment_out(item)


@equipment_router.delete("/{item_id}")
def delete_equipment(item_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Equipment).filter(Equipment.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
