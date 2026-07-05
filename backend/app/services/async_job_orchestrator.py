import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.constants import JobStatus
from app.db.repositories import JobRepository
from app.models.schemas import (
    AnalyzeResponse,
    ATSAnalysis,
    FitAnalysis,
    TailorPreviewResponse,
    TailorRequest,
    TailorResponse,
)
from app.services.queue_service import QueueService
from app.services.tailoring_service import TailoringService

logger = logging.getLogger(__name__)


class AsyncJobOrchestrator:
    def __init__(self, settings: Settings, session: AsyncSession | None) -> None:
        self._settings = settings
        self._session = session
        self._repository = JobRepository(session) if session is not None else None
        self._queue = QueueService(settings)

    def _tailoring_for(self, tenant_id: str) -> TailoringService:
        return TailoringService(self._settings, tenant_id=tenant_id)

    @property
    def uses_queue(self) -> bool:
        return (
            self._settings.database_enabled
            and self._session is not None
            and self._queue.enabled
        )

    async def submit_tailor(self, tenant_id: str, request: TailorRequest) -> TailorResponse:
        if not self.uses_queue or self._repository is None:
            return await self._tailoring_for(tenant_id).tailor_single(request)

        job_id = str(uuid.uuid4())
        await self._repository.create_queued_job(
            tenant_id=tenant_id,
            cv_project_id=request.cv_project_id,
            job_type="tailor",
            request_payload=request.model_dump(),
            job_url=request.job_url,
            job_id=job_id,
        )
        queue_job_id = await self._queue.enqueue(
            queue_name="tailoring",
            job_name="tailor",
            job_id=job_id,
            tenant_id=tenant_id,
            payload=request.model_dump(),
        )
        await self._repository.update_status(job_id, JobStatus.QUEUED.value, queue_job_id=queue_job_id)
        return TailorResponse(
            job_id=job_id,
            fit_analysis=FitAnalysis(overall_fit=0),
            ats_analysis=ATSAnalysis(overall_score=0),
            changes=[],
            refined_instructions="",
            status=JobStatus.QUEUED,
        )

    async def submit_analyze(self, tenant_id: str, request: TailorRequest) -> AnalyzeResponse:
        if not self.uses_queue or self._repository is None:
            return await self._tailoring_for(tenant_id).analyze_single(request)

        job_id = str(uuid.uuid4())
        await self._repository.create_queued_job(
            tenant_id=tenant_id,
            cv_project_id=request.cv_project_id,
            job_type="analyze",
            request_payload=request.model_dump(),
            job_url=request.job_url,
            job_id=job_id,
        )
        queue_job_id = await self._queue.enqueue(
            queue_name="tailoring",
            job_name="analyze",
            job_id=job_id,
            tenant_id=tenant_id,
            payload=request.model_dump(),
        )
        await self._repository.update_status(job_id, JobStatus.QUEUED.value, queue_job_id=queue_job_id)
        return AnalyzeResponse(
            job_id=job_id,
            fit_analysis=FitAnalysis(overall_fit=0),
            ats_analysis=ATSAnalysis(overall_score=0),
            job_description=await self._empty_job_description(request),
            refined_instructions="",
            status=JobStatus.QUEUED,
        )

    async def submit_preview(self, tenant_id: str, request: TailorRequest) -> TailorPreviewResponse:
        if not self.uses_queue or self._repository is None:
            return await self._tailoring_for(tenant_id).preview_single(request)

        job_id = str(uuid.uuid4())
        await self._repository.create_queued_job(
            tenant_id=tenant_id,
            cv_project_id=request.cv_project_id,
            job_type="preview",
            request_payload=request.model_dump(),
            job_url=request.job_url,
            job_id=job_id,
        )
        queue_job_id = await self._queue.enqueue(
            queue_name="tailoring",
            job_name="preview",
            job_id=job_id,
            tenant_id=tenant_id,
            payload=request.model_dump(),
        )
        await self._repository.update_status(job_id, JobStatus.QUEUED.value, queue_job_id=queue_job_id)
        return TailorPreviewResponse(
            job_id=job_id,
            fit_analysis=FitAnalysis(overall_fit=0),
            ats_analysis=ATSAnalysis(overall_score=0),
            changes=[],
            refined_instructions="",
            status=JobStatus.QUEUED,
        )

    async def _empty_job_description(self, request: TailorRequest):
        from app.models.schemas import JobDescriptionExtract

        return JobDescriptionExtract(raw_text=request.job_description or "")
