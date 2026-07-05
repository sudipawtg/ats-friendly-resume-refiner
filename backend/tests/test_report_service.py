import json

import pytest

from app.config import Settings
from app.services.cv_storage import CVStorageService
from app.services.report_service import ReportService
from app.services.tailoring_service import TailoringService
from tests.conftest import make_sample_cv_zip


@pytest.fixture
def report_env(tmp_path, sample_cv_zip):
    settings = Settings(storage_dir=tmp_path)
    storage = CVStorageService(settings)
    project = storage.save_upload("Report CV", sample_cv_zip)
    tailoring = TailoringService(settings)
    job_id = "report-job-001"
    job_record = {
        "id": job_id,
        "cv_project_id": project["id"],
        "status": "completed",
        "fit_analysis": {
            "overall_fit": 75,
            "strong_matches": ["Python"],
            "recommended_emphasis": ["LLM"],
            "potential_gaps": [],
        },
        "ats_analysis": {
            "overall_score": 70,
            "keyword_coverage": ["Python"],
            "missing_keywords": [],
            "formatting_notes": [],
            "improvements": [],
            "gaps": [],
            "star_assessment": [],
        },
        "changes": [],
        "job_description": {"title": "AI Engineer", "company": "Acme"},
    }
    tailoring._persist_job(job_record)
    return settings, project, job_id, tailoring


class TestReportService:
    def test_generate_html_report_for_job(self, report_env):
        settings, _, job_id, _ = report_env
        service = ReportService(settings)
        report_path = service.generate_html_report(job_id=job_id)
        assert report_path.exists()
        assert report_path.suffix == ".html"
        content = report_path.read_text(encoding="utf-8")
        assert "ResumeForge" in content

    def test_generate_html_report_missing_job_still_creates_file(self, report_env):
        settings, _, _, _ = report_env
        service = ReportService(settings)
        report_path = service.generate_html_report(job_id="nonexistent")
        assert report_path.exists()

    def test_report_respects_include_flags(self, report_env):
        settings, _, job_id, _ = report_env
        service = ReportService(settings)
        context = service._build_context(
            job_id=job_id,
            batch_id=None,
            include_ats=False,
            include_fit=False,
            include_changes=False,
            include_gaps=False,
        )
        assert context["include_ats"] is False
        assert context["include_fit"] is False
        assert len(context["jobs"]) == 1

    def test_batch_report_merges_summary(self, report_env, sample_cv_zip):
        settings, project, _, tailoring = report_env
        batch_id = "batch-report-001"
        job_entry_id = "batch-job-001"
        storage = CVStorageService(settings)
        storage.copy_master_to_output(project["id"], job_entry_id)
        storage.save_tailoring_summary(
            project["id"],
            job_entry_id,
            {
                "fit_analysis": {"overall_fit": 60, "strong_matches": [], "recommended_emphasis": [], "potential_gaps": []},
                "ats_analysis": {"overall_score": 55, "keyword_coverage": [], "missing_keywords": [], "formatting_notes": [], "improvements": [], "gaps": [], "star_assessment": []},
            },
        )
        batch = {
            "id": batch_id,
            "name": "Batch Report",
            "status": "completed",
            "cv_project_id": project["id"],
            "jobs": [
                {
                    "id": job_entry_id,
                    "status": "completed",
                    "company": "Acme",
                    "title": "Engineer",
                    "location": "London",
                    "fit_score": 60,
                    "key_skills": [],
                    "tailoring_status": "completed",
                    "warnings": [],
                    "job_description": {"title": "Engineer", "company": "Acme"},
                }
            ],
            "created_at": "2026-01-01T00:00:00",
        }
        batches = tailoring._load_batches()
        batches[batch_id] = batch
        tailoring._save_batches(batches)

        service = ReportService(settings)
        context = service._build_context(
            job_id=None,
            batch_id=batch_id,
            include_ats=True,
            include_fit=True,
            include_changes=True,
            include_gaps=True,
        )
        assert context["batch"]["name"] == "Batch Report"
        assert len(context["jobs"]) == 1
