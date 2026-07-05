import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.repositories import JobRepository
from app.models.schemas import TailorRequest
from app.services.tailoring_service import TailoringService

logger = logging.getLogger(__name__)


class WorkerExecutorService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(
        self,
        session: AsyncSession,
        tenant_id: str,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
    ) -> None:
        repository = JobRepository(session)
        tailoring = TailoringService(self._settings, tenant_id=tenant_id)
        await repository.update_status(job_id, "processing")

        try:
            request = TailorRequest.model_validate(payload)
            if job_type == "analyze":
                result = await tailoring.analyze_single(request)
                await repository.save_tailor_result(
                    job_id=job_id,
                    status=result.status.value,
                    fit_analysis=result.fit_analysis.model_dump(),
                    ats_analysis=result.ats_analysis.model_dump(),
                    changes=[],
                    job_description=result.job_description.model_dump(),
                    refined_instructions=result.refined_instructions,
                )
                return

            if job_type == "preview":
                result = await tailoring.preview_single(request)
                await repository.save_tailor_result(
                    job_id=job_id,
                    status=result.status.value,
                    fit_analysis=result.fit_analysis.model_dump(),
                    ats_analysis=result.ats_analysis.model_dump(),
                    changes=[change.model_dump() for change in result.changes],
                    job_description=None,
                    refined_instructions=result.refined_instructions,
                )
                return

            if job_type == "tailor":
                result = await tailoring.tailor_single_for_job_id(request, job_id)
                await repository.save_tailor_result(
                    job_id=job_id,
                    status=result.status.value,
                    fit_analysis=result.fit_analysis.model_dump(),
                    ats_analysis=result.ats_analysis.model_dump(),
                    changes=[change.model_dump() for change in result.changes],
                    job_description=None,
                    refined_instructions=result.refined_instructions,
                )
                return

            raise ValueError(f"Unsupported worker job type: {job_type}")
        except Exception as error:
            logger.exception("Worker job %s failed", job_id)
            await repository.update_status(job_id, "failed", error_message=str(error))
            raise
