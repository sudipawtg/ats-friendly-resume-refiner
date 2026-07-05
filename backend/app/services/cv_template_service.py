import logging
import shutil
from pathlib import Path

from app.cv_templates.registry import CVTemplateDefinition, get_template_definition
from app.constants import DEFAULT_SECTIONS

logger = logging.getLogger(__name__)

SECTION_FILE_MAP: dict[str, str] = {
    "Skills": "sections/skills.tex",
    "Experience": "sections/experience.tex",
    "Education": "sections/education.tex",
    "Activities": "sections/activities.tex",
    "Objective": "sections/objective.tex",
}

DEFAULT_CONTACT: dict[str, str] = {
    "name": "Your Name",
    "phone": "+44 0000 000000",
    "city": "City, Country",
    "email": "you@example.com",
    "linkedin": "your-linkedin",
    "github": "your-github",
    "role": "Your Job Title",
}

DEFAULT_SECTION_CONTENT: dict[str, str] = {
    "sections/objective.tex": "",
    "sections/skills.tex": "\\item Add your key skills here",
    "sections/experience.tex": (
        "\\subsection{{Job Title \\hfill Start --- End}}\n"
        "\\subtext{Company \\hfill Location}\n"
        "\\begin{zitemize}\n"
        "\\item Describe your impact with measurable outcomes.\n"
        "\\end{zitemize}"
    ),
    "sections/education.tex": "\\item Degree, Institution, Year",
    "sections/activities.tex": "\\item Certifications, volunteering, or side projects",
}


