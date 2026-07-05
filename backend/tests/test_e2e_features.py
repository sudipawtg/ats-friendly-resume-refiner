import asyncio
import io

import pytest
from httpx import AsyncClient

from tests.conftest import SAMPLE_JOB_DESCRIPTION, make_sample_cv_zip


@pytest.mark.asyncio
async def test_health_endpoint(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_cv_upload_list_and_section_flow(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload_response = await api_client.post(
        "/api/cvs/upload",
        data={"name": "E2E Master CV"},
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
    )
    assert upload_response.status_code == 200
    project = upload_response.json()
    project_id = project["id"]
    assert project["name"] == "E2E Master CV"
    assert len(project["sections"]) >= 2

    list_response = await api_client.get("/api/cvs")
    assert list_response.status_code == 200
    projects = list_response.json()
    assert any(entry["id"] == project_id for entry in projects)

    get_response = await api_client.get(f"/api/cvs/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["master_file"]

    section_path = project["sections"][0]
    section_response = await api_client.get(f"/api/cvs/{project_id}/sections/{section_path}")
    assert section_response.status_code == 200
    assert len(section_response.json()["content"]) > 0


@pytest.mark.asyncio
async def test_crawl_job_with_manual_description(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/crawl",
        json={"url": "", "manual_description": SAMPLE_JOB_DESCRIPTION},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["extraction_confidence"] >= 0.2
    assert len(data["raw_text"]) > 0


@pytest.mark.asyncio
async def test_tailor_cv_end_to_end_with_manual_job_description(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
        data={"name": "Tailor E2E CV"},
    )
    assert upload_response.status_code == 200
    project = upload_response.json()

    tailor_response = await api_client.post(
        "/api/tailor",
        json={
            "cv_project_id": project["id"],
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "editable_sections": ["sections/skills.tex", "sections/experience.tex"],
            "global_instruction": "Emphasize Python and LLM experience",
            "refine_prompt": True,
        },
    )
    assert tailor_response.status_code == 200
    result = tailor_response.json()
    assert result["job_id"]
    assert result["status"] in ("completed", "needs_manual")
    assert result["fit_analysis"]["overall_fit"] >= 0
    assert result["ats_analysis"]["overall_score"] >= 0

    job_response = await api_client.get(f"/api/jobs/{result['job_id']}")
    assert job_response.status_code == 200
    assert job_response.json()["id"] == result["job_id"]

    if result["status"] == "completed":
        download_response = await api_client.get(
            f"/api/cvs/{project['id']}/download/{result['job_id']}"
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/zip"

        report_response = await api_client.post(
            "/api/reports/html",
            json={"job_id": result["job_id"]},
        )
        assert report_response.status_code == 200
        assert "text/html" in report_response.headers["content-type"]
        assert "ResumeForge" in report_response.text


@pytest.mark.asyncio
async def test_prompt_refine_and_instruction_profiles(api_client: AsyncClient) -> None:
    profiles_response = await api_client.get("/api/instruction-profiles")
    assert profiles_response.status_code == 200
    profiles = profiles_response.json()
    assert "ai_engineer" in profiles

    refine_response = await api_client.post(
        "/api/prompt/refine",
        json={
            "raw_instruction": "Position me as an AI consultant with business impact",
            "context": "Tailoring for fintech role",
            "target_section": "sections/experience.tex",
        },
    )
    assert refine_response.status_code == 200
    refined = refine_response.json()
    assert refined["methodology_applied"] == "STAR"
    assert "AI consultant" in refined["refined_instruction"]


@pytest.mark.asyncio
async def test_batch_campaign_end_to_end(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
        data={"name": "Batch E2E CV"},
    )
    assert upload_response.status_code == 200
    project_id = upload_response.json()["id"]

    batch_response = await api_client.post(
        "/api/batches",
        json={
            "cv_project_id": project_id,
            "name": "E2E Campaign",
            "jobs": [
                {
                    "manual_description": SAMPLE_JOB_DESCRIPTION,
                    "company": "Acme Corp",
                    "title": "Senior AI Engineer",
                    "location": "London, UK",
                },
                {
                    "manual_description": SAMPLE_JOB_DESCRIPTION,
                    "company": "Beta Ltd",
                    "title": "ML Engineer",
                    "location": "Remote",
                },
            ],
            "editable_sections": ["sections/skills.tex"],
            "global_instruction": "Highlight Python expertise",
        },
    )
    assert batch_response.status_code == 200
    batch = batch_response.json()
    batch_id = batch["id"]
    assert batch["total_jobs"] == 2
    assert batch["name"] == "E2E Campaign"

    final_batch = batch
    for _ in range(30):
        await asyncio.sleep(0.2)
        poll_response = await api_client.get(f"/api/batches/{batch_id}")
        assert poll_response.status_code == 200
        final_batch = poll_response.json()
        if final_batch["completed"] + final_batch["needs_manual"] + final_batch["failed"] == final_batch["total_jobs"]:
            break

    assert final_batch["completed"] + final_batch["needs_manual"] + final_batch["failed"] == 2

    list_response = await api_client.get("/api/batches")
    assert list_response.status_code == 200
    assert any(entry["id"] == batch_id for entry in list_response.json())


@pytest.mark.asyncio
async def test_job_discovery_metadata_endpoints(api_client: AsyncClient) -> None:
    sources_response = await api_client.get("/api/jobs/search/sources")
    assert sources_response.status_code == 200
    assert "indeed_uk" in sources_response.json()

    filters_response = await api_client.get("/api/jobs/search/date-filters")
    assert filters_response.status_code == 200
    assert filters_response.json()["7"] == 7


@pytest.mark.asyncio
async def test_upload_rejects_non_zip(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("resume.txt", io.BytesIO(b"not a zip"), "text/plain")},
        data={"name": "Invalid"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_tailor_requires_job_input(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
        data={"name": "Validation CV"},
    )
    project_id = upload_response.json()["id"]

    response = await api_client.post(
        "/api/tailor",
        json={
            "cv_project_id": project_id,
            "editable_sections": ["sections/skills.tex"],
        },
    )
    assert response.status_code == 400
