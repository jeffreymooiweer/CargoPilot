import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import Equipment, User
from app.schemas import EquipmentBase, EquipmentOut, EquipmentUpdate
from app.services.equipment_import import EQUIPMENT_EXAMPLE, EQUIPMENT_HEADERS, import_equipment_rows
from app.services.spreadsheet_io import build_xlsx_template, read_tabular_file

equipment_router = APIRouter(prefix="/equipment", tags=["equipment"])


class EquipmentImportResultOut(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[str]


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


@equipment_router.get("/import-template")
def download_equipment_template(user: User = Depends(get_current_user)):
    content = build_xlsx_template(EQUIPMENT_HEADERS, EQUIPMENT_EXAMPLE, sheet_name="Materieel import")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="materieel_import_template.xlsx"'},
    )


@equipment_router.post("/import", response_model=EquipmentImportResultOut)
async def import_equipment_file(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Bestandsnaam ontbreekt")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Leeg bestand")
    rows = read_tabular_file(content, file.filename)
    result = import_equipment_rows(db, rows)
    if result.created == 0 and result.updated == 0 and not result.errors:
        raise HTTPException(status_code=400, detail="Geen importeerbare regels gevonden")
    return EquipmentImportResultOut(
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )


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
