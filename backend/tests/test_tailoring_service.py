import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.constants import ChangeStatus, JobStatus
from app.models.schemas import (
    ATSAnalysis,
    BatchCreateRequest,
    BatchJobEntry,
    FitAnalysis,
    JobDescriptionExtract,
    SectionChange,
    TailorRequest,
)
from app.services.cv_storage import CVStorageService
from app.services.tailoring_service import TailoringService
from tests.conftest import SAMPLE_JOB_DESCRIPTION, make_sample_cv_zip


@pytest.fixture
def tailoring_env(tmp_path, sample_cv_zip):
    settings = Settings(storage_dir=tmp_path, openai_api_key="")
    storage = CVStorageService(settings)
    project = storage.save_upload("Tailor Test", sample_cv_zip)
    service = TailoringService(settings)
    return settings, storage, project, service


def _mock_job_extract() -> JobDescriptionExtract:
    return JobDescriptionExtract(
        company="Acme Corp",
        title="Senior AI Engineer",
        location="London, UK",
        required_skills=["Python", "AWS", "LLM"],
        technologies=["PyTorch", "LangChain"],
        responsibilities=["Build RAG pipelines", "Deploy models"],
        raw_text=SAMPLE_JOB_DESCRIPTION,
        extraction_confidence=0.85,
    )


def _mock_fit() -> FitAnalysis:
    return FitAnalysis(
        overall_fit=72,
        strong_matches=["Python", "AWS"],
        recommended_emphasis=["LLM", "RAG"],
        potential_gaps=["Kubernetes"],
    )


def _mock_ats() -> ATSAnalysis:
    return ATSAnalysis(
        overall_score=68,
        keyword_coverage=["Python"],
        missing_keywords=["Spark"],
        improvements=["Add metrics"],
        gaps=[],
        star_assessment=["Good bullets"],
    )


class TestTailoringServiceGetters:
    def test_get_job_returns_none_for_missing(self, tailoring_env):
        _, _, _, service = tailoring_env
        assert service.get_job("missing") is None

    def test_get_batch_returns_none_for_missing(self, tailoring_env):
        _, _, _, service = tailoring_env
        assert service.get_batch("missing") is None

    def test_list_batches_empty(self, tailoring_env):
        _, _, _, service = tailoring_env
        assert service.list_batches() == []


class TestUpdateChangeStatus:
    def test_updates_existing_change(self, tailoring_env):
        _, _, project, service = tailoring_env
        job_id = "job-change-test"
        change = SectionChange(
            id="change-1",
            section_path="sections/skills.tex",
            original_text="old",
            proposed_text="new",
            reason="test",
            job_requirement="Python",
            evidence_used="existing",
        )
        service._persist_job({
            "id": job_id,
            "cv_project_id": project["id"],
            "changes": [change.model_dump()],
        })
        result = service.update_change_status(job_id, "change-1", ChangeStatus.ACCEPTED.value)
        assert result is not None
        assert result.status == ChangeStatus.ACCEPTED

    def test_edited_text_sets_edited_status(self, tailoring_env):
        _, _, project, service = tailoring_env
        job_id = "job-edit-test"
        change = SectionChange(
            id="change-2",
            section_path="sections/skills.tex",
            original_text="old",
            proposed_text="new",
            reason="test",
            job_requirement="",
            evidence_used="",
        )
        service._persist_job({
            "id": job_id,
            "cv_project_id": project["id"],
            "changes": [change.model_dump()],
        })
        result = service.update_change_status(
            job_id, "change-2", ChangeStatus.ACCEPTED.value, edited_text="custom text"
        )
        assert result is not None
        assert result.proposed_text == "custom text"
        assert result.status == ChangeStatus.EDITED

    def test_returns_none_for_missing_job(self, tailoring_env):
        _, _, _, service = tailoring_env
        assert service.update_change_status("missing", "c1", "accepted") is None

    def test_returns_none_for_missing_change(self, tailoring_env):
        _, _, project, service = tailoring_env
        job_id = "job-no-change"
        service._persist_job({"id": job_id, "cv_project_id": project["id"], "changes": []})
        assert service.update_change_status(job_id, "missing-change", "accepted") is None


