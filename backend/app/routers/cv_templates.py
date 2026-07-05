from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.cv_templates.registry import get_template_definition, list_template_summaries
from app.models.schemas import CVTemplateSummary
from app.services.template_preview_service import build_template_preview_svg

router = APIRouter(prefix="/cv-templates", tags=["CV Templates"])


@router.get("", response_model=list[CVTemplateSummary])
async def list_cv_templates() -> list[CVTemplateSummary]:
    return [CVTemplateSummary(**template) for template in list_template_summaries()]


@router.get("/{template_id}/preview.svg")
async def get_template_preview(template_id: str) -> Response:
    template = get_template_definition(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    svg_content = build_template_preview_svg(template)
    return Response(content=svg_content, media_type="image/svg+xml")
