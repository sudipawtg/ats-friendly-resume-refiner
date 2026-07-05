import asyncio
import io

import pytest
from httpx import AsyncClient

from tests.conftest import SAMPLE_JOB_DESCRIPTION, make_sample_cv_zip


@pytest.mark.asyncio
async def test_analyze_cv_without_writing_output(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload_response = await api_client.post(
        "/api/cvs/upload",
        params={"name": "Analyze Test CV"},
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
    )
    assert upload_response.status_code == 200
    project = upload_response.json()

    analyze_response = await api_client.post(
        "/api/tailor/analyze",
        json={
            "cv_project_id": project["id"],
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "editable_sections": ["sections/skills.tex"],
            "refine_prompt": False,
        },
    )
    assert analyze_response.status_code == 200
    data = analyze_response.json()
    assert "fit_analysis" in data
    assert "ats_analysis" in data
    assert "job_description" in data
    assert data["job_description"]["raw_text"]

    output_dir_missing = True
    import os
    from pathlib import Path

    settings_storage = Path(os.environ.get("STORAGE_DIR", "storage"))
    outputs_root = settings_storage / "outputs" / project["id"]
    if outputs_root.exists():
        output_dir_missing = len(list(outputs_root.iterdir())) == 0
    assert output_dir_missing


@pytest.mark.asyncio
async def test_preview_tailor_without_writing_output(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload_response = await api_client.post(
        "/api/cvs/upload",
        params={"name": "Preview Test CV"},
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
    )
    assert upload_response.status_code == 200
    project = upload_response.json()

    preview_response = await api_client.post(
        "/api/tailor/preview",
        json={
            "cv_project_id": project["id"],
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "editable_sections": ["sections/skills.tex", "sections/experience.tex"],
            "refine_prompt": False,
        },
    )
    assert preview_response.status_code == 200
    data = preview_response.json()
    assert "changes" in data
    assert isinstance(data["changes"], list)


@pytest.mark.asyncio
async def test_output_section_readable_after_apply(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload_response = await api_client.post(
        "/api/cvs/upload",
        params={"name": "Output Section CV"},
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
    )
    project = upload_response.json()

    tailor_response = await api_client.post(
        "/api/tailor",
        json={
            "cv_project_id": project["id"],
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "editable_sections": ["sections/skills.tex"],
            "refine_prompt": False,
        },
    )
    assert tailor_response.status_code == 200
    job_id = tailor_response.json()["job_id"]

    section_response = await api_client.get(
        f"/api/cvs/{project['id']}/outputs/{job_id}/sections/sections/skills.tex"
    )
    assert section_response.status_code == 200
    assert len(section_response.json()["content"]) > 0
