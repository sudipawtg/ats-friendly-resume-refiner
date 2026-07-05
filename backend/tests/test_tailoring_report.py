import json

import pytest

from app.config import Settings
from app.models.schemas import TailorRequest
from app.services.report_service import ReportService
from app.services.tailoring_service import TailoringService


@pytest.fixture
def settings(tmp_path):
    return Settings(storage_dir=tmp_path, openai_api_key="")


@pytest.mark.asyncio
async def test_tailor_needs_manual_when_no_job_info(settings, tmp_path):
    from app.services.cv_storage import CVStorageService
    import io
    import zipfile

    storage = CVStorageService(settings)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("Resume/resume.tex", "\\documentclass{article}")
        zf.writestr("Resume/sections/skills.tex", "\\item Python")
    project = storage.save_upload("Test", buffer.getvalue())

    service = TailoringService(settings)
    request = TailorRequest(
        cv_project_id=project["id"],
        job_url="https://invalid.example.com/no-content",
        editable_sections=["sections/skills.tex"],
    )
    result = await service.tailor_single(request)
    assert result.status.value == "needs_manual" or result.status == "needs_manual"


def test_report_generation_for_job(settings):
    tailoring = TailoringService(settings)
    job_id = "test-job-123"
    jobs = tailoring._load_jobs()
    jobs[job_id] = {
        "id": job_id,
        "fit_analysis": {
            "overall_fit": 82,
            "strong_matches": ["Python", "RAG"],
            "recommended_emphasis": ["Business value"],
            "potential_gaps": ["Insurance domain"],
        },
        "ats_analysis": {
            "overall_score": 75,
            "keyword_coverage": ["Python"],
            "missing_keywords": ["Salesforce"],
            "formatting_notes": [],
            "improvements": ["Add metrics"],
            "gaps": ["Domain experience"],
            "star_assessment": ["Good action verbs"],
        },
        "changes": [],
        "job_description": {"title": "AI Engineer", "company": "PwC"},
    }
    tailoring._save_jobs(jobs)

    report_service = ReportService(settings)
    report_path = report_service.generate_html_report(job_id=job_id)
    content = report_path.read_text(encoding="utf-8")
    assert "ResumeForge" in content
    assert "82" in content
