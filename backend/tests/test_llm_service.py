import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.models.schemas import JobDescriptionExtract
from app.services.llm_service import LLMService


@pytest.fixture
def llm_no_key(tmp_path):
    return LLMService(Settings(storage_dir=tmp_path, openai_api_key=""))


@pytest.fixture
def llm_with_key(tmp_path):
    return LLMService(Settings(storage_dir=tmp_path, openai_api_key="sk-test-key"))


class TestIsConfigured:
    def test_false_without_api_key(self, llm_no_key):
        assert llm_no_key.is_configured is False

    def test_true_with_api_key(self, llm_with_key):
        assert llm_with_key.is_configured is True


class TestFallbackJobExtract:
    def test_extracts_skills_from_text(self, llm_no_key):
        text = "We need Python, AWS, LLM and RAG experience for this AI role. " * 5
        result = llm_no_key._fallback_job_extract(text)
        assert "python" in result.required_skills
        assert "aws" in result.required_skills
        assert result.extraction_confidence >= 0.2

    def test_low_confidence_for_short_text(self, llm_no_key):
        result = llm_no_key._fallback_job_extract("Short job")
        assert result.extraction_confidence == 0.0

    def test_truncates_raw_text(self, llm_no_key):
        long_text = "word " * 3000
        result = llm_no_key._fallback_job_extract(long_text)
        assert len(result.raw_text) <= 5000


class TestRefinePrompt:
    @pytest.mark.asyncio
    async def test_empty_instruction_returns_star_defaults(self, llm_no_key):
        result = await llm_no_key.refine_prompt("")
        assert "STAR" in result.methodology_applied
        assert len(result.suggestions) >= 1

    @pytest.mark.asyncio
    async def test_without_api_key_returns_original(self, llm_no_key):
        instruction = "Emphasise Python and ML experience"
        result = await llm_no_key.refine_prompt(instruction)
        assert result.refined_instruction == instruction
        assert any("OPENAI_API_KEY" in s for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_with_api_key_calls_chat(self, llm_with_key):
        mock_response = json.dumps({
            "refined_instruction": "Refined: emphasise Python",
            "methodology_applied": "STAR",
            "suggestions": ["Add metrics"],
        })
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_with_key.refine_prompt("Emphasise Python")
        assert "Refined" in result.refined_instruction

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back(self, llm_with_key):
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value="not json"):
            result = await llm_with_key.refine_prompt("Keep it concise")
        assert result.refined_instruction == "Keep it concise"


class TestAnalyzeFit:
    @pytest.mark.asyncio
    async def test_without_api_key_returns_placeholder(self, llm_no_key):
        job = JobDescriptionExtract(title="AI Engineer", company="Acme")
        result = await llm_no_key.analyze_fit({"sections/skills.tex": "\\item Python"}, job)
        assert result.overall_fit == 50
        assert len(result.potential_gaps) >= 1

    @pytest.mark.asyncio
    async def test_with_api_key_parses_response(self, llm_with_key):
        mock_response = json.dumps({
            "overall_fit": 78,
            "strong_matches": ["Python"],
            "recommended_emphasis": ["LLM"],
            "potential_gaps": ["Kubernetes"],
        })
        job = JobDescriptionExtract(title="AI Engineer")
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_with_key.analyze_fit({"sections/skills.tex": "\\item Python"}, job)
        assert result.overall_fit == 78
        assert "Python" in result.strong_matches


class TestAnalyzeAts:
    @pytest.mark.asyncio
    async def test_without_api_key_returns_placeholder(self, llm_no_key):
        job = JobDescriptionExtract(title="Data Analyst")
        result = await llm_no_key.analyze_ats({}, job)
        assert result.overall_score == 50

    @pytest.mark.asyncio
    async def test_with_api_key_parses_response(self, llm_with_key):
        mock_response = json.dumps({
            "overall_score": 65,
            "keyword_coverage": ["Python"],
            "missing_keywords": ["Spark"],
            "formatting_notes": [],
            "improvements": ["Add SQL"],
            "gaps": [],
            "star_assessment": ["Good structure"],
        })
        job = JobDescriptionExtract(title="Engineer")
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_with_key.analyze_ats({}, job, "Use STAR")
        assert result.overall_score == 65


class TestTailorSections:
    @pytest.mark.asyncio
    async def test_without_api_key_returns_empty(self, llm_no_key):
        job = JobDescriptionExtract(title="Engineer", company="Acme")
        result = await llm_no_key.tailor_sections(
            {"sections/skills.tex": "\\item Python"},
            ["sections/skills.tex"],
            job,
            "",
            {},
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_skips_unchanged_sections(self, llm_with_key):
        original = "\\item Python"
        mock_response = json.dumps({
            "proposed_text": original,
            "reason": "No change needed",
            "job_requirement": "",
            "evidence_used": "",
        })
        job = JobDescriptionExtract(title="Engineer", company="Acme")
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_with_key.tailor_sections(
                {"sections/skills.tex": original},
                ["sections/skills.tex"],
                job,
                "Tailor for AI",
                {},
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_changes_for_modified_sections(self, llm_with_key):
        original = "\\item Python"
        proposed = "\\item Python, PyTorch, LLM"
        mock_response = json.dumps({
            "proposed_text": proposed,
            "reason": "Aligned with job",
            "job_requirement": "ML skills",
            "evidence_used": "Existing Python",
        })
        job = JobDescriptionExtract(title="AI Engineer", company="Acme", required_skills=["Python"])
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_with_key.tailor_sections(
                {"sections/skills.tex": original},
                ["sections/skills.tex"],
                job,
                "Emphasise AI",
                {},
            )
        assert len(result) == 1
        assert result[0].proposed_text == proposed
        assert result[0].section_path == "sections/skills.tex"

    @pytest.mark.asyncio
    async def test_skips_empty_non_objective_sections(self, llm_with_key):
        job = JobDescriptionExtract(title="Engineer")
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock) as mock_chat:
            result = await llm_with_key.tailor_sections(
                {"sections/activities.tex": ""},
                ["sections/activities.tex"],
                job,
                "",
                {},
            )
        mock_chat.assert_not_called()
        assert result == []


class TestExtractJobDescription:
    @pytest.mark.asyncio
    async def test_uses_fallback_without_api_key(self, llm_no_key):
        text = "Senior Python developer needed with AWS and LLM experience. " * 10
        result = await llm_no_key.extract_job_description(text)
        assert isinstance(result, JobDescriptionExtract)
        assert result.extraction_confidence >= 0.2

    @pytest.mark.asyncio
    async def test_parses_llm_response(self, llm_with_key):
        mock_response = json.dumps({
            "company": "Acme",
            "title": "AI Engineer",
            "location": "London",
            "required_skills": ["Python"],
            "extraction_confidence": 0.9,
        })
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_with_key.extract_job_description("Job posting text")
        assert result.company == "Acme"
        assert result.title == "AI Engineer"

    @pytest.mark.asyncio
    async def test_coerces_null_optional_job_fields(self, llm_with_key):
        mock_response = json.dumps({
            "company": "Searchability NS&D",
            "title": "AI Software Engineer",
            "location": "London",
            "salary": None,
            "visa_requirements": None,
            "required_skills": ["Python"],
            "extraction_confidence": 0.9,
        })
        with patch.object(llm_with_key, "_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_with_key.extract_job_description("Job posting text")
        assert result.salary == ""
        assert result.visa_requirements == ""
