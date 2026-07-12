from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import DocumentExportRequest
from app.services.documents import (
    export_document,
    fill_pdf_document,
    get_document,
    get_registry,
    has_pdf_template,
    validate_document,
)

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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
    if exporter not in {"generic", "pdf_template"}:
        raise HTTPException(status_code=400, detail="Use /export for the appendix template")
    errors, _warnings = validate_document(
        document, payload.values, payload.lines, payload.dangerous_goods, payload.output_language
    )
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    ref = datetime.now().strftime("%Y%m%d%H%M%S")
    if exporter == "pdf_template" and has_pdf_template(payload.document_key):
        out_path = fill_pdf_document(
            payload.document_key,
            payload.values,
            payload.lines,
            payload.dangerous_goods,
            payload.output_language,
        )
        background_tasks.add_task(_delete_file, out_path)
        return FileResponse(
            path=out_path,
            filename=f"{payload.document_key}_{ref}.pdf",
            media_type="application/pdf",
        )

    out_path = export_document(
        payload.document_key,
        payload.values,
        payload.lines,
        payload.dangerous_goods,
        payload.output_language,
    )
    background_tasks.add_task(_delete_file, out_path)
    return FileResponse(
        path=out_path,
        filename=f"{payload.document_key}_{ref}.xlsx",
        media_type=XLSX_MEDIA,
    )


def _delete_file(path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
