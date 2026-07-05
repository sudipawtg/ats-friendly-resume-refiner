from dataclasses import dataclass
from typing import Literal


SectionStyle = Literal["scrule", "bold_rule", "minimal"]
HeaderLayout = Literal["center", "left"]


@dataclass(frozen=True)
class CVTemplateDefinition:
    id: str
    name: str
    description: str
    preview_color: str
    category: str
    highlight_rgb: tuple[int, int, int]
    section_style: SectionStyle
    header_layout: HeaderLayout
    section_order: tuple[str, ...]


DEFAULT_SECTION_ORDER: tuple[str, ...] = (
    "Skills",
    "Experience",
    "Education",
    "Activities",
)

CV_TEMPLATE_REGISTRY: tuple[CVTemplateDefinition, ...] = (
    CVTemplateDefinition(
        id="classic_blue",
        name="Classic Blue",
        description="Professional layout with blue accents and centered header.",
        preview_color="#3D5A80",
        category="Professional",
        highlight_rgb=(61, 90, 128),
        section_style="scrule",
        header_layout="center",
        section_order=DEFAULT_SECTION_ORDER,
    ),
    CVTemplateDefinition(
        id="modern_teal",
        name="Modern Teal",
        description="Fresh teal highlights suited to tech and product roles.",
        preview_color="#14B8A6",
        category="Modern",
        highlight_rgb=(20, 184, 166),
        section_style="bold_rule",
        header_layout="center",
        section_order=DEFAULT_SECTION_ORDER,
    ),
    CVTemplateDefinition(
        id="executive_navy",
        name="Executive Navy",
        description="Left-aligned navy header for senior leadership profiles.",
        preview_color="#1E3A5F",
        category="Executive",
        highlight_rgb=(30, 58, 95),
        section_style="scrule",
        header_layout="left",
        section_order=("Experience", "Skills", "Education", "Activities"),
    ),
    CVTemplateDefinition(
        id="minimal_slate",
        name="Minimal Slate",
        description="Clean grayscale styling with understated section dividers.",
        preview_color="#475569",
        category="Minimal",
        highlight_rgb=(71, 85, 105),
        section_style="minimal",
        header_layout="center",
        section_order=DEFAULT_SECTION_ORDER,
    ),
    CVTemplateDefinition(
        id="creative_purple",
        name="Creative Purple",
        description="Vibrant purple accents for design and creative portfolios.",
        preview_color="#8B5CF6",
        category="Creative",
        highlight_rgb=(139, 92, 246),
        section_style="bold_rule",
        header_layout="center",
        section_order=("Skills", "Experience", "Activities", "Education"),
    ),
    CVTemplateDefinition(
        id="professional_green",
        name="Professional Green",
        description="Green accent theme for consulting and sustainability roles.",
        preview_color="#10B981",
        category="Professional",
        highlight_rgb=(16, 185, 129),
        section_style="scrule",
        header_layout="left",
        section_order=DEFAULT_SECTION_ORDER,
    ),
    CVTemplateDefinition(
        id="bold_coral",
        name="Bold Coral",
        description="High-contrast coral headers that stand out in recruiter inboxes.",
        preview_color="#F43F5E",
        category="Bold",
        highlight_rgb=(244, 63, 94),
        section_style="bold_rule",
        header_layout="center",
        section_order=DEFAULT_SECTION_ORDER,
    ),
    CVTemplateDefinition(
        id="elegant_burgundy",
        name="Elegant Burgundy",
        description="Refined burgundy tones for academic and research CVs.",
        preview_color="#881337",
        category="Academic",
        highlight_rgb=(136, 19, 55),
        section_style="scrule",
        header_layout="left",
        section_order=("Education", "Experience", "Skills", "Activities"),
    ),
)

CV_TEMPLATE_BY_ID: dict[str, CVTemplateDefinition] = {
    template.id: template for template in CV_TEMPLATE_REGISTRY
}


def get_template_definition(template_id: str) -> CVTemplateDefinition | None:
    return CV_TEMPLATE_BY_ID.get(template_id)


def list_template_summaries() -> list[dict[str, str | tuple[str, ...]]]:
    return [
        {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "preview_color": template.preview_color,
            "category": template.category,
            "section_order": template.section_order,
            "preview_url": f"/api/cv-templates/{template.id}/preview.svg",
        }
        for template in CV_TEMPLATE_REGISTRY
    ]
