import json
import logging
from pathlib import Path

from app.config import Settings
from app.models.schemas import TailoringPreferencesResponse, TailoringPreferencesUpdate
from app.services.tenant_storage_paths import ensure_tenant_storage_layout, resolve_tenant_storage_root

logger = logging.getLogger(__name__)


class PreferencesService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._tenant_id = tenant_id
        self._tenant_root = resolve_tenant_storage_root(settings, tenant_id)
        ensure_tenant_storage_layout(self._tenant_root)
        self._preferences_path = self._tenant_root / "tailoring_preferences.json"

    def load_preferences(self) -> TailoringPreferencesResponse:
        if not self._preferences_path.exists():
            return TailoringPreferencesResponse()
        try:
            payload = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read tailoring preferences for tenant %s", self._tenant_id)
            return TailoringPreferencesResponse()
        section_instructions = payload.get("section_instructions") or {}
        if not isinstance(section_instructions, dict):
            section_instructions = {}
        return TailoringPreferencesResponse(
            global_instruction=str(payload.get("global_instruction") or ""),
            section_instructions={
                str(key): str(value) for key, value in section_instructions.items()
            },
            active_profile_id=payload.get("active_profile_id"),
        )

    def save_preferences(self, update: TailoringPreferencesUpdate) -> TailoringPreferencesResponse:
        current = self.load_preferences()
        merged = TailoringPreferencesResponse(
            global_instruction=update.global_instruction
            if update.global_instruction is not None
            else current.global_instruction,
            section_instructions=update.section_instructions
            if update.section_instructions is not None
            else current.section_instructions,
            active_profile_id=update.active_profile_id
            if update.active_profile_id is not None
            else current.active_profile_id,
        )
        self._preferences_path.write_text(
            json.dumps(merged.model_dump(), indent=2),
            encoding="utf-8",
        )
        logger.info("Saved tailoring preferences for tenant %s", self._tenant_id or "legacy")
        return merged
