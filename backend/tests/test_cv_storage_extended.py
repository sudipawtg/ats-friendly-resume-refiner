import io
import zipfile

import pytest

from app.config import Settings
from app.services.cv_storage import CVStorageService


@pytest.fixture
def storage(tmp_path):
    settings = Settings(storage_dir=tmp_path)
    return CVStorageService(settings)


def _make_sample_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("Resume/resume.tex", "\\documentclass{article}\n\\begin{document}\n\\end{document}")
        zf.writestr("Resume/sections/skills.tex", "\\item Python")
        zf.writestr("Resume/sections/experience.tex", "\\item Built AI systems")
        zf.writestr("Resume/TLCresume.sty", "% style")
        zf.writestr("Resume/_header.tex", "% header")
    return buffer.getvalue()


def test_get_project_returns_none_for_missing(storage):
    assert storage.get_project("nonexistent") is None


def test_read_all_sections_empty_for_missing_project(storage):
    assert storage.read_all_sections("missing") == {}


def test_write_output_section(storage):
    project = storage.save_upload("Test CV", _make_sample_zip())
    path = storage.write_output_section(
        project["id"], "job-1", "sections/skills.tex", "\\item Updated Python"
    )
    assert path.exists()
    assert "Updated Python" in path.read_text(encoding="utf-8")


def test_copy_master_to_output_missing_project_raises(storage):
    with pytest.raises(ValueError, match="Project .* not found"):
        storage.copy_master_to_output("missing", "job-1")


def test_read_section_invalid_path_raises(storage):
    project = storage.save_upload("Test CV", _make_sample_zip())
    with pytest.raises(ValueError, match="Invalid section path"):
        storage.read_section(project["id"], "../../../etc/passwd")


def test_create_output_zip(storage):
    project = storage.save_upload("Test CV", _make_sample_zip())
    job_id = "zip-test"
    storage.copy_master_to_output(project["id"], job_id)
    storage.write_output_section(
        project["id"], job_id, "sections/skills.tex", "\\item Tailored"
    )
    zip_path = storage.create_output_zip(project["id"], job_id, "tailored_output")
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        assert any("skills.tex" in n for n in names)


def test_save_and_load_tailoring_summary(storage):
    project = storage.save_upload("Test CV", _make_sample_zip())
    job_id = "summary-test"
    storage.copy_master_to_output(project["id"], job_id)
    summary = {"job_id": job_id, "fit_score": 80}
    path = storage.save_tailoring_summary(project["id"], job_id, summary)
    assert path.exists()
    loaded = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert loaded["fit_score"] == 80


def test_instruction_profile_crud(storage):
    profile = {
        "id": "profile-1",
        "name": "Custom Profile",
        "global_instruction": "Be concise",
        "section_instructions": [],
        "created_at": "2026-01-01T00:00:00",
    }
    saved = storage.save_instruction_profile(profile)
    assert saved["id"] == "profile-1"

    profiles = storage.load_instruction_profiles()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Custom Profile"

    updated = {**profile, "name": "Updated Profile"}
    storage.save_instruction_profile(updated)
    assert storage.load_instruction_profiles()[0]["name"] == "Updated Profile"

    assert storage.delete_instruction_profile("profile-1") is True
    assert storage.load_instruction_profiles() == []
    assert storage.delete_instruction_profile("missing") is False


def test_load_instruction_profiles_empty_when_missing(storage):
    assert storage.load_instruction_profiles() == []


def test_nested_resume_without_sections_uses_defaults(storage):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Resume/resume.tex", "\\documentclass{article}")
        archive.writestr("Resume/sections/objective.tex", "\\item Goal")
        archive.writestr("Resume/TLCresume.sty", "% style")
        archive.writestr("Resume/_header.tex", "% header")
    project = storage.save_upload("Nested CV", buffer.getvalue())
    assert "sections/objective.tex" in project["sections"]

def test_multiple_projects_in_registry(storage):
    storage.save_upload("CV 1", _make_sample_zip())
    storage.save_upload("CV 2", _make_sample_zip())
    projects = storage.list_projects()
    assert len(projects) == 2
    names = {p["name"] for p in projects}
    assert names == {"CV 1", "CV 2"}
