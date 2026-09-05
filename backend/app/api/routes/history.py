"""The shipments page's routes.

Mounted only when ``CARGOPILOT_HISTORY=true`` in the organisation
application — see ``main.py``. Everywhere else these addresses do not exist,
which is how the promise "nothing is kept" is enforced rather than described.

Every signed-in user of the organisation sees every kept shipment. The
roadmap's departments — who sees whose — are the next phase and will narrow
this; until then the organisation is the unit.
"""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.documents import build_bundle, delete_file
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import DOCUMENT_BUNDLE, limiter
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas import DocumentBundleRequest
from app.schemas.history import ShipmentDetail, ShipmentIn, ShipmentPage, ShipmentSummary
from app.services import history

router = APIRouter(prefix="/shipments", tags=["shipments"])


def _record(shipment_id: int, db: Session) -> Shipment:
    record = db.get(Shipment, shipment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No such shipment")
    return record


@router.get("", response_model=ShipmentPage)
def list_shipments(
    q: str = Query(default="", max_length=120),
    modality: str = Query(default="", max_length=16),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=history.PER_PAGE_MAX),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows, total = history.search(db, q, modality, date_from, date_to, page, per_page)
    return ShipmentPage(items=[history.summary(r) for r in rows],
                        total=total, page=page, per_page=per_page)


@router.post("", response_model=ShipmentSummary)
def keep_shipment(payload: ShipmentIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    try:
        return history.summary(history.keep(db, user, payload))
    except history.RecordTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc


@router.put("/{shipment_id}", response_model=ShipmentSummary)
def update_shipment(shipment_id: int, payload: ShipmentIn,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    record = _record(shipment_id, db)
    try:
        return history.summary(history.keep(db, user, payload, existing=record))
    except history.RecordTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc


@router.get("/{shipment_id}", response_model=ShipmentDetail)
def get_shipment(shipment_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return history.detail(_record(shipment_id, db))


@router.get("/{shipment_id}/export.json")
def shipment_export(shipment_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """The structured export as it was kept — the record, not a re-render."""
    record = _record(shipment_id, db)
    name = f"cargopilot-shipment-{record.reference or record.id}.json"
    return JSONResponse(content=history.detail(record).export,
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/{shipment_id}/documents")
@limiter.limit(DOCUMENT_BUNDLE)
def shipment_documents(request: Request, shipment_id: int,
                       background_tasks: BackgroundTasks,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """The documents again, re-rendered from the kept bundle request.

    Rendered by the same code path as the export step's download, from the
    same payload — so what comes back is what went out, on today's build.
    A shipment kept without a ready document has nothing to re-render, and
    says so rather than handing over an empty archive.
    """
    record = _record(shipment_id, db)
    bundle = history.bundle_of(record)
    if not bundle or not bundle.get("documents"):
        raise HTTPException(status_code=404,
                            detail="This shipment was kept without ready documents.")
    bundle_path, ref = build_bundle(DocumentBundleRequest(**bundle), db)
    background_tasks.add_task(delete_file, bundle_path)
    return FileResponse(path=bundle_path,
                        filename=f"cargopilot-documents-{record.reference or ref}.zip",
                        media_type="application/zip")


@router.delete("/{shipment_id}")
def forget_shipment(shipment_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    history.forget(db, _record(shipment_id, db))
    return {"ok": True}
