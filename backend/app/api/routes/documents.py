from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import DocumentExportRequest, UnCardsRequest
from app.services.documents import (
    build_un_cards_zip,
    fill_pdf_document,
    get_document,
    get_registry,
    has_pdf_template,
    render_document_pdf,
    un_card_count,
    un_cards_availability,
    validate_document,
)
from app.services import regulations
from app.services.documents.avc_form import fill_avc_waybill, has_avc_template
from app.services.documents.signature import decode_signature_image
from app.services.settings_store import instance_settings

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/registry")
def document_registry(user: User = Depends(get_current_user)):
    return get_registry()


@router.post("/validate")
def validate(payload: DocumentExportRequest, user: User = Depends(get_current_user)):
    document = get_document(payload.document_key)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document")
    errors, warnings = validate_document(
        document, payload.values, payload.lines, payload.dangerous_goods, payload.output_language
    )
    return {"document_key": payload.document_key, "errors": errors, "warnings": warnings}


@router.post("/export")
def export(
    payload: DocumentExportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    document = get_document(payload.document_key)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document")
    exporter = document.get("exporter")
    errors, _warnings = validate_document(
        document, payload.values, payload.lines, payload.dangerous_goods, payload.output_language
    )
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    signature_png = None
    if payload.signature_image:
        try:
            signature_png = decode_signature_image(payload.signature_image)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    ref = datetime.now().strftime("%Y%m%d%H%M%S")
    if exporter == "pdf_template" and has_pdf_template(payload.document_key):
        # Officieel, invulbaar formulier: template invullen.
        out_path = fill_pdf_document(
            payload.document_key,
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            signature_png=signature_png,
        )
    elif exporter == "avc" and has_avc_template():
        # AVC waybill: filling in the official sVa form. That form has no
        # AcroForm fields, so the values go on as a text layer over the
        # template.
        out_path = fill_avc_waybill(
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            signature_png=signature_png,
        )
    else:
        # Self-designed document: generate a clean PDF.
        out_path = render_document_pdf(
            document,
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
            signature_png=signature_png,
        )
    background_tasks.add_task(_delete_file, out_path)
    return FileResponse(
        path=out_path,
        filename=f"{payload.document_key}_{ref}.pdf",
        media_type="application/pdf",
    )


@router.get("/instructions")
def instructions_overview(user: User = Depends(get_current_user)):
    """What this installation can hand a driver or a boatmaster under 5.4.3.

    Per regime and language, because the model is only ever offered as the
    edition prints it: a language the store cannot produce is reported as
    missing with the document that would produce it, never filled in from a
    neighbouring language.
    """
    return {"documents": [
        regulations.instruction_status(doc["model_of"]["regime"],
                                       doc["model_of"]["language"])
        for doc in regulations.instruction_documents()]}


@router.get("/instructions/{regime}/{language}")
def instructions_file(regime: str, language: str,
                      user: User = Depends(get_current_user)):
    if regime not in regulations.REGIMES or language not in regulations.LANGUAGES:
        raise HTTPException(status_code=404, detail="Unknown regime or language")
    status = regulations.instruction_status(regime, language)
    if not status.get("available"):
        raise HTTPException(status_code=409, detail=status)
    path = regulations.instructions_pdf(regime, language)
    if path is None:  # pragma: no cover - the status said it was there
        raise HTTPException(status_code=409, detail=status)
    return FileResponse(
        path, media_type="application/pdf",
        filename=f"{regime}-2025-instructions-{language}.pdf")


@router.post("/un-cards/availability")
def un_cards_status(
    payload: UnCardsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Which UN cards this shipment can be given, before offering the download."""
    status = un_cards_availability(payload.dangerous_goods)
    if not instance_settings(db).un_cards_enabled:
        # Switched off for this installation. Reported the same way as a missing
        # card library, so the wizard simply does not offer the download.
        return {**status, "enabled": False, "available": [], "count": 0, "library_size": 0}
    return {**status, "library_size": un_card_count()}


@router.post("/un-cards")
def export_un_cards(
    payload: UnCardsRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A zip with the UN cards for the substances in this shipment."""
    if not instance_settings(db).un_cards_enabled:
        raise HTTPException(status_code=404, detail="UN cards are disabled for this installation")
    try:
        out_path, status = build_un_cards_zip(payload.dangerous_goods)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    background_tasks.add_task(_delete_file, out_path)
    ref = datetime.now().strftime("%Y%m%d%H%M%S")
    return FileResponse(
        path=out_path,
        filename=f"un_cards_{ref}.zip",
        media_type="application/zip",
        headers={"X-UN-Cards-Count": str(status["count"])},
    )


def _delete_file(path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
