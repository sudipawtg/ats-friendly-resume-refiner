import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def get_sync_database_url(async_database_url: str) -> str:
    if async_database_url.startswith("sqlite+aiosqlite"):
        return async_database_url.replace("sqlite+aiosqlite", "sqlite", 1)
    return async_database_url.replace("+asyncpg", "+psycopg2", 1)


def run_migrations() -> None:
    settings = get_settings()
    if not settings.database_url:
        return

    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", get_sync_database_url(settings.database_url))
    command.upgrade(alembic_config, "head")
    logger.info("Database migrations applied")
