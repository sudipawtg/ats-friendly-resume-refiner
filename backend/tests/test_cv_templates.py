import io
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient

from app.cv_templates.registry import CV_TEMPLATE_REGISTRY, get_template_definition
from app.main import app
from app.services.cv_template_service import CVTemplateService
from app.services.docx_service import CVDocxService
from app.services.pdf_import_service import PDFImportService
from tests.conftest import make_sample_cv_zip


@pytest.fixture
async def client(test_settings):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api") as ac:
        yield ac


class TestCVTemplateRegistry:
    def test_has_eight_templates(self):
        assert len(CV_TEMPLATE_REGISTRY) == 8

    def test_all_templates_have_unique_ids(self):
        template_ids = [template.id for template in CV_TEMPLATE_REGISTRY]
        assert len(template_ids) == len(set(template_ids))

    def test_get_template_definition(self):
        template = get_template_definition("classic_blue")
        assert template is not None
        assert template.name == "Classic Blue"


class TestCVTemplateService:
    def test_materialize_project_creates_latex_files(self, tmp_path):
        destination = tmp_path / "master"
        template = CVTemplateService().materialize_project(destination, "modern_teal")
        assert template.id == "modern_teal"
        assert (destination / "resume.tex").exists()
        assert (destination / "TLCresume.sty").exists()
        assert (destination / "sections" / "skills.tex").exists()


class TestPDFImportService:
    def test_parse_with_heuristics_extracts_email(self):
        text = "Jane Doe\nSenior Engineer\njane@example.com\n\nSkills:\nPython\n\nExperience:\nBuilt APIs"
        parsed = PDFImportService().parse_with_heuristics(text)
        assert parsed.contact.get("email") == "jane@example.com"
        assert "sections/skills.tex" in parsed.sections
        assert "sections/experience.tex" in parsed.sections


class TestCVTemplateEndpoints:
    @pytest.mark.asyncio
    async def test_list_templates(self, client):
        response = await client.get("/cv-templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 8
        assert data[0]["id"]
        assert data[0]["preview_url"].endswith("/preview.svg")

    @pytest.mark.asyncio
    async def test_template_preview_svg(self, client):
        response = await client.get("/cv-templates/classic_blue/preview.svg")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert "<svg" in response.text

    @pytest.mark.asyncio
    async def test_create_from_template(self, client):
        response = await client.post(
            "/cvs/from-template",
            json={"name": "Starter CV", "template_id": "classic_blue"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Starter CV"
        assert data["template_id"] == "classic_blue"
        assert data["source_type"] == "template"
        assert len(data["sections"]) >= 1

    @pytest.mark.asyncio
    async def test_apply_template(self, client, sample_cv_zip):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project_id = upload.json()["id"]
        response = await client.post(
            f"/cvs/{project_id}/apply-template",
            json={"template_id": "creative_purple"},
        )
        assert response.status_code == 200
        assert response.json()["template_id"] == "creative_purple"

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_format(self, client):
        files = {"file": ("cv.txt", io.BytesIO(b"hello"), "text/plain")}
        response = await client.post("/cvs/upload", files=files)
        assert response.status_code == 400
        assert "zip" in response.json()["detail"].lower()


class TestDocxExport:
    @pytest.mark.asyncio
    async def test_master_docx_export(self, client, sample_cv_zip, test_settings):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project_id = upload.json()["id"]
        response = await client.get(f"/cvs/{project_id}/master-docx")
        assert response.status_code == 200
        assert "wordprocessingml" in response.headers["content-type"]

    def test_docx_service_builds_file(self, test_settings, sample_cv_zip, tmp_path):
        from app.services.cv_storage import CVStorageService

        storage = CVStorageService(test_settings)
        project = storage.save_upload("Docx Test", sample_cv_zip)
        docx_path = CVDocxService(test_settings).generate_master_docx(project["id"])
        assert docx_path.exists()
        assert docx_path.suffix == ".docx"


class TestMasterSectionRefine:
    @pytest.mark.asyncio
    async def test_refine_master_section(self, client, sample_cv_zip, monkeypatch):
        upload = await client.post(
            "/cvs/upload",
            files={"file": ("cv.zip", io.BytesIO(sample_cv_zip), "application/zip")},
        )
        project = upload.json()
        section_path = project["sections"][0]

        async def mock_refine_master_section(
            self,
            section_path: str,
            original: str,
            instruction: str,
            global_instruction: str = "",
        ):
            return {
                "content": f"{original}\\n\\item Refined content",
                "reason": "Improved clarity",
            }

        monkeypatch.setattr(
            "app.services.llm_service.LLMService.refine_master_section",
            mock_refine_master_section,
        )

        response = await client.post(
            f"/cvs/{project['id']}/sections/refine",
            json={"section_path": section_path, "instruction": "Make it clearer"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["section_path"] == section_path
        assert "Refined content" in data["content"]

        section_response = await client.get(f"/cvs/{project['id']}/sections/{section_path}")
        assert "Refined content" in section_response.json()["content"]
