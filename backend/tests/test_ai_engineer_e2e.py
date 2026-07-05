import io

import pytest
from httpx import AsyncClient

from tests.conftest import make_sample_cv_zip

AI_ENGINEER_JOB = """
AI Engineer — TechNova Ltd, London, UK (Hybrid)

We are hiring an AI Engineer to design and deploy production LLM applications.
You will build RAG pipelines, integrate OpenAI and Azure APIs, and ship FastAPI microservices on AWS.

Responsibilities:
- Develop and fine-tune LLM-based features for enterprise clients
- Build retrieval-augmented generation pipelines with LangChain
- Collaborate with product and data teams on model evaluation
- Deploy services with Docker and Kubernetes

Required: Python, PyTorch, LLMs, RAG, AWS, FastAPI, 3+ years ML engineering experience.
Preferred: MLOps, vector databases, stakeholder communication.
""".strip()


@pytest.mark.asyncio
async def test_ai_engineer_full_journey(api_client: AsyncClient) -> None:
    zip_bytes = make_sample_cv_zip()
    upload = await api_client.post(
        "/api/cvs/upload",
        params={"name": "AI Engineer Test CV"},
        files={"file": ("master_cv.zip", io.BytesIO(zip_bytes), "application/zip")},
    )
    assert upload.status_code == 200
    project = upload.json()

    preview = await api_client.get(
        f"/api/cvs/{project['id']}/sections/sections/skills.tex"
    )
    assert preview.status_code == 200
    assert len(preview.json()["content"]) > 0

    crawl = await api_client.post(
        "/api/crawl",
        json={"url": "", "manual_description": AI_ENGINEER_JOB},
    )
    assert crawl.status_code == 200
    job_data = crawl.json()
    assert job_data["extraction_confidence"] >= 0.2

    tailor = await api_client.post(
        "/api/tailor",
        json={
            "cv_project_id": project["id"],
            "job_description": AI_ENGINEER_JOB,
            "editable_sections": ["sections/skills.tex", "sections/experience.tex"],
            "global_instruction": (
                "Position me as an AI Engineer. Highlight Python, LLM, and RAG. Use STAR methodology."
            ),
            "instruction_profile_id": "ai_engineer",
            "refine_prompt": True,
        },
    )
    assert tailor.status_code == 200
    result = tailor.json()
    assert result["job_id"]
    assert result["status"] in ("completed", "needs_manual")
    assert result["fit_analysis"]["overall_fit"] >= 0
    assert result["ats_analysis"]["overall_score"] >= 0

    job_get = await api_client.get(f"/api/jobs/{result['job_id']}")
    assert job_get.status_code == 200

    if result["status"] == "completed":
        download = await api_client.get(
            f"/api/cvs/{project['id']}/download/{result['job_id']}"
        )
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"

        report = await api_client.post(
            "/api/reports/html",
            json={"job_id": result["job_id"]},
        )
        assert report.status_code == 200
        assert "ResumeForge" in report.text
