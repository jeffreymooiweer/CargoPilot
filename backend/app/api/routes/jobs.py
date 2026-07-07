import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import Job, User
from app.schemas import CalculateRequest, ExportRequest, JobCreate, JobUpdate, ParseRequest
from app.services.exporter.appendix_exporter import export_appendix
from app.services.pipeline import parse_and_calculate

router = APIRouter(tags=["jobs"])


@router.post("/parse")
def parse_text(payload: ParseRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = parse_and_calculate(
        payload.text,
        db,
        column_map=payload.column_map,
        has_header=payload.has_header,
        input_language=payload.input_language,
        mode="continue",
    )
    return result


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
        included = [l for l in payload.lines if l.get("include", True)]
        result["totals"] = {
            "line_count": len(payload.lines),
            "included_count": len(included),
            "total_quantity": sum(l.get("quantity") or 0 for l in included),
            "total_weight_kg": round(sum(l.get("weight_total_kg") or 0 for l in included), 2),
            "total_material_volume_m3": round(sum(l.get("material_volume_m3") or 0 for l in included), 6),
            "total_transport_volume_m3": round(sum(l.get("transport_volume_m3") or 0 for l in included), 6),
            "warning_count": sum(1 for l in payload.lines if l.get("status") in {"warning", "needs_review"}),
            "error_count": sum(1 for l in payload.lines if l.get("status") == "error"),
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


@router.post("/jobs")
def create_job(payload: JobCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = parse_and_calculate(
        payload.text,
        db,
        column_map=payload.column_map,
        has_header=payload.has_header,
        input_language=payload.input_language,
        output_language=payload.output_language,
        mode=payload.mode,
    )
    job = Job(
        title=payload.title,
        status="review" if result["success"] else "error",
        input_raw=payload.text,
        parsed_json=json.dumps(result),
        calculated_json=json.dumps(result),
        metadata_json=json.dumps({"output_language": payload.output_language}),
        created_by_id=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job": _job_dict(job), "result": result}


@router.get("/jobs")
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.created_by_id == user.id).order_by(Job.id.desc()).limit(50).all()
    return [_job_dict(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = _get_job(job_id, user, db)
    return _job_dict(job, include_data=True)


@router.patch("/jobs/{job_id}")
def update_job(job_id: int, payload: JobUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = _get_job(job_id, user, db)
    if payload.title is not None:
        job.title = payload.title
    if payload.calculated_json is not None:
        job.calculated_json = json.dumps(payload.calculated_json)
    if payload.metadata_json is not None:
        job.metadata_json = json.dumps(payload.metadata_json)
    if payload.status is not None:
        job.status = payload.status
    db.commit()
    db.refresh(job)
    return _job_dict(job, include_data=True)


@router.post("/jobs/{job_id}/export")
def export_job(job_id: int, payload: ExportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = _get_job(job_id, user, db)
    data = json.loads(job.calculated_json or "{}")
    lines = data.get("lines", [])
    if not lines:
        raise HTTPException(status_code=400, detail="No calculated lines")
    meta = payload.metadata or {}
    stored_meta = json.loads(job.metadata_json or "{}")
    meta = {**stored_meta, **meta}
    out_path = export_appendix(
        lines,
        meta,
        payload.output_language,
        job_ref=f"job{job.id}",
        template_name=payload.template_name,
    )
    job.export_path = str(out_path)
    job.status = "exported"
    db.commit()
    return FileResponse(
        path=out_path,
        filename=out_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _get_job(job_id: int, user: User, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.created_by_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _job_dict(job: Job, include_data: bool = False) -> dict:
    data = {
        "id": job.id,
        "title": job.title,
        "status": job.status,
        "export_path": job.export_path,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
    if include_data:
        data["input_raw"] = job.input_raw
        data["calculated"] = json.loads(job.calculated_json or "{}")
        data["metadata"] = json.loads(job.metadata_json or "{}")
    else:
        calc = json.loads(job.calculated_json or "{}")
        data["totals"] = calc.get("totals", {})
    return data
