import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.tenant import TenantContext, get_tenant_context
from app.db.session import get_db_session
from app.models.schemas import TailoringPreferencesResponse, TailoringPreferencesUpdate
from app.services.preferences_service import PreferencesService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/tailoring", response_model=TailoringPreferencesResponse)
async def get_tailoring_preferences(
    tenant: TenantContext = Depends(get_tenant_context),
) -> TailoringPreferencesResponse:
    settings = get_settings()
    return PreferencesService(settings, tenant_id=tenant.tenant_id).load_preferences()


@router.put("/tailoring", response_model=TailoringPreferencesResponse)
async def save_tailoring_preferences(
    request: TailoringPreferencesUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> TailoringPreferencesResponse:
    del session
    settings = get_settings()
    return PreferencesService(settings, tenant_id=tenant.tenant_id).save_preferences(request)
