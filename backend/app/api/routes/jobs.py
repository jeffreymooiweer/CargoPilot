from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import CalculateRequest, ExportRequest, ParseRequest
from app.services.documents import render_appendix_pdf
from app.services.exporter.appendix_exporter import export_appendix
from app.services.pipeline import parse_and_calculate

router = APIRouter(tags=["workflow"])


@router.post("/parse")
def parse_text(payload: ParseRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return parse_and_calculate(
        payload.text,
        db,
        column_map=payload.column_map,
        has_header=payload.has_header,
        input_language=payload.input_language,
        mode="continue",
    )


@router.post("/calculate")
def calculate(payload: CalculateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.lines:
        result = {
            "success": True,
            "column_map": payload.column_map or {},
            "lines": payload.lines,
            "totals": {},
            "errors": [],
        }
        included = [line for line in payload.lines if line.get("include", True)]
        result["totals"] = {
            "line_count": len(payload.lines),
            "included_count": len(included),
            "total_quantity": sum(line.get("quantity") or 0 for line in included),
            "total_weight_kg": round(sum(line.get("weight_total_kg") or 0 for line in included), 2),
            "total_material_volume_m3": round(sum(line.get("material_volume_m3") or 0 for line in included), 6),
            "total_transport_volume_m3": round(sum(line.get("transport_volume_m3") or 0 for line in included), 6),
            "warning_count": sum(1 for line in payload.lines if line.get("status") in {"warning", "needs_review"}),
            "error_count": sum(1 for line in payload.lines if line.get("status") == "error"),
        }
        return result
    if not payload.text:
        raise HTTPException(status_code=400, detail="text or lines required")
    return parse_and_calculate(
        payload.text,
        db,
        column_map=payload.column_map,
        has_header=payload.has_header,
        input_language=payload.input_language,
        output_language=payload.output_language,
        mode=payload.mode,
        line_overrides=payload.line_overrides,
    )


@router.post("/export")
def export_appendix_file(
    payload: ExportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    if not payload.lines:
        raise HTTPException(status_code=400, detail="lines required")
    ref = f"cp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    if payload.format == "pdf":
        out_path = render_appendix_pdf(
            payload.lines,
            payload.dangerous_goods,
            payload.metadata,
            payload.output_language,
        )
        background_tasks.add_task(_delete_file, out_path)
        return FileResponse(path=out_path, filename=f"appendix_{ref}.pdf", media_type="application/pdf")
    out_path = export_appendix(
        payload.lines,
        payload.metadata,
        payload.output_language,
        job_ref=ref,
        template_name=payload.template_name,
        dangerous_goods=payload.dangerous_goods,
    )
    background_tasks.add_task(_delete_file, out_path)
    return FileResponse(
        path=out_path,
        filename=f"appendix_{ref}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _delete_file(path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
