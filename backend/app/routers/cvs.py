import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import INSTRUCTION_PROFILES
from app.core.tenant import TenantContext, get_tenant_context
from app.db.models import CvProject
from app.db.repositories import CvProjectRepository
from app.db.session import get_db_session
from app.models.schemas import ApplyTemplateRequest, CreateFromTemplateRequest, CVCoachReviewRequest, CVCoachReviewResponse, CoachChatRequest, CoachChatResponse, CVProjectResponse, MasterSectionRefineRequest, MasterSectionRefineResponse, SectionContentUpdateRequest, SectionRestoreRequest, SectionVersionSummary
from app.services.cv_storage import CVStorageService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cvs", tags=["CV Projects"])


def _cv_project_to_response(record: CvProject) -> CVProjectResponse:
    return CVProjectResponse(
        id=record.id,
        name=record.name,
        master_file=record.master_file,
        sections=list(record.sections or []),
        locked_files=list(record.locked_files or []),
        source_type=getattr(record, "source_type", None) or "zip",
        template_id=getattr(record, "template_id", None),
        created_at=record.created_at.isoformat() if record.created_at else datetime.utcnow().isoformat(),
    )


def _registry_entry_to_response(entry: dict) -> CVProjectResponse:
    return CVProjectResponse(
        id=entry["id"],
        name=entry["name"],
        master_file=entry["master_file"],
        sections=list(entry.get("sections") or []),
        locked_files=list(entry.get("locked_files") or []),
        source_type=entry.get("source_type") or "zip",
        template_id=entry.get("template_id"),
        created_at=entry.get("created_at") or datetime.utcnow().isoformat(),
    )


async def _sync_project_to_database(
    session: AsyncSession | None,
    tenant_id: str,
    project_entry: dict,
) -> None:
    if session is None:
        return
    repository = CvProjectRepository(session)
    existing = await repository.get_project_for_tenant(tenant_id, project_entry["id"])
    if existing is not None:
        return
    await repository.create_project(
        tenant_id=tenant_id,
        project_id=project_entry["id"],
        name=project_entry["name"],
        master_file=project_entry["master_file"],
        master_root=project_entry.get("master_root", "master"),
        sections=list(project_entry.get("sections") or []),
        locked_files=list(project_entry.get("locked_files") or []),
    )