class TestTailorSingle:
    @pytest.mark.asyncio
    async def test_tailor_with_manual_description(self, tailoring_env):
        _, _, project, service = tailoring_env
        request = TailorRequest(
            cv_project_id=project["id"],
            job_description=SAMPLE_JOB_DESCRIPTION,
            refine_prompt=False,
        )
        with patch.object(service._crawler, "extract_job", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = _mock_job_extract()
            with patch.object(service._llm, "analyze_fit", new_callable=AsyncMock) as mock_fit:
                mock_fit.return_value = _mock_fit()
                with patch.object(service._llm, "analyze_ats", new_callable=AsyncMock) as mock_ats:
                    mock_ats.return_value = _mock_ats()
                    with patch.object(service._llm, "tailor_sections", new_callable=AsyncMock) as mock_tailor:
                        mock_tailor.return_value = [
                            SectionChange(
                                id="c1",
                                section_path="sections/skills.tex",
                                original_text="\\item Python",
                                proposed_text="\\item Python, LLM, RAG",
                                reason="Aligned",
                                job_requirement="AI skills",
                                evidence_used="Python",
                            )
                        ]
                        result = await service.tailor_single(request)

        assert result.job_id
        assert result.status == JobStatus.COMPLETED
        assert result.fit_analysis.overall_fit == 72
        assert len(result.changes) == 1

        job = service.get_job(result.job_id)
        assert job is not None
        assert job["status"] == JobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_tailor_missing_project_raises(self, tailoring_env):
        _, _, _, service = tailoring_env
        request = TailorRequest(cv_project_id="missing", job_description=SAMPLE_JOB_DESCRIPTION)
        with pytest.raises(ValueError, match="CV project not found"):
            await service.tailor_single(request)

    @pytest.mark.asyncio
    async def test_tailor_low_confidence_returns_needs_manual(self, tailoring_env):
        _, _, project, service = tailoring_env
        request = TailorRequest(
            cv_project_id=project["id"],
            job_url="http://example.com/job",
            refine_prompt=False,
        )
        low_confidence = JobDescriptionExtract(raw_text="short", extraction_confidence=0.0)
        with patch.object(service._crawler, "extract_job", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = low_confidence
            result = await service.tailor_single(request)

        assert result.status == JobStatus.NEEDS_MANUAL
        assert result.changes == []


class TestCreateBatch:
    @pytest.mark.asyncio
    async def test_deduplicates_urls(self, tailoring_env):
        _, _, project, service = tailoring_env
        request = BatchCreateRequest(
            cv_project_id=project["id"],
            name="Dedup Batch",
            jobs=[
                BatchJobEntry(url="https://example.com/job/1"),
                BatchJobEntry(url="https://example.com/job/1"),
                BatchJobEntry(url="https://example.com/job/2"),
            ],
        )
        response = await service.create_batch(request)
        assert response.total_jobs == 2

    @pytest.mark.asyncio
    async def test_batch_response_counts(self, tailoring_env):
        _, _, project, service = tailoring_env
        request = BatchCreateRequest(
            cv_project_id=project["id"],
            name="Count Batch",
            jobs=[BatchJobEntry(manual_description=SAMPLE_JOB_DESCRIPTION)],
        )
        response = await service.create_batch(request)
        assert response.status.value == "processing"
        assert response.total_jobs == 1
        assert response.processing >= 1

    def test_to_batch_response(self, tailoring_env):
        _, _, project, service = tailoring_env
        batch = {
            "id": "batch-1",
            "name": "Test",
            "status": "processing",
            "cv_project_id": project["id"],
            "jobs": [
                {"id": "j1", "status": "pending", "company": "", "title": "", "location": "",
                 "fit_score": None, "key_skills": [], "tailoring_status": "", "warnings": []},
            ],
            "created_at": "2026-01-01T00:00:00",
        }
        response = service._to_batch_response(batch)
        assert response.total_jobs == 1
        assert response.processing == 1
