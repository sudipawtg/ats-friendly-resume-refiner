import pytest
from pydantic import ValidationError

from app.constants import BatchStatus, ChangeStatus, JobStatus
from app.models.schemas import (
    ATSAnalysis,
    BatchCreateRequest,
    BatchJobEntry,
    FitAnalysis,
    HealthResponse,
    JobSearchRequest,
    PromptRefineRequest,
    SectionChange,
    TailorRequest,
)


class TestHealthResponse:
    def test_default_version(self):
        response = HealthResponse(status="ok")
        assert response.status == "ok"
        assert response.version == "1.0.0"


class TestFitAnalysis:
    def test_valid_score(self):
        fit = FitAnalysis(overall_fit=75)
        assert fit.overall_fit == 75

    def test_score_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            FitAnalysis(overall_fit=-1)

    def test_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            FitAnalysis(overall_fit=101)


class TestATSAnalysis:
    def test_valid_score(self):
        ats = ATSAnalysis(overall_score=80)
        assert ats.overall_score == 80

    def test_invalid_score_rejected(self):
        with pytest.raises(ValidationError):
            ATSAnalysis(overall_score=150)


class TestJobSearchRequest:
    def test_valid_request(self):
        req = JobSearchRequest(job_title="AI Engineer", location="London")
        assert req.max_days_old == 7
        assert "indeed_uk" in req.sources

    def test_job_title_too_short(self):
        with pytest.raises(ValidationError):
            JobSearchRequest(job_title="A")

    def test_max_days_old_bounds(self):
        with pytest.raises(ValidationError):
            JobSearchRequest(job_title="Engineer", max_days_old=0)
        with pytest.raises(ValidationError):
            JobSearchRequest(job_title="Engineer", max_days_old=31)

    def test_max_results_per_source_bounds(self):
        with pytest.raises(ValidationError):
            JobSearchRequest(job_title="Engineer", max_results_per_source=0)
        with pytest.raises(ValidationError):
            JobSearchRequest(job_title="Engineer", max_results_per_source=51)


class TestTailorRequest:
    def test_minimal_request(self):
        req = TailorRequest(cv_project_id="proj-123")
        assert req.refine_prompt is True
        assert req.editable_sections == []

    def test_with_job_description(self):
        req = TailorRequest(
            cv_project_id="proj-123",
            job_description="Senior Python developer needed",
        )
        assert req.job_description is not None


class TestBatchCreateRequest:
    def test_valid_batch(self):
        req = BatchCreateRequest(
            cv_project_id="proj-1",
            name="Campaign A",
            jobs=[BatchJobEntry(url="https://example.com/job/1")],
        )
        assert len(req.jobs) == 1
        assert req.name == "Campaign A"


class TestSectionChange:
    def test_default_status_pending(self):
        change = SectionChange(
            id="c1",
            section_path="sections/skills.tex",
            original_text="old",
            proposed_text="new",
            reason="align",
            job_requirement="Python",
            evidence_used="existing",
        )
        assert change.status == ChangeStatus.PENDING


class TestPromptRefineRequest:
    def test_requires_raw_instruction(self):
        req = PromptRefineRequest(raw_instruction="Emphasise leadership")
        assert req.context == ""
        assert req.target_section == ""


class TestEnumValues:
    def test_job_status_values(self):
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.NEEDS_MANUAL.value == "needs_manual"

    def test_batch_status_values(self):
        assert BatchStatus.PROCESSING.value == "processing"
        assert BatchStatus.PARTIAL.value == "partial"
