from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import DbSession, OperatorAuth, get_current_user
from app.models.user import User
from app.models.export_job import ExportJob
from app.schemas.export import ExportCreate, ExportResponse
from app.services.audit_service import get_audit_service
from app.services.export_service import get_export_service
from app.services.reel_service import get_reel_service
from app.services.slideshow_service import get_slideshow_service

router = APIRouter(prefix="/exports", tags=["exports"])


def _to_response(job: ExportJob) -> ExportResponse:
    download_url = None
    if job.status == "completed" and job.output_path:
        download_url = f"/api/v1/exports/{job.id}/download"
    return ExportResponse(
        id=job.id,
        event_id=job.event_id,
        status=job.status,
        format=job.format,
        output_path=job.output_path,
        download_url=download_url,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.post("", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
def create_export(
    body: ExportCreate, db: DbSession, user: User = Depends(get_current_user)
) -> ExportResponse:
    options = None
    if body.message_ids:
        options = {"message_ids": [str(mid) for mid in body.message_ids]}
    job = ExportJob(
        event_id=body.event_id,
        format=body.format,
        status="queued",
        options_json=options,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if body.format == "reel":
        job = get_reel_service().run_job(db, job.id)
    elif body.format == "slideshow":
        job = get_slideshow_service().run_job(db, job.id)
    else:
        job = get_export_service().run_job(db, job.id)

    audit = get_audit_service()
    audit.log_user_action(
        db,
        user.id,
        action="export",
        resource_type="export_job",
        resource_id=str(job.id),
        details={"event_id": str(body.event_id), "format": body.format},
    )
    return _to_response(job)


@router.get("/{export_id}/download")
def download_export(
    export_id: UUID, db: DbSession, user: User = Depends(get_current_user)
) -> FileResponse:
    job = db.query(ExportJob).filter(ExportJob.id == export_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Export not ready")

    path = Path(job.output_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file missing")

    audit = get_audit_service()
    audit.log_user_action(
        db,
        user.id,
        action="export_download",
        resource_type="export_job",
        resource_id=str(job.id),
        details={"event_id": str(job.event_id)},
    )

    if job.format == "reel":
        media_type, filename = "audio/mpeg", f"booth-reel-{job.event_id}.mp3"
    elif job.format == "slideshow":
        media_type, filename = "application/zip", f"booth-slideshow-{job.event_id}.zip"
    else:
        media_type, filename = "application/zip", f"booth-export-{job.event_id}.zip"
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/{export_id}", response_model=ExportResponse)
def get_export(export_id: UUID, db: DbSession, _: OperatorAuth) -> ExportResponse:
    job = db.query(ExportJob).filter(ExportJob.id == export_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    return _to_response(job)
