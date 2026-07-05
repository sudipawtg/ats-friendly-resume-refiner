import logging

from app.config import Settings
from app.models.schemas import SectionContentUpdateRequest, SectionVersionSummary
from app.services.cv_storage import CVStorageService
from app.services.section_history_service import SectionHistoryService

logger = logging.getLogger(__name__)


class CVSectionService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._storage = CVStorageService(settings, tenant_id=tenant_id)
        self._history = SectionHistoryService(settings, tenant_id=tenant_id)

    def save_section_content(
        self,
        project_id: str,
        section_path: str,
        request: SectionContentUpdateRequest,
    ) -> dict[str, str]:
        project = self._storage.get_project(project_id)
        if not project:
            raise ValueError("CV project not found")
        if section_path not in project.get("sections", []):
            raise ValueError(f"Section not found: {section_path}")

        self._history.write_section_with_history(
            project_id,
            section_path,
            request.content,
            "manual_edit",
        )
        logger.info("Saved manual section edit for %s in project %s", section_path, project_id)
        return {"section_path": section_path, "content": request.content}

    def list_section_history(self, project_id: str, section_path: str) -> list[SectionVersionSummary]:
        project = self._storage.get_project(project_id)
        if not project:
            raise ValueError("CV project not found")
        if section_path not in project.get("sections", []):
            raise ValueError(f"Section not found: {section_path}")

        versions = self._history.list_versions(project_id, section_path)
        return [SectionVersionSummary(**entry) for entry in versions]

    def restore_section_version(
        self,
        project_id: str,
        section_path: str,
        version_id: str,
    ) -> dict[str, str]:
        project = self._storage.get_project(project_id)
        if not project:
            raise ValueError("CV project not found")
        if section_path not in project.get("sections", []):
            raise ValueError(f"Section not found: {section_path}")

        restored_content = self._history.restore_version(project_id, section_path, version_id)
        return {"section_path": section_path, "content": restored_content}
