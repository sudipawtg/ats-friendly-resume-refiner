import io
import zipfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
RESUME_LATEX_DIR = REPO_ROOT / "Resume_latex"

SAMPLE_JOB_DESCRIPTION = """
Senior AI Engineer at Acme Corp, London, UK (Hybrid).
We are seeking a Senior AI Engineer with strong Python, machine learning, and LLM experience.
Responsibilities include building RAG pipelines, fine-tuning models, deploying on AWS,
collaborating with product teams, and mentoring junior engineers.
Required skills: Python, PyTorch, LangChain, AWS, FastAPI, OpenAI API, 5+ years experience.
Preferred: Kubernetes, MLOps, insurance domain knowledge, stakeholder engagement.
Benefits include competitive salary, pension, and flexible working arrangements.
"""


def make_sample_cv_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "Resume/resume.tex",
            "\\documentclass{article}\n\\input{_header.tex}\n\\begin{document}\n\\end{document}",
        )
        archive.writestr("Resume/_header.tex", "% header")
        archive.writestr("Resume/TLCresume.sty", "% style")
        archive.writestr("Resume/sections/objective.tex", "\\item Seeking AI engineering roles")
        archive.writestr("Resume/sections/skills.tex", "\\item Python, AWS, LLM, RAG")
        archive.writestr(
            "Resume/sections/experience.tex",
            "\\item Built enterprise AI systems with Python and Azure OpenAI",
        )
        archive.writestr("Resume/sections/education.tex", "\\item MSc Computer Science")
        archive.writestr("Resume/sections/activities.tex", "\\item Open source contributor")
    return buffer.getvalue()


def make_sample_pdf() -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0,
        6,
        "Jane Doe\nSenior Engineer\njane@example.com\n\nSkills:\nPython, AWS\n\nExperience:\nBuilt APIs at Acme Corp",
    )
    return bytes(pdf.output())


def make_resume_latex_zip() -> bytes:
    if not RESUME_LATEX_DIR.is_dir():
        raise FileNotFoundError(f"Resume_latex folder not found at {RESUME_LATEX_DIR}")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in RESUME_LATEX_DIR.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(RESUME_LATEX_DIR).as_posix())
    return buffer.getvalue()


@pytest.fixture
def sample_cv_zip() -> bytes:
    return make_sample_cv_zip()


@pytest.fixture
def sample_pdf() -> bytes:
    return make_sample_pdf()


@pytest.fixture
def test_settings(tmp_path, monkeypatch) -> Settings:
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    settings = get_settings()
    yield settings
    get_settings.cache_clear()


@pytest.fixture
async def api_client(test_settings: Settings) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
