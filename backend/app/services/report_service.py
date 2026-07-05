from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import Settings
from app.services.tailoring_service import TailoringService
from app.services.tenant_storage_paths import resolve_tenant_storage_root

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class ReportService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._tenant_id = tenant_id
        self._tenant_root = resolve_tenant_storage_root(settings, tenant_id)
        self._tailoring = TailoringService(settings, tenant_id=tenant_id)
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate_html_report(
        self,
        job_id: str | None = None,
        batch_id: str | None = None,
        include_ats: bool = True,
        include_fit: bool = True,
        include_changes: bool = True,
        include_gaps: bool = True,
    ) -> Path:
        template = self._env.get_template("report.html")
        context = self._build_context(job_id, batch_id, include_ats, include_fit, include_changes, include_gaps)
        html = template.render(**context)

        report_name = f"report_{job_id or batch_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        reports_dir = self._tenant_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / report_name
        report_path.write_text(html, encoding="utf-8")
        return report_path

    def _build_context(
        self,
        job_id: str | None,
        batch_id: str | None,
        include_ats: bool,
        include_fit: bool,
        include_changes: bool,
        include_gaps: bool,
    ) -> dict:
        generated_at = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
        context: dict = {
            "title": "ResumeForge Analysis Report",
            "generated_at": generated_at,
            "include_ats": include_ats,
            "include_fit": include_fit,
            "include_changes": include_changes,
            "include_gaps": include_gaps,
            "jobs": [],
        }

        if job_id:
            job = self._tailoring.get_job(job_id)
            if job:
                context["jobs"] = [job]
                context["title"] = f"ResumeForge Report — Job {job_id[:8]}"
        elif batch_id:
            batch = self._tailoring.get_batch(batch_id)
            if batch:
                context["batch"] = batch
                context["title"] = f"ResumeForge Batch Report — {batch.get('name', batch_id)}"
                job_records = []
                for entry in batch.get("jobs", []):
                    full_job = self._tailoring.get_job(entry["id"])
                    if full_job:
                        job_records.append(full_job)
                    else:
                        merged = {**entry}
                        if entry.get("job_description") and isinstance(entry["job_description"], dict):
                            merged["job_description"] = entry["job_description"]
                        summary_path = (
                            self._tenant_root
                            / "outputs"
                            / batch["cv_project_id"]
                            / entry["id"]
                            / "tailoring_summary.json"
                        )
                        if summary_path.exists():
                            import json

                            summary = json.loads(summary_path.read_text(encoding="utf-8"))
                            merged.update(summary)
                        job_records.append(merged)
                context["jobs"] = job_records

        return context