@router.get("", response_model=list[CVProjectResponse])
async def list_cv_projects(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> list[CVProjectResponse]:
    settings = get_settings()
    if settings.database_enabled and session is not None:
        repository = CvProjectRepository(session)
        records = await repository.list_projects_for_tenant(tenant.tenant_id)
        return [_cv_project_to_response(record) for record in records]

    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    return [_registry_entry_to_response(entry) for entry in storage.list_projects()]


@router.get("/{project_id}", response_model=CVProjectResponse)
async def get_cv_project(
    project_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> CVProjectResponse:
    settings = get_settings()
    if settings.database_enabled and session is not None:
        repository = CvProjectRepository(session)
        record = await repository.get_project_for_tenant(tenant.tenant_id, project_id)
        if record is None:
            raise HTTPException(status_code=404, detail="CV project not found")
        return _cv_project_to_response(record)

    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CV project not found")
    return _registry_entry_to_response(project)


@router.post("/upload", response_model=CVProjectResponse)
async def upload_cv(
    file: UploadFile = File(...),
    name: str = Form("Master CV"),
    template_id: str = Form("classic_blue"),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> CVProjectResponse:
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Upload must include a filename")

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_size_mb}MB limit")

    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    filename_lower = file.filename.lower()

    try:
        if filename_lower.endswith(".zip"):
            project = storage.save_upload(name, content)
        elif filename_lower.endswith(".pdf"):
            from app.services.llm_service import LLMService
            from app.services.pdf_import_service import PDFImportService

            pdf_service = PDFImportService()
            extracted_text, extraction_method = pdf_service.extract_text(content)
            if len(extracted_text.strip()) < 50:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract enough text from the PDF. Try a text-based PDF, a clearer scan, or upload a LaTeX ZIP.",
                )

            heuristic_parse = pdf_service.parse_with_heuristics(extracted_text, extraction_method)
            llm_service = LLMService(settings)
            llm_parse = await llm_service.parse_cv_from_text(extracted_text)
            merged_contact = {**heuristic_parse.contact, **llm_parse.get("contact", {})}
            merged_sections = {**heuristic_parse.sections, **llm_parse.get("sections", {})}

            from app.cv_templates.registry import get_template_definition

            if get_template_definition(template_id) is None:
                raise HTTPException(status_code=400, detail=f"Unknown template: {template_id}")

            project = storage.save_pdf_upload(
                name,
                content,
                sections_content=merged_sections,
                contact=merged_contact,
                template_id=template_id,
            )
        else:
            raise HTTPException(status_code=400, detail="Upload must be a .zip or .pdf file")

        await _sync_project_to_database(session, tenant.tenant_id, project)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("CV upload failed")
        raise HTTPException(status_code=400, detail="Could not process CV file") from error

    return _registry_entry_to_response(project)


@router.post("/from-template", response_model=CVProjectResponse)
async def create_cv_from_template(
    payload: CreateFromTemplateRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> CVProjectResponse:
    from app.cv_templates.registry import get_template_definition

    if get_template_definition(payload.template_id) is None:
        raise HTTPException(status_code=400, detail=f"Unknown template: {payload.template_id}")

    settings = get_settings()
    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    try:
        project = storage.save_from_template(payload.name, payload.template_id)
        await _sync_project_to_database(session, tenant.tenant_id, project)
    except Exception as error:
        logger.exception("Template CV creation failed")
        raise HTTPException(status_code=400, detail="Could not create CV from template") from error

    return _registry_entry_to_response(project)


@router.post("/{project_id}/apply-template", response_model=CVProjectResponse)
async def apply_cv_template(
    project_id: str,
    payload: ApplyTemplateRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> CVProjectResponse:
    from app.cv_templates.registry import get_template_definition

    if get_template_definition(payload.template_id) is None:
        raise HTTPException(status_code=400, detail=f"Unknown template: {payload.template_id}")

    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)
    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    try:
        project = storage.apply_template(project_id, payload.template_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Apply template failed for project %s", project_id)
        raise HTTPException(status_code=400, detail="Could not apply template") from error

    return _registry_entry_to_response(project)


@router.get("/{project_id}/master-pdf")
async def download_master_pdf(
    project_id: str,
    download: bool = Query(default=False),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> FileResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)
    from app.services.pdf_service import CVPdfService

    try:
        pdf_path = CVPdfService(settings, tenant_id=tenant.tenant_id).generate_master_pdf(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Master PDF generation failed for project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not generate master CV PDF") from error

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"master_cv_{project_id[:8]}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/{project_id}/master-sections")
async def get_master_sections(
    project_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict[str, list[dict[str, str]]]:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)
    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    section_map = storage.read_all_sections(project_id)
    if not section_map:
        raise HTTPException(status_code=404, detail="CV project not found or has no sections")
    sections = [
        {"section_path": section_path, "content": content}
        for section_path, content in section_map.items()
    ]
    return {"sections": sections}


@router.put("/{project_id}/sections/{section_path:path}")
async def save_section_content(
    project_id: str,
    section_path: str,
    request: SectionContentUpdateRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict[str, str]:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.cv_section_service import CVSectionService

    try:
        return CVSectionService(settings, tenant_id=tenant.tenant_id).save_section_content(
            project_id, section_path, request
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Manual section save failed for project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not save section") from error


@router.get("/{project_id}/sections/{section_path:path}/history", response_model=list[SectionVersionSummary])
async def list_section_history(
    project_id: str,
    section_path: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> list[SectionVersionSummary]:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.cv_section_service import CVSectionService

    try:
        return CVSectionService(settings, tenant_id=tenant.tenant_id).list_section_history(
            project_id, section_path
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/{project_id}/sections/{section_path:path}/restore", response_model=dict[str, str])
async def restore_section_version(
    project_id: str,
    section_path: str,
    request: SectionRestoreRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict[str, str]:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.cv_section_service import CVSectionService

    try:
        return CVSectionService(settings, tenant_id=tenant.tenant_id).restore_section_version(
            project_id, section_path, request.version_id
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Section restore failed for project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not restore section version") from error


@router.get("/{project_id}/sections/{section_path:path}")
async def get_section(
    project_id: str,
    section_path: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict[str, str]:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)
    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    try:
        content = storage.read_section(project_id, section_path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"section_path": section_path, "content": content}


@router.post("/{project_id}/sections/refine", response_model=MasterSectionRefineResponse)
async def refine_master_section(
    project_id: str,
    request: MasterSectionRefineRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> MasterSectionRefineResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.cv_edit_service import CVEditService

    try:
        return await CVEditService(settings, tenant_id=tenant.tenant_id).refine_master_section(
            project_id, request
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Master section refine failed for project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not refine section") from error


@router.post("/{project_id}/coach/review", response_model=CVCoachReviewResponse)
async def review_cv_with_coach(
    project_id: str,
    request: CVCoachReviewRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> CVCoachReviewResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.cv_coach_service import CVCoachService

    try:
        return await CVCoachService(settings, tenant_id=tenant.tenant_id).review_cv(
            project_id, request
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("CV coach review failed for project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not review CV") from error


@router.post("/{project_id}/coach/chat", response_model=CoachChatResponse)
async def coach_chat(
    project_id: str,
    request: CoachChatRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> CoachChatResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.cv_coach_service import CVCoachService

    try:
        return await CVCoachService(settings, tenant_id=tenant.tenant_id).chat(project_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("CV coach chat failed for project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not process coach message") from error


@router.get("/{project_id}/outputs/{job_id}/sections/{section_path:path}")
async def get_output_section(
    project_id: str,
    job_id: str,
    section_path: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> dict[str, str]:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)
    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    try:
        content = storage.read_output_section(project_id, job_id, section_path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"section_path": section_path, "content": content}


@router.get("/{project_id}/download/{job_id}/docx")
async def download_output_docx(
    project_id: str,
    job_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> FileResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.docx_service import CVDocxService

    try:
        docx_path = CVDocxService(settings, tenant_id=tenant.tenant_id).generate_tailored_docx(
            project_id, job_id
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("DOCX generation failed")
        raise HTTPException(status_code=500, detail="Could not generate DOCX") from error

    return FileResponse(
        path=str(docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=docx_path.name,
    )


@router.get("/{project_id}/master-docx")
async def download_master_docx(
    project_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> FileResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.docx_service import CVDocxService

    try:
        docx_path = CVDocxService(settings, tenant_id=tenant.tenant_id).generate_master_docx(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Master DOCX generation failed for project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not generate master CV DOCX") from error

    return FileResponse(
        path=str(docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=docx_path.name,
    )


@router.get("/{project_id}/download/{job_id}/pdf")
async def download_output_pdf(
    project_id: str,
    job_id: str,
    download: bool = Query(default=False),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> FileResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)

    from app.services.pdf_service import CVPdfService

    try:
        pdf_path = CVPdfService(settings, tenant_id=tenant.tenant_id).generate_tailored_pdf(
            project_id, job_id
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail="Could not generate PDF") from error

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/{project_id}/download/{job_id}")
async def download_output_zip(
    project_id: str,
    job_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession | None = Depends(get_db_session),
) -> FileResponse:
    settings = get_settings()
    await _ensure_project_access(settings, session, tenant.tenant_id, project_id)
    storage = CVStorageService(settings, tenant_id=tenant.tenant_id)
    output_dir = storage.get_output_dir(project_id, job_id)
    if not output_dir.exists() or not any(output_dir.iterdir()):
        raise HTTPException(status_code=404, detail="Output not found")

    zip_path = storage.create_output_zip(project_id, job_id, f"tailored_{job_id[:8]}")
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=zip_path.name,
    )


async def _ensure_project_access(
    settings,
    session: AsyncSession | None,
    tenant_id: str,
    project_id: str,
) -> None:
    if settings.database_enabled and session is not None:
        repository = CvProjectRepository(session)
        record = await repository.get_project_for_tenant(tenant_id, project_id)
        if record is None:
            raise HTTPException(status_code=404, detail="CV project not found")
        return

    storage = CVStorageService(settings, tenant_id=tenant_id)
    if storage.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="CV project not found")
