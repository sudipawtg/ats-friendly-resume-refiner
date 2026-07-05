"""Tests for CV Coach co-assist review."""

import io

import pytest
from httpx import AsyncClient

from app.models.schemas import CVCoachReviewResponse, CVCoachSectionSuggestion
from app.constants import CoachPriority


@pytest.mark.asyncio
async def test_cv_coach_review_returns_suggestions(
    api_client: AsyncClient,
    sample_cv_zip: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        data={"name": "Coach Test CV"},
    )
    assert upload_response.status_code == 200
    project_id = upload_response.json()["id"]

    async def mock_review_master_cv(
        self,
        sections: dict[str, str],
        target_role: str = "",
        focus: str = "",
    ) -> CVCoachReviewResponse:
        first_section = next(iter(sections.keys()))
        return CVCoachReviewResponse(
            overall_score=78,
            summary="Strong AI engineering profile with room to sharpen experience bullets.",
            strengths=["Clear technical depth", "Production LLM experience"],
            top_improvements=["Add more metrics to recent role"],
            section_suggestions=[
                CVCoachSectionSuggestion(
                    section_path=first_section,
                    score=65,
                    priority=CoachPriority.HIGH,
                    issues=["Bullets could be more outcome-focused"],
                    suggested_instruction="Rewrite bullets with STAR structure and existing metrics only.",
                )
            ],
        )

    monkeypatch.setattr(
        "app.services.llm_service.LLMService.review_master_cv",
        mock_review_master_cv,
    )

    review_response = await api_client.post(
        f"/api/cvs/{project_id}/coach/review",
        json={"target_role": "Senior AI Engineer", "focus": "impact and measurable outcomes"},
    )
    assert review_response.status_code == 200
    payload = review_response.json()
    assert payload["overall_score"] == 78
    assert len(payload["section_suggestions"]) == 1
    assert payload["section_suggestions"][0]["priority"] == CoachPriority.HIGH


@pytest.mark.asyncio
async def test_cv_coach_apply_suggestion_updates_section(
    api_client: AsyncClient,
    sample_cv_zip: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        data={"name": "Coach Apply CV"},
    )
    project_id = upload_response.json()["id"]
    section_path = upload_response.json()["sections"][0]

    async def mock_refine_master_section(
        self,
        section_path: str,
        original: str,
        instruction: str,
        global_instruction: str = "",
    ) -> dict[str, str]:
        return {
            "content": "\\item Coach-improved content",
            "reason": "Applied coach suggestion",
        }

    monkeypatch.setattr(
        "app.services.llm_service.LLMService.refine_master_section",
        mock_refine_master_section,
    )

    refine_response = await api_client.post(
        f"/api/cvs/{project_id}/sections/refine",
        json={
            "section_path": section_path,
            "instruction": "Rewrite bullets with STAR structure and existing metrics only.",
            "global_instruction": "Optimize for target role: Senior AI Engineer",
        },
    )
    assert refine_response.status_code == 200
    assert "Coach-improved" in refine_response.json()["content"]
