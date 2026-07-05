import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.config import Settings
from app.services.pdf_service import CVPdfService, latex_to_plain_text, _ascii_safe


class TestLatexToPlainText:
    def test_converts_item_commands_to_bullets(self):
        result = latex_to_plain_text("\\item Built AI systems\\item Deployed on AWS")
        assert "- Built AI systems" in result
        assert "- Deployed on AWS" in result

    def test_strips_textbf_and_emph(self):
        result = latex_to_plain_text("\\textbf{Senior Engineer} at \\emph{Acme Corp}")
        assert "Senior Engineer" in result
        assert "Acme Corp" in result

    def test_removes_braces_and_commands(self):
        result = latex_to_plain_text("\\section{Experience} \\item Python")
        assert "Experience" in result
        assert "Python" in result
        assert "{" not in result

    def test_normalizes_unicode_dashes(self):
        result = latex_to_plain_text("Python \u2014 AWS \u2013 ML")
        assert "\u2014" not in result
        assert "Python - AWS - ML" in result

    def test_collapses_whitespace(self):
        result = latex_to_plain_text("  Python   AWS   \n\n  LLM  ")
        assert result == "Python AWS LLM"

    def test_empty_string(self):
        assert latex_to_plain_text("") == ""

    def test_preserves_plain_text(self):
        assert latex_to_plain_text("Plain skills list") == "Plain skills list"


class TestAsciiSafe:
    def test_replaces_unicode_dashes(self):
        assert _ascii_safe("a\u2014b\u2013c\u2022d") == "a-b-c-d"


@pytest.fixture
def pdf_settings(tmp_path):
    return Settings(storage_dir=tmp_path)


@pytest.fixture
def pdf_storage_setup(pdf_settings, sample_cv_zip):
    from app.services.cv_storage import CVStorageService

    storage = CVStorageService(pdf_settings)
    project = storage.save_upload("PDF Test CV", sample_cv_zip)
    job_id = "fallback-job-001"
    output_dir = storage.copy_master_to_output(project["id"], job_id)
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    (sections_dir / "skills.tex").write_text(
        "\\item \\textbf{Python}, AWS, LLM, RAG pipelines",
        encoding="utf-8",
    )
    (sections_dir / "experience.tex").write_text(
        "\\item Built enterprise AI systems with Azure OpenAI",
        encoding="utf-8",
    )
    summary = {
        "job_description": {
            "company": "Acme Corp",
            "raw_text": "Senior AI Engineer\nLondon, UK",
        }
    }
    storage.save_tailoring_summary(project["id"], job_id, summary)
    return pdf_settings, project["id"], job_id


def test_text_fallback_pdf_generation(pdf_storage_setup):
    settings, project_id, job_id = pdf_storage_setup
    service = CVPdfService(settings)

    from app.services.latex_compile_service import LatexCompileError

    original_compile = service._compiler.compile_output_to_pdf

    def raise_compile_error(output_dir, master_file):
        raise LatexCompileError("No compiler in test")

    service._compiler.compile_output_to_pdf = raise_compile_error

    pdf_path = service.generate_tailored_pdf(project_id, job_id)
    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.stat().st_size > 500

    reader = PdfReader(str(pdf_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Python" in text or "Tailored CV" in text


def test_generate_tailored_pdf_missing_output_raises(pdf_settings):
    service = CVPdfService(pdf_settings)
    with pytest.raises(FileNotFoundError, match="not found"):
        service.generate_tailored_pdf("missing-project", "missing-job")


def test_generate_tailored_pdf_missing_project_raises(pdf_settings, tmp_path):
    output_dir = tmp_path / "outputs" / "proj-1" / "job-1" / "sections"
    output_dir.mkdir(parents=True)
    (output_dir / "skills.tex").write_text("\\item Python", encoding="utf-8")

    service = CVPdfService(pdf_settings)
    with pytest.raises(FileNotFoundError, match="CV project"):
        service.generate_tailored_pdf("proj-1", "job-1")


def test_fallback_pdf_uses_summary_job_title(pdf_storage_setup):
    from app.services.latex_compile_service import LatexCompileError

    settings, project_id, job_id = pdf_storage_setup
    service = CVPdfService(settings)

    def raise_compile_error(output_dir, master_file):
        raise LatexCompileError("No compiler in test")

    service._compiler.compile_output_to_pdf = raise_compile_error
    pdf_path = service.generate_tailored_pdf(project_id, job_id)
    reader = PdfReader(str(pdf_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Acme Corp" in text or "Senior AI Engineer" in text or "Tailored" in text
