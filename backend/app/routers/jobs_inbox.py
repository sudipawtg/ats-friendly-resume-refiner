import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import TenantContext, get_tenant_context
from app.db.repositories import JobRepository, SavedJobRepository
from app.db.session import get_db_session
from app.models.schemas import JobDescriptionExtract
from app.services.job_mapper import job_record_to_dict, job_record_to_result
from app.services.tailoring_service import TailoringService
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Jobs Inbox & Outputs"])


class SavedJobCreateRequest(BaseModel):
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    job_description: JobDescriptionExtract | None = None
    fit_score: int | None = None
    notes: str = ""


class SavedJobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    url: str
    fit_score: int | None
    notes: str
    job_description: JobDescriptionExtract | None = None


class OutputSummaryResponse(BaseModel):
    job_id: str
    cv_project_id: str
    status: str
    job_type: str
    fit_score: int | None = None
    ats_score: int | None = None
    url: str | None = None
    updated_at: str | None = None


@router.get("/saved-jobs", response_model=list[SavedJobResponse])
async def list_saved_jobs(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> list[SavedJobResponse]:
    settings = get_settings()
    if not settings.database_enabled or session is None:
        return []
    repository = SavedJobRepository(session)
    saved_jobs = await repository.list_saved_jobs(tenant.tenant_id)
    return [
        SavedJobResponse(
            id=saved.id,
            title=saved.title,
            company=saved.company,
            location=saved.location,
            url=saved.url,
            fit_score=saved.fit_score,
            notes=saved.notes,
            job_description=JobDescriptionExtract(**saved.job_description)
            if saved.job_description
            else None,
        )
        for saved in saved_jobs
    ]


@router.post("/saved-jobs", response_model=SavedJobResponse)
async def create_saved_job(
    request: SavedJobCreateRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> SavedJobResponse:
    settings = get_settings()
    if not settings.database_enabled or session is None:
        raise HTTPException(status_code=503, detail="Saved jobs require database configuration")
    repository = SavedJobRepository(session)
    saved = await repository.upsert_saved_job(
        tenant_id=tenant.tenant_id,
        url=request.url,
        title=request.title,
        company=request.company,
        location=request.location,
        job_description=request.job_description.model_dump() if request.job_description else None,
        fit_score=request.fit_score,
        notes=request.notes,
    )
    return SavedJobResponse(
        id=saved.id,
        title=saved.title,
        company=saved.company,
        location=saved.location,
        url=saved.url,
        fit_score=saved.fit_score,
        notes=saved.notes,
        job_description=request.job_description,
    )


@router.delete("/saved-jobs/{saved_job_id}")
async def delete_saved_job(
    saved_job_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict[str, bool]:
    settings = get_settings()
    if not settings.database_enabled or session is None:
        raise HTTPException(status_code=503, detail="Saved jobs require database configuration")
    repository = SavedJobRepository(session)
    deleted = await repository.delete_saved_job(tenant.tenant_id, saved_job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved job not found")
    return {"deleted": True}


@router.get("/outputs", response_model=list[OutputSummaryResponse])
async def list_outputs(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> list[OutputSummaryResponse]:
    settings = get_settings()
    if not settings.database_enabled or session is None:
        return []
    repository = JobRepository(session)
    jobs = await repository.list_outputs_for_tenant(tenant.tenant_id)
    outputs: list[OutputSummaryResponse] = []
    for job in jobs:
        fit_score = job.fit_analysis.get("overall_fit") if job.fit_analysis else None
        ats_score = job.ats_analysis.get("overall_score") if job.ats_analysis else None
        outputs.append(
            OutputSummaryResponse(
                job_id=job.id,
                cv_project_id=job.cv_project_id,
                status=job.status,
                job_type=job.job_type,
                fit_score=fit_score,
                ats_score=ats_score,
                url=job.url,
                updated_at=job.updated_at.isoformat() if job.updated_at else None,
            )
        )
    return outputs


@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict:
    settings = get_settings()
    if settings.database_enabled and session is not None:
        repository = JobRepository(session)
        record = await repository.get_job_for_tenant(tenant.tenant_id, job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Job not found")
        payload = job_record_to_dict(record)
        if record.status in {"completed", "needs_manual", "failed"}:
            payload["result"] = job_record_to_result(record)
        return payload

    service = TailoringService(settings, tenant_id=tenant.tenant_id)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
