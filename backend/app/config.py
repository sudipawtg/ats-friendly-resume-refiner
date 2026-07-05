from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ResumeForge"
    debug: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: int = 120
    storage_dir: Path = Path("storage")
    max_upload_size_mb: int = 50
    crawl_timeout_seconds: int = 90
    crawl_user_agent: str = (
        "Mozilla/5.0 (compatible; ResumeForge/1.0; +https://resumeforge.app/bot)"
    )
    min_job_content_chars: int = 200
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    database_url: str = ""
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"
    default_tenant_name: str = "Default Workspace"
    require_api_key: bool = False
    bootstrap_api_key: str = ""
    database_use_alembic: bool = True

    redis_url: str = ""
    queue_service_url: str = "http://127.0.0.1:8787"
    internal_api_key: str = ""
    async_jobs_enabled: bool = False

    @property
    def database_enabled(self) -> bool:
        return bool(self.database_url)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "cvs").mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "outputs").mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "reports").mkdir(parents=True, exist_ok=True)
    return settings
