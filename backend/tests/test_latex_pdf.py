import io
import shutil
import zipfile

import pytest
from pypdf import PdfReader

from app.config import Settings
from app.services.cv_storage import CVStorageService
from app.services.latex_compile_service import LatexCompileService
from app.services.pdf_service import CVPdfService
from tests.conftest import make_resume_latex_zip


def _extract_pdf_text(pdf_path) -> str:
    reader = PdfReader(str(pdf_path))
    return "".join(page.extract_text() or "" for page in reader.pages)


@pytest.fixture
def storage(tmp_path):
    settings = Settings(storage_dir=tmp_path)
    return CVStorageService(settings)


def test_resume_latex_upload_discovers_all_sections(storage):
    project = storage.save_upload("Sudip CV", make_resume_latex_zip())
    assert len(project["sections"]) == 5
    assert "sections/skills.tex" in project["sections"]
    assert "sections/experience.tex" in project["sections"]
    assert project["master_file"] == "Resume/resume.tex"
    assert project["master_root"] == "master"


def test_resume_latex_sections_readable(storage):
    project = storage.save_upload("Sudip CV", make_resume_latex_zip())
    skills = storage.read_section(project["id"], "sections/skills.tex")
    experience = storage.read_section(project["id"], "sections/experience.tex")
    assert "Python" in skills
    assert "AWTG" in experience or "Accenture" in experience


def test_resume_latex_output_preserves_structure(storage, tmp_path):
    project = storage.save_upload("Sudip CV", make_resume_latex_zip())
    job_id = "test-job-pdf"
    output_dir = storage.copy_master_to_output(project["id"], job_id)

    assert (output_dir / "Resume" / "resume.tex").exists()
    assert (output_dir / "sections" / "skills.tex").exists()
    assert (output_dir / "TLCresume.sty").exists()
    assert (output_dir / "_header.tex").exists()


@pytest.mark.skipif(not shutil.which("tectonic") and not shutil.which("pdflatex"), reason="No LaTeX compiler")
def test_resume_latex_compiles_to_pdf(storage, tmp_path):
    settings = Settings(storage_dir=tmp_path)
    project = storage.save_upload("Sudip CV", make_resume_latex_zip())
    job_id = "compile-test"
    output_dir = storage.copy_master_to_output(project["id"], job_id)

    compiler = LatexCompileService(settings)
    pdf_path = compiler.compile_output_to_pdf(output_dir, project["master_file"])
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 10_000

    pdf_text = _extract_pdf_text(pdf_path)
    assert "Sudip" in pdf_text
    assert "AWTG" in pdf_text or "Accenture" in pdf_text
    assert "Python" in pdf_text


@pytest.mark.skipif(not shutil.which("tectonic") and not shutil.which("pdflatex"), reason="No LaTeX compiler")
def test_pdf_service_compiles_tailored_output(storage, tmp_path):
    settings = Settings(storage_dir=tmp_path)
    project = storage.save_upload("Sudip CV", make_resume_latex_zip())
    job_id = "pdf-service-test"
    storage.copy_master_to_output(project["id"], job_id)

    pdf_path = CVPdfService(settings).generate_tailored_pdf(project["id"], job_id)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 10_000

    pdf_text = _extract_pdf_text(pdf_path)
    assert "Executive" not in pdf_text
    assert "Sudip" in pdf_text
    assert "Python" in pdf_text