class CVTemplateService:
    def materialize_project(
        self,
        destination: Path,
        template_id: str,
        sections_content: dict[str, str] | None = None,
        contact: dict[str, str] | None = None,
    ) -> CVTemplateDefinition:
        template = get_template_definition(template_id)
        if template is None:
            raise ValueError(f"Unknown template: {template_id}")

        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)

        resolved_contact = {**DEFAULT_CONTACT, **(contact or {})}
        resolved_sections = {**DEFAULT_SECTION_CONTENT, **(sections_content or {})}

        (destination / "TLCresume.sty").write_text(
            self._build_style_file(template),
            encoding="utf-8",
        )
        (destination / "_header.tex").write_text(
            self._build_header_file(template, resolved_contact),
            encoding="utf-8",
        )
        (destination / "resume.tex").write_text(
            self._build_resume_file(template, resolved_contact),
            encoding="utf-8",
        )

        sections_dir = destination / "sections"
        sections_dir.mkdir(parents=True, exist_ok=True)
        for section_path in DEFAULT_SECTIONS:
            section_file = destination / section_path
            section_file.parent.mkdir(parents=True, exist_ok=True)
            section_file.write_text(resolved_sections.get(section_path, ""), encoding="utf-8")

        logger.info("Materialized CV template %s at %s", template_id, destination)
        return template

    def apply_template_layout(
        self,
        master_root: Path,
        template_id: str,
        contact: dict[str, str] | None = None,
    ) -> None:
        template = get_template_definition(template_id)
        if template is None:
            raise ValueError(f"Unknown template: {template_id}")

        existing_contact = self._read_contact_from_resume(master_root / "resume.tex")
        resolved_contact = {**DEFAULT_CONTACT, **existing_contact, **(contact or {})}

        (master_root / "TLCresume.sty").write_text(
            self._build_style_file(template),
            encoding="utf-8",
        )
        (master_root / "_header.tex").write_text(
            self._build_header_file(template, resolved_contact),
            encoding="utf-8",
        )
        (master_root / "resume.tex").write_text(
            self._build_resume_file(template, resolved_contact),
            encoding="utf-8",
        )

    def _build_style_file(self, template: CVTemplateDefinition) -> str:
        red, green, blue = template.highlight_rgb
        if template.section_style == "bold_rule":
            section_format = (
                r"\titleformat{\section}{\color{highlight} \bfseries \raggedright \Large}"
                r"{}{0em}{}[\vspace{-0.5em}\hrulefill]"
            )
        elif template.section_style == "minimal":
            section_format = (
                r"\titleformat{\section}{\color{highlight} \bfseries \raggedright \large}"
                r"{}{0em}{}[]"
            )
        else:
            section_format = (
                r"\titleformat{\section}{\color{highlight} \scshape \raggedright \large}"
                r"{}{0em}{}[\vspace{-0.75em}\hrulefill]"
            )

        return f"""\\NeedsTeXFormat{{LaTeX2e}}
\\ProvidesPackage{{TLCresume}}[ResumeForge template package]

\\RequirePackage[T1]{{fontenc}}
\\RequirePackage[default,semibold]{{sourcesanspro}}
\\RequirePackage[10pt]{{moresize}}
\\usepackage{{anyfontsize}}
\\RequirePackage{{csquotes}}
\\RequirePackage[margin=.5in, top=.5in, bottom=1in]{{geometry}}
\\raggedright
\\raggedbottom

\\RequirePackage{{xcolor}}
\\definecolor{{highlight}}{{RGB}}{{{red}, {green}, {blue}}}

\\RequirePackage{{hyperref}}
\\hypersetup{{colorlinks=true,urlcolor=highlight}}

\\RequirePackage[inline]{{enumitem}}
\\setlength{{\\tabcolsep}}{{0in}}

\\RequirePackage[nostruts]{{titlesec}}
\\titlespacing*{{\\section}}{{0em}}{{0.5em}}{{0em}}
{section_format}
\\titlespacing*{{\\subsection}}{{0em}}{{0em}}{{0em}}
\\titleformat{{\\subsection}}{{\\bfseries}}{{}}{{0em}}{{}}[]

\\newcommand{{\\skills}}[1]{{ {{\\bfseries #1}} }}
\\newcommand{{\\subtext}}[1]{{\\textit{{#1}}\\par\\vspace{{-.75em}}}}

\\setlist[itemize]{{align=parleft,left=0pt..1em}}
\\newenvironment{{zitemize}}{{
\\begin{{itemize}} \\itemsep 0pt \\parskip 0pt \\parsep 1pt}}
{{\\end{{itemize}}\\vspace{{-.5em}}}}

\\pagenumbering{{gobble}}
\\RequirePackage{{standalone}}
\\RequirePackage[english]{{babel}}
"""

    def _build_header_file(self, template: CVTemplateDefinition, contact: dict[str, str]) -> str:
        email = contact["email"]
        linkedin = contact["linkedin"]
        github = contact["github"]

        if template.header_layout == "left":
            return f"""\\RequirePackage{{fancyhdr}}
\\fancypagestyle{{fancy}}{{%
\\fancyhf{{}}
\\lhead{{\\phone \\\\
        \\city \\\\
        \\href{{mailto:{email}}}{{{email}}}}}
\\rhead{{\\href{{https://github.com/{github}}}{{github.com/{github}}} \\\\
        \\href{{https://www.linkedin.com/in/{linkedin}}}{{linkedin.com/in/{linkedin}}}}}
\\chead{{}}
\\renewcommand{{\\headrulewidth}}{{1pt}}
\\renewcommand{{\\headrule}}{{\\hbox to\\headwidth{{%
  \\color{{highlight}}\\leaders\\hrule height \\headrulewidth\\hfill}}}}
}}
\\pagestyle{{fancy}}
\\setlength{{\\headheight}}{{90pt}}
\\setlength{{\\headsep}}{{5pt}}
"""

        return f"""\\RequirePackage{{fancyhdr}}
\\fancypagestyle{{fancy}}{{%
\\fancyhf{{}}
\\lhead{{\\phone \\\\
        \\city \\\\
        \\href{{mailto:{email}}}{{{email}}}}}
\\chead{{%
    \\centering {{\\Huge \\skills \\name \\vspace{{.25em}}}} \\\\
    {{\\color{{highlight}} \\Large{{\\role}}}}}}
\\rhead{{\\href{{https://github.com/{github}}}{{github.com/{github}}} \\\\
        \\href{{https://www.linkedin.com/in/{linkedin}}}{{linkedin.com/in/{linkedin}}}}}
\\renewcommand{{\\headrulewidth}}{{1pt}}
\\renewcommand{{\\headrule}}{{\\hbox to\\headwidth{{%
  \\color{{highlight}}\\leaders\\hrule height \\headrulewidth\\hfill}}}}
}}
\\pagestyle{{fancy}}
\\setlength{{\\headheight}}{{90pt}}
\\setlength{{\\headsep}}{{5pt}}
"""

    def _build_resume_file(self, template: CVTemplateDefinition, contact: dict[str, str]) -> str:
        section_blocks = "\n\n".join(
            f"\\section{{{section_name}}}\n\\input{{{SECTION_FILE_MAP[section_name]}}}"
            for section_name in template.section_order
            if section_name in SECTION_FILE_MAP
        )

        return f"""\\documentclass[letter,10pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{TLCresume}}

\\def\\name{{{contact["name"]}}}
\\def\\phone{{{contact["phone"]}}}
\\def\\city{{{contact["city"]}}}
\\def\\email{{{contact["email"]}}}
\\def\\LinkedIn{{{contact["linkedin"]}}}
\\def\\github{{{contact["github"]}}}
\\def\\role{{{contact["role"]}}}

\\input{{_header}}
\\begin{{document}}
{self._build_title_block(template)}

{section_blocks}

\\end{{document}}
"""

    def _build_title_block(self, template: CVTemplateDefinition) -> str:
        if template.header_layout == "left":
            return "{\\Huge \\skills \\name \\par}\n{\\color{highlight} \\Large{\\role} \\par}\n\\vspace{0.5em}"
        return ""

    def _read_contact_from_resume(self, resume_path: Path) -> dict[str, str]:
        if not resume_path.exists():
            return {}

        content = resume_path.read_text(encoding="utf-8")
        contact: dict[str, str] = {}
        field_map = {
            "name": "name",
            "phone": "phone",
            "city": "city",
            "email": "email",
            "LinkedIn": "linkedin",
            "github": "github",
            "role": "role",
        }
        for latex_key, contact_key in field_map.items():
            marker = f"\\def\\{latex_key}{{"
            start_index = content.find(marker)
            if start_index == -1:
                continue
            start_index += len(marker)
            end_index = content.find("}", start_index)
            if end_index == -1:
                continue
            contact[contact_key] = content[start_index:end_index]
        return contact
