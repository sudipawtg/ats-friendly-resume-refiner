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


def test_save_upload_discovers_sections(storage):
    project = storage.save_upload("Test CV", _make_sample_zip())
    assert project["id"]
    assert len(project["sections"]) >= 2
    assert any("skills" in s for s in project["sections"])
    assert project["master_root"] == "master/Resume"


def test_overleaf_layout_sections_at_project_root(storage, tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Resume/resume.tex", "\\documentclass{article}\n\\input{sections/skills}")
        archive.writestr("sections/skills.tex", "\\item Python")
        archive.writestr("sections/experience.tex", "\\item AI")
        archive.writestr("TLCresume.sty", "% style")
        archive.writestr("_header.tex", "% header")
    project = storage.save_upload("Overleaf CV", buffer.getvalue())
    assert project["master_root"] == "master"
    assert project["master_file"] == "Resume/resume.tex"
    assert len(project["sections"]) == 2


def test_read_section(storage):
    project = storage.save_upload("Test CV", _make_sample_zip())
    content = storage.read_section(project["id"], project["sections"][0])
    assert len(content) > 0


def test_list_projects(storage):
    storage.save_upload("CV 1", _make_sample_zip())
    projects = storage.list_projects()
    assert len(projects) == 1


def test_tenant_scoped_storage_paths(tmp_path):
    settings = Settings(storage_dir=tmp_path)
    tenant_storage = CVStorageService(settings, tenant_id="tenant-alpha")
    project = tenant_storage.save_upload("Tenant CV", _make_sample_zip())
    assert (tmp_path / "tenant-alpha" / "cvs" / project["id"]).exists()
    assert project.get("tenant_id") == "tenant-alpha"
