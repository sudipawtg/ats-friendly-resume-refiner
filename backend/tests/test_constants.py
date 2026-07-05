import pytest

from app.constants import (
    DATE_FILTER_OPTIONS,
    DEFAULT_GLOBAL_INSTRUCTIONS,
    DEFAULT_SECTIONS,
    INSTRUCTION_PROFILES,
    JOB_SEARCH_SOURCES,
    LOCKED_CV_FILES,
    STAR_METHODOLOGY_INSTRUCTION,
    BatchStatus,
    ChangeStatus,
    JobStatus,
)


class TestJobStatus:
    def test_all_statuses_defined(self):
        expected = {
            "queued",
            "processing",
            "pending",
            "crawling",
            "needs_manual",
            "ready",
            "tailoring",
            "completed",
            "failed",
        }
        assert {s.value for s in JobStatus} == expected


class TestBatchStatus:
    def test_all_statuses_defined(self):
        expected = {"draft", "processing", "completed", "partial"}
        assert {s.value for s in BatchStatus} == expected


class TestChangeStatus:
    def test_all_statuses_defined(self):
        expected = {"pending", "accepted", "rejected", "edited"}
        assert {s.value for s in ChangeStatus} == expected


class TestInstructionProfiles:
    def test_all_profiles_have_content(self):
        for profile_id, text in INSTRUCTION_PROFILES.items():
            assert profile_id
            assert len(text) > 20

    def test_expected_profiles_exist(self):
        expected_ids = {
            "ai_engineer",
            "ai_consultant",
            "ai_product_manager",
            "data_analyst",
            "technical_product_manager",
            "research_academic",
        }
        assert set(INSTRUCTION_PROFILES.keys()) == expected_ids


class TestJobSearchSources:
    def test_all_sources_have_labels(self):
        for source_id, label in JOB_SEARCH_SOURCES.items():
            assert source_id
            assert len(label) > 2


class TestDateFilterOptions:
    def test_valid_day_ranges(self):
        assert DATE_FILTER_OPTIONS["7"] == 7
        assert DATE_FILTER_OPTIONS["30"] == 30
        assert all(days > 0 for days in DATE_FILTER_OPTIONS.values())


class TestDefaultSections:
    def test_five_default_sections(self):
        assert len(DEFAULT_SECTIONS) == 5
        assert all(s.startswith("sections/") for s in DEFAULT_SECTIONS)


class TestLockedCvFiles:
    def test_resume_tex_locked(self):
        assert "resume.tex" in LOCKED_CV_FILES
        assert "TLCresume.sty" in LOCKED_CV_FILES


class TestDefaultInstructions:
    def test_global_instructions_not_empty(self):
        assert "professional" in DEFAULT_GLOBAL_INSTRUCTIONS.lower()
        assert "invent" in DEFAULT_GLOBAL_INSTRUCTIONS.lower()

    def test_star_methodology_mentions_star(self):
        assert "STAR" in STAR_METHODOLOGY_INSTRUCTION
