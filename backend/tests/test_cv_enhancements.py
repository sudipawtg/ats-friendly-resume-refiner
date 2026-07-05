"""Tests for settings persistence, section history, coach chat, and manual section save."""

import io

import pytest
from httpx import AsyncClient

from app.models.schemas import CoachChatResponse


@pytest.mark.asyncio
async def test_tailoring_preferences_persist(api_client: AsyncClient) -> None:
    save_response = await api_client.put(
        "/api/settings/tailoring",
        json={
            "global_instruction": "Use UK English and STAR bullets.",
            "section_instructions": {"sections/skills.tex": "Group skills by category."},
        },
    )
    assert save_response.status_code == 200
    payload = save_response.json()
    assert payload["global_instruction"] == "Use UK English and STAR bullets."
    assert payload["section_instructions"]["sections/skills.tex"] == "Group skills by category."

    load_response = await api_client.get("/api/settings/tailoring")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["global_instruction"] == "Use UK English and STAR bullets."


@pytest.mark.asyncio
async def test_manual_section_save_and_restore(api_client: AsyncClient, sample_cv_zip: bytes) -> None:
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        data={"name": "History Test CV"},
    )
    project_id = upload_response.json()["id"]
    section_path = upload_response.json()["sections"][0]

    original = await api_client.get(f"/api/cvs/{project_id}/sections/{section_path}")
    original_content = original.json()["content"]

    save_response = await api_client.put(
        f"/api/cvs/{project_id}/sections/{section_path}",
        json={"content": "\\item Manual edit content"},
    )
    assert save_response.status_code == 200

    history_response = await api_client.get(
        f"/api/cvs/{project_id}/sections/{section_path}/history"
    )
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 1

    restore_response = await api_client.post(
        f"/api/cvs/{project_id}/sections/{section_path}/restore",
        json={"version_id": history[0]["version_id"]},
    )
    assert restore_response.status_code == 200
    assert original_content in restore_response.json()["content"]


@pytest.mark.asyncio
async def test_coach_chat_returns_reply(
    api_client: AsyncClient,
    sample_cv_zip: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_response = await api_client.post(
        "/api/cvs/upload",
        files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        data={"name": "Chat Test CV"},
    )
    project_id = upload_response.json()["id"]

    async def mock_coach_chat(
        self,
        sections: dict[str, str],
        message: str,
        history: list[dict[str, str]],
        target_role: str = "",
        focus: str = "",
    ) -> CoachChatResponse:
        first_section = next(iter(sections.keys()))
        return CoachChatResponse(
            reply="Try tightening your experience bullets with metrics you already have.",
            suggested_section_path=first_section,
            suggested_instruction="Make bullets shorter and more outcome-focused.",
        )

    monkeypatch.setattr(
        "app.services.llm_service.LLMService.coach_chat",
        mock_coach_chat,
    )

    chat_response = await api_client.post(
        f"/api/cvs/{project_id}/coach/chat",
        json={
            "message": "Make experience shorter",
            "history": [],
            "target_role": "Senior AI Engineer",
        },
    )
    assert chat_response.status_code == 200
    payload = chat_response.json()
    assert "experience" in payload["reply"].lower() or "bullets" in payload["reply"].lower()
    assert payload["suggested_section_path"]
    assert payload["suggested_instruction"]
