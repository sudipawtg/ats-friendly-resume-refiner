from pathlib import Path

from app.config import Settings


def resolve_tenant_storage_root(settings: Settings, tenant_id: str | None) -> Path:
    if tenant_id:
        tenant_root = settings.storage_dir / tenant_id
        tenant_root.mkdir(parents=True, exist_ok=True)
        return tenant_root
    return settings.storage_dir


def ensure_tenant_storage_layout(tenant_root: Path) -> None:
    (tenant_root / "cvs").mkdir(parents=True, exist_ok=True)
    (tenant_root / "outputs").mkdir(parents=True, exist_ok=True)
    (tenant_root / "reports").mkdir(parents=True, exist_ok=True)
