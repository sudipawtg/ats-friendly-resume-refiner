import logging

from app.config import Settings
from app.models.schemas import CVCoachReviewRequest, CVCoachReviewResponse, CoachChatRequest, CoachChatResponse
from app.services.cv_storage import CVStorageService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class CVCoachService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._storage = CVStorageService(settings, tenant_id=tenant_id)
        self._llm = LLMService(settings)

    async def review_cv(
        self,
        project_id: str,
        request: CVCoachReviewRequest,
    ) -> CVCoachReviewResponse:
        project = self._storage.get_project(project_id)
        if not project:
            raise ValueError("CV project not found")

        sections = self._storage.read_all_sections(project_id)
        if not sections:
            raise ValueError("CV project has no sections to review")

        review = await self._llm.review_master_cv(
            sections=sections,
            target_role=request.target_role,
            focus=request.focus,
        )
        logger.info("CV coach review completed for project %s", project_id)
        return review

    async def chat(
        self,
        project_id: str,
        request: CoachChatRequest,
    ) -> CoachChatResponse:
        project = self._storage.get_project(project_id)
        if not project:
            raise ValueError("CV project not found")

        sections = self._storage.read_all_sections(project_id)
        if not sections:
            raise ValueError("CV project has no sections to discuss")

        return await self._llm.coach_chat(
            sections=sections,
            message=request.message,
            history=[entry.model_dump() for entry in request.history],
            target_role=request.target_role,
            focus=request.focus,
        )
