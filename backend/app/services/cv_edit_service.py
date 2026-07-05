import logging

from app.config import Settings
from app.models.schemas import MasterSectionRefineRequest, MasterSectionRefineResponse
from app.services.cv_storage import CVStorageService
from app.services.llm_service import LLMService
from app.services.tailoring_service import normalize_proposed_latex

logger = logging.getLogger(__name__)


class CVEditService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._storage = CVStorageService(settings, tenant_id=tenant_id)
        self._llm = LLMService(settings)

    async def refine_master_section(
        self,
        project_id: str,
        request: MasterSectionRefineRequest,
    ) -> MasterSectionRefineResponse:
        project = self._storage.get_project(project_id)
        if not project:
            raise ValueError("CV project not found")

        if request.section_path not in project.get("sections", []):
            raise ValueError(f"Section not found: {request.section_path}")

        original_text = self._storage.read_section(project_id, request.section_path)
        refined = await self._llm.refine_master_section(
            section_path=request.section_path,
            original=original_text,
            instruction=request.instruction,
            global_instruction=request.global_instruction,
        )
        if refined is None:
            raise ValueError(
                "Could not refine section. Check your OpenAI API key or try a different instruction."
            )

        updated_content = normalize_proposed_latex(refined["content"])
        from app.services.section_history_service import SectionHistoryService

        SectionHistoryService(self._settings, tenant_id=self._storage.tenant_id).write_section_with_history(
            project_id,
            request.section_path,
            updated_content,
            "ai_refine",
        )
        logger.info("Refined master section %s for project %s", request.section_path, project_id)

        return MasterSectionRefineResponse(
            section_path=request.section_path,
            content=updated_content,
            reason=refined.get("reason", ""),
        )
