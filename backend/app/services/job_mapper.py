import logging
from typing import Any

from app.constants import JobStatus
from app.db.models import TailoringJob
from app.models.schemas import (
    ATSAnalysis,
    AnalyzeResponse,
    FitAnalysis,
    JobDescriptionExtract,
    SectionChange,
    TailorPreviewResponse,
    TailorResponse,
)

logger = logging.getLogger(__name__)


def tailoring_job_to_analyze_response(record: TailoringJob) -> AnalyzeResponse:
    fit_data = record.fit_analysis or {}
    ats_data = record.ats_analysis or {}
    job_description_data = record.job_description or {}
    return AnalyzeResponse(
        job_id=record.id,
        fit_analysis=FitAnalysis(**fit_data) if fit_data else FitAnalysis(overall_fit=0),
        ats_analysis=ATSAnalysis(**ats_data) if ats_data else ATSAnalysis(overall_score=0),
        job_description=JobDescriptionExtract(**job_description_data)
        if job_description_data
        else JobDescriptionExtract(raw_text=""),
        refined_instructions=record.refined_instructions,
        status=JobStatus(record.status),
    )


def tailoring_job_to_preview_response(record: TailoringJob) -> TailorPreviewResponse:
    fit_data = record.fit_analysis or {}
    ats_data = record.ats_analysis or {}
    changes = [
        SectionChange(
            id=change.id,
            section_path=change.section_path,
            original_text=change.original_text,
            proposed_text=change.proposed_text,
            reason=change.reason,
            job_requirement=change.job_requirement,
            evidence_used=change.evidence_used,
            status=change.status,
        )
        for change in record.changes
    ]
    return TailorPreviewResponse(
        job_id=record.id,
        fit_analysis=FitAnalysis(**fit_data) if fit_data else FitAnalysis(overall_fit=0),
        ats_analysis=ATSAnalysis(**ats_data) if ats_data else ATSAnalysis(overall_score=0),
        changes=changes,
        refined_instructions=record.refined_instructions,
        status=JobStatus(record.status),
    )


def job_record_to_result(record: TailoringJob) -> dict[str, Any]:
    if record.job_type == "analyze":
        return tailoring_job_to_analyze_response(record).model_dump()
    if record.job_type == "preview":
        return tailoring_job_to_preview_response(record).model_dump()
    return tailoring_job_to_tailor_response(record).model_dump()


def tailoring_job_to_tailor_response(record: TailoringJob) -> TailorResponse:
    fit_data = record.fit_analysis or {}
    ats_data = record.ats_analysis or {}
    changes = [
        SectionChange(
            id=change.id,
            section_path=change.section_path,
            original_text=change.original_text,
            proposed_text=change.proposed_text,
            reason=change.reason,
            job_requirement=change.job_requirement,
            evidence_used=change.evidence_used,
            status=change.status,
        )
        for change in record.changes
    ]
    return TailorResponse(
        job_id=record.id,
        fit_analysis=FitAnalysis(**fit_data) if fit_data else FitAnalysis(overall_fit=0),
        ats_analysis=ATSAnalysis(**ats_data) if ats_data else ATSAnalysis(overall_score=0),
        changes=changes,
        refined_instructions=record.refined_instructions,
        status=JobStatus(record.status),
    )


def job_record_to_dict(record: TailoringJob) -> dict[str, Any]:
    return {
        "id": record.id,
        "cv_project_id": record.cv_project_id,
        "job_type": record.job_type,
        "status": record.status,
        "url": record.url,
        "job_description": record.job_description,
        "fit_analysis": record.fit_analysis,
        "ats_analysis": record.ats_analysis,
        "changes": [
            {
                "id": change.id,
                "section_path": change.section_path,
                "original_text": change.original_text,
                "proposed_text": change.proposed_text,
                "reason": change.reason,
                "job_requirement": change.job_requirement,
                "evidence_used": change.evidence_used,
                "status": change.status,
            }
            for change in record.changes
        ],
        "refined_instructions": record.refined_instructions,
        "error_message": record.error_message,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
