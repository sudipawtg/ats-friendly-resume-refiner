import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.bootstrap import ensure_default_tenant
from app.db.session import close_database, get_session_factory, init_database
from app.models.schemas import HealthResponse
from app.routers import cv_templates, cvs, internal, job_search, jobs_inbox, settings as settings_router, tailoring

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.database_enabled:
        await init_database()
        session_factory = get_session_factory()
        async with session_factory() as session:
            bootstrap_key = await ensure_default_tenant(
                session,
                settings.default_tenant_id,
                settings.default_tenant_name,
            )
            await session.commit()
            if bootstrap_key and not settings.bootstrap_api_key:
                logger.warning(
                    "Bootstrap tenant API key generated. Set BOOTSTRAP_API_KEY in env to persist: %s",
                    bootstrap_key,
                )
    yield
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Overleaf CV Tailoring Platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(cvs.router, prefix="/api")
    app.include_router(cv_templates.router, prefix="/api")
    app.include_router(tailoring.router, prefix="/api")
    app.include_router(job_search.router, prefix="/api")
    app.include_router(jobs_inbox.router, prefix="/api")
    app.include_router(settings_router.router, prefix="/api")
    app.include_router(internal.router, prefix="/api")

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
