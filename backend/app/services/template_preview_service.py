from app.cv_templates.registry import CVTemplateDefinition


def build_template_preview_svg(template: CVTemplateDefinition) -> str:
    accent_color = template.preview_color
    is_left_layout = template.header_layout == "left"

    if is_left_layout:
        header_block = f"""
  <text x="20" y="26" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#0f172a">Your Name</text>
  <text x="20" y="42" font-family="Arial, sans-serif" font-size="10" fill="{accent_color}">Job Title</text>
  <text x="220" y="26" font-family="Arial, sans-serif" font-size="8" fill="#64748b">email@example.com</text>
  <line x1="16" y1="50" x2="284" y2="50" stroke="{accent_color}" stroke-width="2"/>"""
    else:
        header_block = f"""
  <text x="150" y="26" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#0f172a">Your Name</text>
  <text x="150" y="42" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="{accent_color}">Job Title</text>
  <line x1="16" y1="50" x2="284" y2="50" stroke="{accent_color}" stroke-width="2"/>"""

    section_blocks: list[str] = []
    vertical_offset = 64
    for section_name in template.section_order[:4]:
        section_blocks.append(
            f'  <text x="20" y="{vertical_offset}" font-family="Arial, sans-serif" '
            f'font-size="9" font-weight="700" fill="{accent_color}">{section_name.upper()}</text>'
        )
        vertical_offset += 14
        section_blocks.append(
            f'  <rect x="20" y="{vertical_offset - 6}" width="240" height="4" rx="2" fill="#e2e8f0"/>'
        )
        vertical_offset += 10
        section_blocks.append(
            f'  <rect x="20" y="{vertical_offset - 6}" width="190" height="4" rx="2" fill="#f1f5f9"/>'
        )
        vertical_offset += 16

    sections_markup = "\n".join(section_blocks)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200" role="img" aria-label="{template.name} preview">
  <rect width="300" height="200" fill="#ffffff" rx="10"/>
  <rect x="1" y="1" width="298" height="198" fill="none" stroke="#e2e8f0" rx="10"/>
{header_block}
{sections_markup}
</svg>"""
