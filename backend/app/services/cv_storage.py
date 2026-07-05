import json
import logging
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.constants import DEFAULT_SECTIONS, LOCKED_CV_FILES
from app.services.cv_template_service import CVTemplateService
from app.services.tenant_storage_paths import ensure_tenant_storage_layout, resolve_tenant_storage_root

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_ID = "classic_blue"


class CVStorageService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._tenant_id = tenant_id
        self._tenant_root = resolve_tenant_storage_root(settings, tenant_id)
        ensure_tenant_storage_layout(self._tenant_root)
        self._registry_path = self._tenant_root / "cvs" / "registry.json"
        self._profiles_path = self._tenant_root / "instruction_profiles.json"

    @property
    def tenant_id(self) -> str | None:
        return self._tenant_id

    @property
    def tenant_root(self) -> Path:
        return self._tenant_root

    def _load_registry(self) -> dict[str, dict]:
        if not self._registry_path.exists():
            return {}
        return json.loads(self._registry_path.read_text(encoding="utf-8"))

    def _save_registry(self, registry: dict[str, dict]) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry_path.write_text(json.dumps(registry, indent=2, default=str), encoding="utf-8")

    def _project_dir(self, project_id: str) -> Path:
        return self._tenant_root / "cvs" / project_id

    def output_dir_path(self, project_id: str, job_id: str) -> Path:
        return self._tenant_root / "outputs" / project_id / job_id

    def get_output_dir(self, project_id: str, job_id: str) -> Path:
        return self.output_dir_path(project_id, job_id)

    def _output_dir(self, project_id: str, job_id: str) -> Path:
        path = self.output_dir_path(project_id, job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_projects(self) -> list[dict]:
        return list(self._load_registry().values())

    def get_project(self, project_id: str) -> dict | None:
        return self._load_registry().get(project_id)

    def save_upload(self, name: str, zip_bytes: bytes, project_id: str | None = None) -> dict:
        resolved_project_id = project_id or str(uuid.uuid4())
        project_dir = self._project_dir(resolved_project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        zip_path = project_dir / "master.zip"
        zip_path.write_bytes(zip_bytes)

        extract_dir = project_dir / "master"
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)

        project_root, master_tex_rel = self._resolve_project_layout(extract_dir)
        sections = self._discover_sections(project_root)

        entry = {
            "id": resolved_project_id,
            "name": name,
            "master_file": master_tex_rel.as_posix(),
            "master_root": project_root.relative_to(project_dir).as_posix(),
            "sections": sections,
            "locked_files": sorted(LOCKED_CV_FILES),
            "source_type": "zip",
            "template_id": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        if self._tenant_id:
            entry["tenant_id"] = self._tenant_id
        registry = self._load_registry()
        registry[resolved_project_id] = entry
        self._save_registry(registry)
        logger.info(
            "Saved CV project %s with %d sections (tenant=%s)",
            resolved_project_id,
            len(sections),
            self._tenant_id or "legacy",
        )
        return entry

    def save_from_template(
        self,
        name: str,
        template_id: str,
        sections_content: dict[str, str] | None = None,
        contact: dict[str, str] | None = None,
        project_id: str | None = None,
    ) -> dict:
        resolved_project_id = project_id or str(uuid.uuid4())
        project_dir = self._project_dir(resolved_project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        master_root = project_dir / "master"
        CVTemplateService().materialize_project(
            master_root,
            template_id,
            sections_content=sections_content,
            contact=contact,
        )

        sections = self._discover_sections(master_root)
        entry = {
            "id": resolved_project_id,
            "name": name,
            "master_file": "resume.tex",
            "master_root": "master",
            "sections": sections,
            "locked_files": sorted(LOCKED_CV_FILES),
            "source_type": "template",
            "template_id": template_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        if self._tenant_id:
            entry["tenant_id"] = self._tenant_id
        registry = self._load_registry()
        registry[resolved_project_id] = entry
        self._save_registry(registry)
        logger.info(
            "Created CV project %s from template %s (tenant=%s)",
            resolved_project_id,
            template_id,
            self._tenant_id or "legacy",
        )
        return entry

    def save_pdf_upload(
        self,
        name: str,
        pdf_bytes: bytes,
        sections_content: dict[str, str],
        contact: dict[str, str] | None = None,
        template_id: str = DEFAULT_TEMPLATE_ID,
        project_id: str | None = None,
    ) -> dict:
        resolved_project_id = project_id or str(uuid.uuid4())
        project_dir = self._project_dir(resolved_project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "source.pdf").write_bytes(pdf_bytes)

        master_root = project_dir / "master"
        CVTemplateService().materialize_project(
            master_root,
            template_id,
            sections_content=sections_content,
            contact=contact,
        )

        sections = self._discover_sections(master_root)
        entry = {
            "id": resolved_project_id,
            "name": name,
            "master_file": "resume.tex",
            "master_root": "master",
            "sections": sections,
            "locked_files": sorted(LOCKED_CV_FILES),
            "source_type": "pdf",
            "template_id": template_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        if self._tenant_id:
            entry["tenant_id"] = self._tenant_id
        registry = self._load_registry()
        registry[resolved_project_id] = entry
        self._save_registry(registry)
        logger.info(
            "Imported CV project %s from PDF with template %s (tenant=%s)",
            resolved_project_id,
            template_id,
            self._tenant_id or "legacy",
        )
        return entry

    def apply_template(self, project_id: str, template_id: str) -> dict:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        master_root = self.get_master_root(project_id)
        CVTemplateService().apply_template_layout(master_root, template_id)
        sections = self._discover_sections(master_root)

        project["template_id"] = template_id
        project["sections"] = sections
        registry = self._load_registry()
        registry[project_id] = project
        self._save_registry(registry)
        return project

    def read_section(self, project_id: str, section_path: str) -> str:
        path = self._resolve_path(project_id, section_path)
        if not path.exists():
            raise FileNotFoundError(f"Section not found: {section_path}")
        return path.read_text(encoding="utf-8")

    def write_section(self, project_id: str, section_path: str, content: str) -> Path:
        path = self._resolve_path(project_id, section_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read_all_sections(self, project_id: str) -> dict[str, str]:
        project = self.get_project(project_id)
        if not project:
            return {}
        sections: dict[str, str] = {}
        for section_path in project["sections"]:
            try:
                sections[section_path] = self.read_section(project_id, section_path)
            except FileNotFoundError:
                logger.warning("Missing section %s for project %s", section_path, project_id)
        return sections

    def read_output_section(self, project_id: str, job_id: str, section_path: str) -> str:
        output_dir = self._output_dir(project_id, job_id)
        target = (output_dir / section_path).resolve()
        if not str(target).startswith(str(output_dir.resolve())):
            raise ValueError("Invalid section path")
        if not target.exists():
            raise FileNotFoundError(f"Section not found: {section_path}")
        return target.read_text(encoding="utf-8")

    def write_output_section(
        self, project_id: str, job_id: str, section_path: str, content: str
    ) -> Path:
        output_dir = self._output_dir(project_id, job_id)
        target = output_dir / section_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def copy_master_to_output(self, project_id: str, job_id: str) -> Path:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        master_root = self._project_dir(project_id) / project["master_root"]
        output_dir = self._output_dir(project_id, job_id)
        self._copy_tree(master_root, output_dir)
        return output_dir

    def create_output_zip(self, project_id: str, job_id: str, folder_name: str) -> Path:
        output_dir = self._output_dir(project_id, job_id)
        zip_path = output_dir.parent / f"{folder_name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(output_dir))
        return zip_path

    def save_tailoring_summary(self, project_id: str, job_id: str, summary: dict) -> Path:
        output_dir = self._output_dir(project_id, job_id)
        summary_path = output_dir / "tailoring_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        return summary_path

    def load_tailoring_summary(self, project_id: str, job_id: str) -> dict | None:
        summary_path = self._output_dir(project_id, job_id) / "tailoring_summary.json"
        if not summary_path.exists():
            return None
        return json.loads(summary_path.read_text(encoding="utf-8"))

    def get_master_root(self, project_id: str) -> Path:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        return self._project_dir(project_id) / project["master_root"]

    def load_instruction_profiles(self) -> list[dict]:
        if not self._profiles_path.exists():
            return []
        return json.loads(self._profiles_path.read_text(encoding="utf-8"))

    def save_instruction_profile(self, profile: dict) -> dict:
        profiles = self.load_instruction_profiles()
        existing_index = next((i for i, profile_entry in enumerate(profiles) if profile_entry["id"] == profile["id"]), None)
        if existing_index is not None:
            profiles[existing_index] = profile
        else:
            profiles.append(profile)
        self._profiles_path.write_text(json.dumps(profiles, indent=2, default=str), encoding="utf-8")
        return profile

    def delete_instruction_profile(self, profile_id: str) -> bool:
        profiles = self.load_instruction_profiles()
        filtered = [profile_entry for profile_entry in profiles if profile_entry["id"] != profile_id]
        if len(filtered) == len(profiles):
            return False
        self._profiles_path.write_text(json.dumps(filtered, indent=2, default=str), encoding="utf-8")
        return True

    def _resolve_path(self, project_id: str, relative_path: str) -> Path:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        master_root = self._project_dir(project_id) / project["master_root"]
        resolved = (master_root / relative_path).resolve()
        if not str(resolved).startswith(str(master_root.resolve())):
            raise ValueError("Invalid section path")
        return resolved

    def _resolve_project_layout(self, extract_dir: Path) -> tuple[Path, Path]:
        resume_candidates = sorted(extract_dir.rglob("resume.tex"))
        if not resume_candidates:
            return extract_dir, Path("resume.tex")

        for resume_path in resume_candidates:
            resume_dir = resume_path.parent
            if self._is_latex_project_root(resume_dir):
                return resume_dir, Path(resume_path.name)

            parent_dir = resume_dir.parent
            if self._is_latex_project_root(parent_dir):
                return parent_dir, resume_path.relative_to(parent_dir)

        first_resume = resume_candidates[0]
        return first_resume.parent, Path(first_resume.name)

    def _is_latex_project_root(self, path: Path) -> bool:
        sections_dir = path / "sections"
        has_sections = sections_dir.is_dir() and any(sections_dir.glob("*.tex"))
        has_support_file = (path / "TLCresume.sty").exists() or (path / "_header.tex").exists()
        return has_sections and has_support_file

    def _discover_sections(self, master_root: Path) -> list[str]:
        sections_dir = master_root / "sections"
        discovered: list[str] = []
        if sections_dir.exists():
            for tex_file in sorted(sections_dir.glob("*.tex")):
                discovered.append(str(tex_file.relative_to(master_root)))
        if not discovered:
            discovered = [section for section in DEFAULT_SECTIONS if (master_root / section).exists()]
        return discovered

    def _copy_tree(self, source: Path, destination: Path) -> None:
        import shutil

        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
