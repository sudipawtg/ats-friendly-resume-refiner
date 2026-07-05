import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import TenantContext, verify_internal_api_key
from app.db.session import get_db_session
from app.services.worker_executor import WorkerExecutorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/worker", tags=["Internal Worker"])


class WorkerExecuteRequest(BaseModel):
    job_id: str
    tenant_id: str
    job_type: str
    payload: dict = Field(default_factory=dict)


@router.post("/execute")
async def execute_worker_job(
    request: WorkerExecuteRequest,
    _: None = Depends(verify_internal_api_key),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict[str, str]:
    if session is None:
        raise HTTPException(status_code=503, detail="Database is required for worker execution")
    executor = WorkerExecutorService()
    try:
        await executor.execute(
            session=session,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            job_type=request.job_type,
            payload=request.payload,
        )
    except Exception as error:
        logger.exception("Internal worker execution failed for job %s", request.job_id)
        raise HTTPException(status_code=500, detail="Worker execution failed") from error
    return {"status": "ok", "job_id": request.job_id}
