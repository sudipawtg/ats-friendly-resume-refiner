import io
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.constants import INSTRUCTION_PROFILES, JOB_SEARCH_SOURCES
from app.main import app
from app.models.schemas import ATSAnalysis, FitAnalysis, JobDescriptionExtract, SectionChange
from app.services.cv_storage import CVStorageService
from tests.conftest import SAMPLE_JOB_DESCRIPTION, make_sample_cv_zip


@pytest.fixture
async def client(test_settings):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api") as ac:
        yield ac


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_ok(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


class TestCVEndpoints:
    @pytest.mark.asyncio
    async def test_list_cvs_empty(self, client):
        response = await client.get("/cvs")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_upload_cv_success(self, client, sample_cv_zip):
        files = {"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")}
        response = await client.post("/cvs/upload", files=files, data={"name": "My CV"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My CV"
        assert data["id"]
        assert len(data["sections"]) >= 1

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_format(self, client):
        files = {"file": ("cv.txt", io.BytesIO(b"hello"), "text/plain")}
        response = await client.post("/cvs/upload", files=files)
        assert response.status_code == 400
        assert "zip" in response.json()["detail"].lower() or "pdf" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized_file(self, client, test_settings, monkeypatch):
        monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")
        get_settings.cache_clear()
        large_zip = b"x" * (2 * 1024 * 1024)
        files = {"file": ("big.zip", io.BytesIO(large_zip), "application/zip")}
        response = await client.post("/cvs/upload", files=files)
        get_settings.cache_clear()
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_get_cv_project(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project_id = upload.json()["id"]
        response = await client.get(f"/cvs/{project_id}")
        assert response.status_code == 200
        assert response.json()["id"] == project_id

    @pytest.mark.asyncio
    async def test_get_cv_project_not_found(self, client):
        response = await client.get("/cvs/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_section(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project = upload.json()
        section_path = project["sections"][0]
        response = await client.get(f"/cvs/{project['id']}/sections/{section_path}")
        assert response.status_code == 200
        data = response.json()
        assert data["section_path"] == section_path
        assert len(data["content"]) > 0

    @pytest.mark.asyncio
    async def test_get_master_sections(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project = upload.json()
        response = await client.get(f"/cvs/{project['id']}/master-sections")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sections"]) == len(project["sections"])
        assert all(section["content"] for section in data["sections"])

    @pytest.mark.asyncio
    async def test_download_output_zip_not_found(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project_id = upload.json()["id"]
        response = await client.get(f"/cvs/{project_id}/download/missing-job")
        assert response.status_code == 404


class TestTailoringEndpoints:
    @pytest.mark.asyncio
    async def test_crawl_manual_description(self, client):
        response = await client.post(
            "/crawl",
            json={"url": "", "manual_description": SAMPLE_JOB_DESCRIPTION},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["extraction_confidence"] >= 0.2

    @pytest.mark.asyncio
    async def test_list_instruction_profiles(self, client):
        response = await client.get("/instruction-profiles")
        assert response.status_code == 200
        assert response.json() == INSTRUCTION_PROFILES

    @pytest.mark.asyncio
    async def test_refine_prompt_empty(self, client):
        response = await client.post("/prompt/refine", json={"raw_instruction": ""})
        assert response.status_code == 200
        assert "STAR" in response.json()["methodology_applied"]

    @pytest.mark.asyncio
    async def test_tailor_missing_project(self, client):
        response = await client.post(
            "/tailor",
            json={
                "cv_project_id": "missing",
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_tailor_needs_manual_without_job_input(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project_id = upload.json()["id"]
        response = await client.post(
            "/tailor",
            json={"cv_project_id": project_id},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_tailor_with_manual_description(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project_id = upload.json()["id"]
        response = await client.post(
            "/tailor",
            json={
                "cv_project_id": project_id,
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "refine_prompt": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"]
        assert data["status"] in ("completed", "needs_manual")

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client):
        response = await client.get("/jobs/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_batches_empty(self, client):
        response = await client.get("/batches")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_batch(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project_id = upload.json()["id"]
        response = await client.post(
            "/batches",
            json={
                "cv_project_id": project_id,
                "name": "Test Batch",
                "jobs": [{"manual_description": SAMPLE_JOB_DESCRIPTION}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Batch"
        assert data["total_jobs"] == 1

    @pytest.mark.asyncio
    async def test_get_batch_not_found(self, client):
        response = await client.get("/batches/missing")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_report_requires_job_or_batch_id(self, client):
        response = await client.post("/reports/html", json={})
        assert response.status_code == 400


class TestJobSearchEndpoints:
    @pytest.mark.asyncio
    async def test_list_sources(self, client):
        response = await client.get("/jobs/search/sources")
        assert response.status_code == 200
        assert response.json() == JOB_SEARCH_SOURCES

    @pytest.mark.asyncio
    async def test_list_date_filters(self, client):
        response = await client.get("/jobs/search/date-filters")
        assert response.status_code == 200
        assert "7" in response.json()

    @pytest.mark.asyncio
    async def test_search_jobs_validation_error(self, client):
        response = await client.post("/jobs/search", json={"job_title": "A"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_jobs_with_mocked_service(self, client):
        from app.models.schemas import JobSearchResponse

        mock_response = JobSearchResponse(
            query="AI Engineer",
            location="London",
            max_days_old=7,
            total_results=0,
            results=[],
            sources_searched=["remotive"],
            warnings=["No jobs found"],
        )
        with patch(
            "app.routers.job_search.JobSearchService.search_jobs",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await client.post(
                "/jobs/search",
                json={"job_title": "AI Engineer", "sources": ["remotive"]},
            )
        assert response.status_code == 200
        assert response.json()["query"] == "AI Engineer"
