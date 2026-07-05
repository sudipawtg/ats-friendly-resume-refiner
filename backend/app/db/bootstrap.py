import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key, hash_api_key
from app.db.models import Tenant, TenantApiKey

logger = logging.getLogger(__name__)


async def ensure_default_tenant(session: AsyncSession, tenant_id: str, tenant_name: str) -> str | None:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is not None:
        return None

    tenant = Tenant(id=tenant_id, name=tenant_name, slug="default")
    session.add(tenant)
    raw_key = generate_api_key()
    session.add(
        TenantApiKey(
            tenant_id=tenant_id,
            name="bootstrap",
            key_hash=hash_api_key(raw_key),
        )
    )
    await session.flush()
    logger.info("Created default tenant %s", tenant_id)
    return raw_key


async def get_tenant_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none()
