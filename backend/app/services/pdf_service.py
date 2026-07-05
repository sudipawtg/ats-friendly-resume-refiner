import logging
import re
from pathlib import Path

from fpdf import FPDF

from app.config import Settings
from app.services.cv_storage import CVStorageService
from app.services.tenant_storage_paths import resolve_tenant_storage_root
from app.services.latex_compile_service import LatexCompileError, LatexCompileService

logger = logging.getLogger(__name__)

SECTION_TITLES: dict[str, str] = {
    "sections/objective.tex": "Objective",
    "sections/skills.tex": "Skills",
    "sections/experience.tex": "Experience",
    "sections/education.tex": "Education",
    "sections/activities.tex": "Activities",
}


def latex_to_plain_text(content: str) -> str:
    text = content.strip()
    text = re.sub(r"\\item\s*", "- ", text)
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}]", "", text)
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2022", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _ascii_safe(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2022", "-")


class CVPdfService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._tenant_id = tenant_id
        self._tenant_root = resolve_tenant_storage_root(settings, tenant_id)
        self._storage = CVStorageService(settings, tenant_id=tenant_id)
        self._compiler = LatexCompileService(settings)

    def generate_tailored_pdf(self, project_id: str, job_id: str) -> Path:
        output_dir = self._storage.get_output_dir(project_id, job_id).resolve()
        if not output_dir.exists():
            raise FileNotFoundError(f"Tailored output not found for job {job_id}")

        project = self._storage.get_project(project_id)
        if not project:
            raise FileNotFoundError(f"CV project {project_id} not found")

        master_file = project.get("master_file", "resume.tex")
        return self._compile_and_cache_pdf(output_dir, master_file, job_id)

    def generate_master_pdf(self, project_id: str) -> Path:
        project = self._storage.get_project(project_id)
        if not project:
            raise FileNotFoundError(f"CV project {project_id} not found")

        master_root = self._storage.get_master_root(project_id).resolve()
        master_file = project.get("master_file", "resume.tex")
        return self._compile_and_cache_pdf(master_root, master_file, f"master_{project_id[:8]}")

    def _compile_and_cache_pdf(self, source_dir: Path, master_file: str, cache_key: str) -> Path:
        try:
            compiled_pdf = self._compiler.compile_output_to_pdf(source_dir, master_file)
            pdf_dir = self._tenant_root / "reports"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            destination = pdf_dir / f"tailored_cv_{cache_key[:12]}.pdf"
            destination.write_bytes(compiled_pdf.read_bytes())
            logger.info("Generated compiled LaTeX PDF at %s", destination)
            return destination
        except LatexCompileError as error:
            logger.warning("LaTeX compile failed, falling back to text PDF: %s", error)
            if "master_" in cache_key:
                raise FileNotFoundError("Could not compile master CV PDF") from error
            return self._generate_text_fallback_pdf(source_dir, cache_key.replace("master_", ""))

    def _generate_text_fallback_pdf(self, output_dir: Path, job_id: str) -> Path:
        summary_path = output_dir / "tailoring_summary.json"
        job_title = "Tailored CV"
        company = ""
        if summary_path.exists():
            import json

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            job_desc = summary.get("job_description") or {}
            raw = job_desc.get("raw_text", "")
            title_match = re.search(r"^([^\n]+)", raw)
            if title_match:
                job_title = title_match.group(1).strip()
            company = job_desc.get("company") or ""

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, _ascii_safe("ResumeForge - Tailored CV (text fallback)"), ln=True)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(80, 80, 80)
        subtitle = _ascii_safe(f"Tailored for: {job_title}")
        if company:
            subtitle += _ascii_safe(f" at {company}")
        pdf.multi_cell(0, 6, subtitle)
        pdf.ln(4)
        pdf.set_text_color(0, 0, 0)

        sections_dir = output_dir / "sections"
        section_files = sorted(sections_dir.glob("*.tex")) if sections_dir.exists() else []
        if not section_files:
            raise FileNotFoundError("No tailored section files found")

        for section_file in section_files:
            relative = f"sections/{section_file.name}"
            heading = SECTION_TITLES.get(relative, section_file.stem.replace("_", " ").title())
            content = latex_to_plain_text(section_file.read_text(encoding="utf-8"))
            if not content:
                continue

            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, _ascii_safe(heading), ln=True)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, _ascii_safe(content))
            pdf.ln(3)

        pdf_dir = self._tenant_root / "reports"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f"tailored_cv_{job_id[:8]}.pdf"
        pdf.output(str(pdf_path))
        return pdf_path
