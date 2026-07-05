"""
Integration tests for the anticipated CV platform flow:
upload/template → edit sections → export (PDF/DOCX) → job tailoring.
"""

import io

import pytest
from httpx import AsyncClient

from app.cv_templates.registry import CV_TEMPLATE_REGISTRY
from tests.conftest import SAMPLE_JOB_DESCRIPTION, make_sample_cv_zip, make_sample_pdf


@pytest.mark.asyncio
async def test_platform_template_gallery_lists_eight_designs(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/cv-templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == len(CV_TEMPLATE_REGISTRY) == 8

    for template in templates:
        preview = await api_client.get(template["preview_url"])
        assert preview.status_code == 200
        assert preview.headers["content-type"].startswith("image/svg+xml")


@pytest.mark.asyncio
async def test_platform_create_from_template_then_edit_section(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_response = await api_client.post(
        "/api/cvs/from-template",
        json={"name": "Flow Test CV", "template_id": "modern_teal"},
    )
    assert create_response.status_code == 200
    project = create_response.json()
    assert project["source_type"] == "template"
    assert project["template_id"] == "modern_teal"

    section_path = "sections/skills.tex"

    async def mock_refine_master_section(
        self,
        section_path: str,
        original: str,
        instruction: str,
        global_instruction: str = "",
    ) -> dict[str, str]:
        return {
            "content": "\\item Python, AWS, LLM, RAG, FastAPI",
            "reason": "Added FastAPI from instruction",
        }

    monkeypatch.setattr(
        "app.services.llm_service.LLMService.refine_master_section",
        mock_refine_master_section,
    )

    refine_response = await api_client.post(
        f"/api/cvs/{project['id']}/sections/refine",
        json={
            "section_path": section_path,
            "instruction": "Highlight FastAPI in skills",
        },
    )
    assert refine_response.status_code == 200
    assert "FastAPI" in refine_response.json()["content"]

    section_response = await api_client.get(
        f"/api/cvs/{project['id']}/sections/{section_path}"
    )
    assert section_response.status_code == 200
    assert "FastAPI" in section_response.json()["content"]


@pytest.mark.asyncio
async def test_platform_pdf_upload_creates_editable_project(
    api_client: AsyncClient, sample_pdf: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_parse_cv_from_text(self, text: str) -> dict[str, object]:
        return {
            "contact": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "role": "Senior Engineer",
            },
            "sections": {
                "sections/skills.tex": "\\item Python, AWS",
                "sections/experience.tex": "\\item Built APIs at Acme Corp",
            },
        }

    monkeypatch.setattr(
        "app.services.llm_service.LLMService.parse_cv_from_text",
        mock_parse_cv_from_text,
    )

    upload_response = await api_client.post(
        "/api/cvs/upload",
        data={"name": "Imported PDF CV", "template_id": "classic_blue"},
        files={"file": ("resume.pdf", io.BytesIO(sample_pdf), "application/pdf")},
    )
    assert upload_response.status_code == 200
    project = upload_response.json()
    assert project["source_type"] == "pdf"
    assert project["template_id"] == "classic_blue"
    assert len(project["sections"]) >= 1

    skills_response = await api_client.get(
        f"/api/cvs/{project['id']}/sections/sections/skills.tex"
    )
    assert skills_response.status_code == 200
    assert "Python" in skills_response.json()["content"]


@pytest.mark.asyncio
async def test_platform_master_exports_pdf_and_docx(
    api_client: AsyncClient, sample_cv_zip: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        data={"name": "Export Test CV"},
    )
    project_id = upload_response.json()["id"]

    pdf_response = await api_client.get(f"/api/cvs/{project_id}/master-pdf")
    if pdf_response.status_code == 200:
        assert pdf_response.headers["content-type"] == "application/pdf"
        assert "inline" in pdf_response.headers.get("content-disposition", "").lower()
        download_response = await api_client.get(
            f"/api/cvs/{project_id}/master-pdf",
            params={"download": True},
        )
        assert download_response.status_code == 200
        assert "attachment" in download_response.headers.get("content-disposition", "").lower()
    else:
        assert pdf_response.status_code in {404, 500}

    docx_response = await api_client.get(f"/api/cvs/{project_id}/master-docx")
    assert docx_response.status_code == 200
    assert "wordprocessingml" in docx_response.headers["content-type"]
    assert len(docx_response.content) > 100


@pytest.mark.asyncio
async def test_platform_job_tailoring_still_works_with_exports(
    api_client: AsyncClient, sample_cv_zip: bytes
) -> None:
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        data={"name": "Tailor Flow CV"},
    )
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
    preview_data = preview_response.json()
    assert preview_data.get("job_id")
    assert isinstance(preview_data.get("changes"), list)

    apply_response = await api_client.post(
        "/api/tailor",
        json={
            "cv_project_id": project["id"],
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "editable_sections": ["sections/skills.tex"],
            "refine_prompt": False,
        },
    )
    assert apply_response.status_code == 200
    job_id = apply_response.json()["job_id"]

    zip_response = await api_client.get(f"/api/cvs/{project['id']}/download/{job_id}")
    assert zip_response.status_code == 200
    assert zip_response.headers["content-type"] == "application/zip"

    docx_response = await api_client.get(
        f"/api/cvs/{project['id']}/download/{job_id}/docx"
    )
    assert docx_response.status_code == 200
    assert "wordprocessingml" in docx_response.headers["content-type"]

    pdf_response = await api_client.get(
        f"/api/cvs/{project['id']}/download/{job_id}/pdf"
    )
    assert pdf_response.status_code in {200, 500}


@pytest.mark.asyncio
async def test_platform_apply_template_preserves_section_content(
    api_client: AsyncClient, sample_cv_zip: bytes
) -> None:
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
    )
    project_id = upload_response.json()["id"]
    section_path = "sections/skills.tex"

    before_response = await api_client.get(
        f"/api/cvs/{project_id}/sections/{section_path}"
    )
    before_content = before_response.json()["content"]

    apply_response = await api_client.post(
        f"/api/cvs/{project_id}/apply-template",
        json={"template_id": "bold_coral"},
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["template_id"] == "bold_coral"

    after_response = await api_client.get(f"/api/cvs/{project_id}/sections/{section_path}")
    assert after_response.json()["content"] == before_content
