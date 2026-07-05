from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.security import hash_api_key
from app.db.models import Tenant, TenantApiKey
from app.db.session import get_db_session


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant_name: str
    tenant_slug: str


async def get_tenant_context(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
    session: AsyncSession | None = Depends(get_db_session),
) -> TenantContext:
    if not settings.database_enabled or session is None:
        return TenantContext(
            tenant_id=settings.default_tenant_id,
            tenant_name=settings.default_tenant_name,
            tenant_slug="default",
        )

    tenant_id = x_tenant_id or settings.default_tenant_id
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if settings.require_api_key:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="Missing API key")
        key_hash = hash_api_key(x_api_key)
        result = await session.execute(
            select(TenantApiKey).where(
                TenantApiKey.tenant_id == tenant_id,
                TenantApiKey.key_hash == key_hash,
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key is None:
            raise HTTPException(status_code=401, detail="Invalid API key")

    return TenantContext(tenant_id=tenant.id, tenant_name=tenant.name, tenant_slug=tenant.slug)


async def verify_internal_api_key(
    x_internal_api_key: str | None = Header(default=None, alias="X-Internal-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.internal_api_key:
        raise HTTPException(status_code=503, detail="Internal worker API is not configured")
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal API key")
