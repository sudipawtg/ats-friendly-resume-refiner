import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.services.cv_storage import CVStorageService

logger = logging.getLogger(__name__)

MAX_SECTION_VERSIONS = 20


class SectionHistoryService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._storage = CVStorageService(settings, tenant_id=tenant_id)

    def _history_dir(self, project_id: str, section_path: str) -> Path:
        safe_name = section_path.replace("/", "__")
        path = self._storage._project_dir(project_id) / ".section_history" / safe_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_versions(self, project_id: str, section_path: str) -> list[dict[str, str]]:
        history_dir = self._history_dir(project_id, section_path)
        versions: list[dict[str, str]] = []
        for file_path in sorted(history_dir.glob("*.json"), reverse=True):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            versions.append(
                {
                    "version_id": payload.get("version_id", file_path.stem),
                    "section_path": section_path,
                    "source": payload.get("source", "unknown"),
                    "created_at": payload.get("created_at", ""),
                    "preview": (payload.get("content") or "")[:160],
                }
            )
        return versions

    def save_version(
        self,
        project_id: str,
        section_path: str,
        content: str,
        source: str,
    ) -> dict[str, str]:
        version_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "version_id": version_id,
            "section_path": section_path,
            "content": content,
            "source": source,
            "created_at": created_at,
        }
        history_dir = self._history_dir(project_id, section_path)
        target = history_dir / f"{created_at.replace(':', '-')}_{version_id[:8]}.json"
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._trim_history(history_dir)
        return {
            "version_id": version_id,
            "section_path": section_path,
            "source": source,
            "created_at": created_at,
        }

    def restore_version(self, project_id: str, section_path: str, version_id: str) -> str:
        history_dir = self._history_dir(project_id, section_path)
        for file_path in history_dir.glob("*.json"):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if payload.get("version_id") != version_id:
                continue
            restored_content = payload.get("content", "")
            if not isinstance(restored_content, str):
                raise ValueError("Invalid version content")
            try:
                current_content = self._storage.read_section(project_id, section_path)
            except FileNotFoundError:
                current_content = ""
            if current_content.strip():
                self.save_version(project_id, section_path, current_content, "pre_restore")
            self._storage.write_section(project_id, section_path, restored_content)
            logger.info("Restored section %s to version %s", section_path, version_id)
            return restored_content
        raise ValueError(f"Version not found: {version_id}")

    def write_section_with_history(
        self,
        project_id: str,
        section_path: str,
        content: str,
        source: str,
    ) -> Path:
        try:
            previous_content = self._storage.read_section(project_id, section_path)
        except FileNotFoundError:
            previous_content = ""
        if previous_content.strip() and previous_content != content:
            self.save_version(project_id, section_path, previous_content, source)
        return self._storage.write_section(project_id, section_path, content)

    def _trim_history(self, history_dir: Path) -> None:
        files = sorted(history_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for stale_file in files[MAX_SECTION_VERSIONS:]:
            try:
                stale_file.unlink()
            except OSError:
                logger.warning("Could not remove old section history file %s", stale_file)
