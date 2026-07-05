import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def sqlite_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("DATABASE_USE_ALEMBIC", "false")
    monkeypatch.setenv("ASYNC_JOBS_ENABLED", "false")
    get_settings.cache_clear()
    settings = get_settings()
    yield settings
    get_settings.cache_clear()


@pytest.fixture
async def sqlite_client(sqlite_settings):
    from app.db.bootstrap import ensure_default_tenant
    from app.db.session import get_session_factory, init_database

    await init_database()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await ensure_default_tenant(
            session,
            sqlite_settings.default_tenant_id,
            sqlite_settings.default_tenant_name,
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_saved_jobs_empty_without_database(api_client):
    response = await api_client.get("/api/saved-jobs")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_outputs_empty_without_database(api_client):
    response = await api_client.get("/api/outputs")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_saved_jobs_create_with_sqlite(sqlite_client):
    response = await sqlite_client.post(
        "/api/saved-jobs",
        json={"url": "https://example.com/jobs/123", "title": "AI Engineer"},
        headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["url"] == "https://example.com/jobs/123"
    assert payload["title"] == "AI Engineer"


@pytest.mark.asyncio
async def test_cv_upload_syncs_to_database(sqlite_client, sample_cv_zip):
    response = await sqlite_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", sample_cv_zip, "application/zip")},
        data={"name": "Synced CV"},
        headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 200
    project = response.json()
    assert project["name"] == "Synced CV"

    list_response = await sqlite_client.get(
        "/api/cvs",
        headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"},
    )
    assert list_response.status_code == 200
    projects = list_response.json()
    assert any(entry["id"] == project["id"] for entry in projects)


@pytest.mark.asyncio
async def test_health_endpoint(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
