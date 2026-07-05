import io
import logging
import re
from dataclasses import dataclass

from pypdf import PdfReader

logger = logging.getLogger(__name__)

MIN_USABLE_TEXT_CHARS = 200

SECTION_HEADER_PATTERN = re.compile(
    r"^(?P<header>(?:skills?|technical\s+skills?|core\s+competencies|experience|work\s+history|"
    r"employment|professional\s+experience|education|activities|certifications?|summary|objective|"
    r"profile|about\s+me|projects?|achievements?))\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

SECTION_PATH_BY_HEADER: dict[str, str] = {
    "skill": "sections/skills.tex",
    "skills": "sections/skills.tex",
    "technical skills": "sections/skills.tex",
    "core competencies": "sections/skills.tex",
    "experience": "sections/experience.tex",
    "work history": "sections/experience.tex",
    "employment": "sections/experience.tex",
    "professional experience": "sections/experience.tex",
    "education": "sections/education.tex",
    "activities": "sections/activities.tex",
    "certification": "sections/activities.tex",
    "certifications": "sections/activities.tex",
    "achievement": "sections/activities.tex",
    "achievements": "sections/activities.tex",
    "summary": "sections/objective.tex",
    "objective": "sections/objective.tex",
    "profile": "sections/objective.tex",
    "about me": "sections/objective.tex",
    "project": "sections/experience.tex",
    "projects": "sections/experience.tex",
}


@dataclass
class ParsedCVContent:
    contact: dict[str, str]
    sections: dict[str, str]
    raw_text: str
    extraction_method: str = "pypdf"


class PDFImportService:
    def extract_text(self, pdf_bytes: bytes) -> tuple[str, str]:
        strategies: list[tuple[str, str]] = []

        pypdf_text = self._extract_with_pypdf(pdf_bytes)
        if pypdf_text.strip():
            strategies.append(("pypdf", pypdf_text))

        pymupdf_text = self._extract_with_pymupdf(pdf_bytes)
        if pymupdf_text.strip():
            strategies.append(("pymupdf", pymupdf_text))

        ocr_text = self._extract_with_ocr(pdf_bytes)
        if ocr_text.strip():
            strategies.append(("ocr", ocr_text))

        if not strategies:
            return "", "none"

        best_method, best_text = max(strategies, key=lambda item: len(item[1].strip()))
        if len(best_text.strip()) < MIN_USABLE_TEXT_CHARS and len(strategies) > 1:
            best_method, best_text = max(strategies, key=lambda item: len(item[1].strip()))
        logger.info(
            "PDF text extraction selected method=%s chars=%d",
            best_method,
            len(best_text.strip()),
        )
        return best_text, best_method

    def parse_with_heuristics(self, text: str, extraction_method: str = "pypdf") -> ParsedCVContent:
        contact = self._extract_contact(text)
        sections = self._split_sections(text)
        if not sections:
            sections = {
                "sections/experience.tex": self._text_to_latex_items(text[:12000]),
            }
        return ParsedCVContent(
            contact=contact,
            sections=sections,
            raw_text=text,
            extraction_method=extraction_method,
        )

    def _extract_with_pypdf(self, pdf_bytes: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append(page_text.strip())
            return self._normalize_text("\n\n".join(pages))
        except Exception as error:
            logger.warning("pypdf extraction failed: %s", error)
            return ""

    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> str:
        try:
            import fitz
        except ImportError:
            return ""

        try:
            document = fitz.open(stream=pdf_bytes, filetype="pdf")
            blocks: list[str] = []
            for page in document:
                page_text = page.get_text("text") or ""
                if page_text.strip():
                    blocks.append(page_text.strip())
            document.close()
            return self._normalize_text("\n\n".join(blocks))
        except Exception as error:
            logger.warning("pymupdf extraction failed: %s", error)
            return ""

    def _extract_with_ocr(self, pdf_bytes: bytes) -> str:
        try:
            import pytesseract
            import fitz
        except ImportError:
            return ""

        try:
            document = fitz.open(stream=pdf_bytes, filetype="pdf")
            ocr_pages: list[str] = []
            for page in document:
                pixmap = page.get_pixmap(dpi=200)
                image_bytes = pixmap.tobytes("png")
                page_text = pytesseract.image_to_string(image_bytes) or ""
                if page_text.strip():
                    ocr_pages.append(page_text.strip())
            document.close()
            return self._normalize_text("\n\n".join(ocr_pages))
        except Exception as error:
            logger.warning("OCR extraction failed: %s", error)
            return ""

    def _normalize_text(self, text: str) -> str:
        cleaned = text.replace("\x00", " ")
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _extract_contact(self, text: str) -> dict[str, str]:
        contact: dict[str, str] = {}
        email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
        if email_match:
            contact["email"] = email_match.group(0)

        phone_match = re.search(r"(\+\d[\d\s\-()]{7,}\d)", text)
        if phone_match:
            contact["phone"] = phone_match.group(1).strip()

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            first_line = lines[0]
            if "@" not in first_line and len(first_line.split()) <= 5:
                contact["name"] = first_line

        linkedin_match = re.search(r"linkedin\.com/in/([\w-]+)", text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = linkedin_match.group(1)

        github_match = re.search(r"github\.com/([\w-]+)", text, re.IGNORECASE)
        if github_match:
            contact["github"] = github_match.group(1)

        role_candidates = lines[1:4] if len(lines) > 1 else []
        for candidate in role_candidates:
            if len(candidate) < 80 and "@" not in candidate:
                contact["role"] = candidate
                break

        return contact

    def _split_sections(self, text: str) -> dict[str, str]:
        matches = list(SECTION_HEADER_PATTERN.finditer(text))
        if not matches:
            return {}

        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            header_key = match.group("header").strip().lower()
            section_path = SECTION_PATH_BY_HEADER.get(header_key)
            if section_path is None:
                continue
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            if not section_text:
                continue
            sections[section_path] = self._text_to_latex_items(section_text)

        return sections

    def _text_to_latex_items(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "\\item Imported content — edit with AI"
        bullet_lines = [f"\\item {self._escape_latex(line)}" for line in lines[:40]]
        return "\n".join(bullet_lines)

    def _escape_latex(self, text: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
        }
        escaped = text
        for character, replacement in replacements.items():
            escaped = escaped.replace(character, replacement)
        return escaped
