import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import ReferenceItem, User
from app.schemas import ReferenceItemBase, ReferenceItemOut

reference_router = APIRouter(prefix="/reference-items", tags=["reference-items"])


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
