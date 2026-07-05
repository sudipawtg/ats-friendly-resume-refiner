import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import INSTRUCTION_PROFILES
from app.core.tenant import TenantContext, get_tenant_context
from app.db.repositories import JobRepository
from app.db.session import get_db_session
from app.models.schemas import (
    AnalyzeResponse,
    BatchCreateRequest,
    BatchResponse,
    CrawlJobRequest,
    JobDescriptionExtract,
    PromptRefineRequest,
    PromptRefineResponse,
    ReportRequest,
    SectionRefineRequest,
    SectionRefineResponse,
    TailorPreviewResponse,
    TailorRequest,
    TailorResponse,
)
from app.services.async_job_orchestrator import AsyncJobOrchestrator
from app.services.crawler import JobCrawlerService
from app.services.job_mapper import job_record_to_dict, job_record_to_result
from app.services.llm_service import LLMService
from app.services.report_service import ReportService
from app.services.tailoring_service import TailoringService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tailoring"])


@router.post("/tailor", response_model=TailorResponse)
async def tailor_cv(
    request: TailorRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> TailorResponse:
    orchestrator = AsyncJobOrchestrator(get_settings(), session)
    try:
        return await orchestrator.submit_tailor(tenant.tenant_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Tailoring failed")
        raise HTTPException(status_code=500, detail="Tailoring failed. Please try again.") from error


@router.post("/tailor/analyze", response_model=AnalyzeResponse)
async def analyze_cv_for_job(
    request: TailorRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> AnalyzeResponse:
    orchestrator = AsyncJobOrchestrator(get_settings(), session)
    try:
        return await orchestrator.submit_analyze(tenant.tenant_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Analyze failed")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.") from error


@router.post("/tailor/preview", response_model=TailorPreviewResponse)
async def preview_tailor_cv(
    request: TailorRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> TailorPreviewResponse:
    orchestrator = AsyncJobOrchestrator(get_settings(), session)
    try:
        return await orchestrator.submit_preview(tenant.tenant_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Preview tailoring failed")
        raise HTTPException(status_code=500, detail="Preview failed. Please try again.") from error


@router.post("/tailor/preview/{preview_job_id}/refine-section", response_model=SectionRefineResponse)
async def refine_preview_section(
    preview_job_id: str,
    request: SectionRefineRequest,
    tenant: TenantContext = Depends(get_tenant_context),
) -> SectionRefineResponse:
    service = TailoringService(get_settings(), tenant_id=tenant.tenant_id)
    try:
        return await service.refine_preview_section(preview_job_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Section refine failed")
        raise HTTPException(status_code=500, detail="Section refine failed. Please try again.") from error


@router.get("/jobs/{job_id}")
async def get_job(
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


@router.post("/crawl", response_model=JobDescriptionExtract)
async def crawl_job(request: CrawlJobRequest) -> JobDescriptionExtract:
    crawler = JobCrawlerService(get_settings())
    result = await crawler.extract_job(request.url, request.manual_description)
    if result.extraction_confidence < 0.2:
        return result
    return result


@router.post("/batches", response_model=BatchResponse)
async def create_batch(
    request: BatchCreateRequest,
    tenant: TenantContext = Depends(get_tenant_context),
) -> BatchResponse:
    service = TailoringService(get_settings(), tenant_id=tenant.tenant_id)
    return await service.create_batch(request)


@router.get("/batches", response_model=list[BatchResponse])
async def list_batches(tenant: TenantContext = Depends(get_tenant_context)) -> list[BatchResponse]:
    service = TailoringService(get_settings(), tenant_id=tenant.tenant_id)
    batches = service.list_batches()
    return [service._to_batch_response(batch) for batch in batches]


@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: str, tenant: TenantContext = Depends(get_tenant_context)) -> BatchResponse:
    service = TailoringService(get_settings(), tenant_id=tenant.tenant_id)
    batch = service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return service._to_batch_response(batch)


@router.post("/prompt/refine", response_model=PromptRefineResponse)
async def refine_prompt(request: PromptRefineRequest) -> PromptRefineResponse:
    llm = LLMService(get_settings())
    return await llm.refine_prompt(
        raw_instruction=request.raw_instruction,
        context=request.context,
        target_section=request.target_section,
    )


@router.get("/instruction-profiles")
async def list_instruction_profiles() -> dict[str, str]:
    return INSTRUCTION_PROFILES


@router.post("/reports/html")
async def generate_html_report(
    request: ReportRequest,
    tenant: TenantContext = Depends(get_tenant_context),
):
    from fastapi.responses import FileResponse

    if not request.job_id and not request.batch_id:
        raise HTTPException(status_code=400, detail="job_id or batch_id required")

    service = ReportService(get_settings(), tenant_id=tenant.tenant_id)
    report_path = service.generate_html_report(
        job_id=request.job_id,
        batch_id=request.batch_id,
        include_ats=request.include_ats,
        include_fit=request.include_fit,
        include_changes=request.include_changes,
        include_gaps=request.include_gaps,
    )
    return FileResponse(
        path=str(report_path),
        media_type="text/html",
        filename=report_path.name,
    )
