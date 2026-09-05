"""The shipment history: keeping, listing and letting go.

Everything else in CargoPilot forgets a shipment the moment its papers are
downloaded. This module is the one place that remembers, and it does so only
when ``CARGOPILOT_HISTORY=true`` in the organisation application — the routes
that call it are not mounted otherwise, and :func:`enforce_switch` at start-up
makes sure a database cannot hold shipments the running application refuses
to acknowledge.

**Switching the history off destroys data, and says so first.** An
installation with shipments in its table and the switch off refuses to start:
it names the count and the second variable, ``CARGOPILOT_HISTORY_DISCARD``,
that discards them. Refusing is loud and destroys nothing by default; a table
kept while the interface claims it does not exist would be the one outcome
worse than either choice.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.history import ShipmentDetail, ShipmentIn, ShipmentSummary
from app.services import departments
from app.services.documents.shipment_export import build_shipment_export

logger = logging.getLogger(__name__)

#: What one kept shipment may weigh, all three documents together. A
#: signature is tens of kilobytes; a large consignment's bundle a few hundred.
#: Four megabytes is not a shipment.
MAX_RECORD_BYTES = 4 * 1024 * 1024

PER_PAGE_MAX = 100


class HistoryLeftBehind(SystemExit):
    """Shipments in the database and no switch to serve them."""


class RecordTooLarge(ValueError):
    """More than :data:`MAX_RECORD_BYTES` of snapshot, bundle and export."""


# --- start-up ----------------------------------------------------------------


def count(db: Session) -> int:
    return int(db.query(func.count(Shipment.id)).scalar() or 0)


def enforce_switch(db: Session) -> None:
    """Refuse to run with shipments, or trips, the switch no longer covers."""
    from app.services import trips

    settings = get_settings()
    if settings.history_enabled:
        return
    left = count(db)
    left_trips = trips.count(db)
    if not left and not left_trips:
        return
    if settings.cargopilot_history_discard:
        db.query(Shipment).delete()
        db.commit()
        trips.discard_all(db)
        logger.warning("Shipment history switched off: discarded %s kept shipment(s) "
                       "and %s kept trip(s) as CARGOPILOT_HISTORY_DISCARD=true asked",
                       left, left_trips)
        return
    raise HistoryLeftBehind(
        f"Refusing to start: the database holds {left} kept shipment(s) and "
        f"{left_trips} kept trip(s) but CARGOPILOT_HISTORY is off. Either set "
        "CARGOPILOT_HISTORY=true to keep serving them, or set "
        "CARGOPILOT_HISTORY_DISCARD=true as well to delete them on the next "
        "start. Nothing has been deleted.")


# --- keeping -----------------------------------------------------------------


def _index(record: Shipment, export: dict[str, Any], payload: ShipmentIn) -> None:
    consignment = export.get("consignment") or {}
    # The wizard's field is shipment_reference; "reference" is read as well for
    # exports written by hand or by an older reader. Until v1.176.0 only the
    # latter was read, so every kept shipment listed as "(no reference)".
    record.reference = str(consignment.get("shipment_reference")
                           or consignment.get("reference") or "")[:120]
    record.consignor_name = str(consignment.get("consignor_name") or "")[:255]
    record.consignee_name = str(consignment.get("consignee_name") or "")[:255]
    record.modality = (payload.modality or "")[:16]
    record.language = (payload.language or "nl")[:8]
    record.regulations = ",".join(export.get("regulations") or [])[:64]
    record.goods_count = sum(1 for line in payload.lines if line.get("include", True))
    record.has_dangerous_goods = bool(payload.dangerous_goods)


def keep(db: Session, user: User, payload: ShipmentIn,
         existing: Shipment | None = None) -> Shipment:
    """Keep a shipment — a new row, or the same row brought up to date."""
    export = build_shipment_export(
        payload.values, payload.lines, payload.dangerous_goods,
        language=payload.language, profiles=payload.profiles,
        modality=payload.modality or None, documents=payload.documents or None)
    snapshot_json = json.dumps(payload.snapshot, ensure_ascii=False)
    bundle_json = (json.dumps(payload.bundle.model_dump(), ensure_ascii=False)
                   if payload.bundle and payload.bundle.documents else None)
    export_json = json.dumps(export, ensure_ascii=False)
    size = len(snapshot_json) + len(bundle_json or "") + len(export_json)
    if size > MAX_RECORD_BYTES:
        raise RecordTooLarge(
            f"The shipment is {size / 1024 / 1024:.1f} MB, more than the "
            f"{MAX_RECORD_BYTES // 1024 // 1024} MB one kept shipment may be.")

    # The keeper's department is copied at the moment of keeping and never
    # moved afterwards: whose work it was, not whose it would be today.
    record = existing or Shipment(created_by_id=user.id if user.id else None,
                                  department_id=getattr(user, "department_id", None))
    _index(record, export, payload)
    record.snapshot_json = snapshot_json
    record.bundle_json = bundle_json
    record.export_json = export_json
    if existing is None:
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


def forget(db: Session, record: Shipment) -> None:
    db.delete(record)
    db.commit()


# --- reading -----------------------------------------------------------------


def _loads(text: str | None) -> dict[str, Any]:
    try:
        value = json.loads(text or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def summary(record: Shipment) -> ShipmentSummary:
    return ShipmentSummary(
        id=record.id,
        reference=record.reference,
        modality=record.modality,
        language=record.language,
        regulations=[r for r in (record.regulations or "").split(",") if r],
        consignor_name=record.consignor_name,
        consignee_name=record.consignee_name,
        goods_count=record.goods_count,
        has_dangerous_goods=record.has_dangerous_goods,
        has_documents=bool(record.bundle_json),
        created_by=record.creator.username if record.creator else "",
        department_id=record.department_id,
        department=record.department.name if record.department else "",
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def detail(record: Shipment) -> ShipmentDetail:
    return ShipmentDetail(
        **summary(record).model_dump(),
        snapshot=_loads(record.snapshot_json),
        export=_loads(record.export_json),
    )


def bundle_of(record: Shipment) -> dict[str, Any] | None:
    return _loads(record.bundle_json) if record.bundle_json else None


def search(db: Session, viewer: User, q: str = "", modality: str = "",
           date_from: datetime | None = None, date_to: datetime | None = None,
           page: int = 1, per_page: int = 25,
           department: str = "") -> tuple[list[Shipment], int]:
    """The page of shipments ``viewer`` may see that match the filters,
    newest first, and the total across all pages."""
    query = departments.visible_to(db.query(Shipment), viewer, department)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        query = query.filter(or_(Shipment.reference.ilike(like),
                                 Shipment.consignor_name.ilike(like),
                                 Shipment.consignee_name.ilike(like)))
    if modality:
        query = query.filter(Shipment.modality == modality)
    if date_from:
        query = query.filter(Shipment.created_at >= date_from)
    if date_to:
        query = query.filter(Shipment.created_at <= date_to)
    total = query.count()
    per_page = max(1, min(int(per_page), PER_PAGE_MAX))
    page = max(1, int(page))
    rows = (query.order_by(Shipment.created_at.desc(), Shipment.id.desc())
            .offset((page - 1) * per_page).limit(per_page).all())
    return rows, total
