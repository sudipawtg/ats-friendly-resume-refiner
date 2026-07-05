import json
import logging
import re
import uuid
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings
from app.constants import (
    DEFAULT_GLOBAL_INSTRUCTIONS,
    INSTRUCTION_PROFILES,
    STAR_METHODOLOGY_INSTRUCTION,
    CoachPriority,
)
from app.models.schemas import (
    ATSAnalysis,
    CVCoachReviewResponse,
    CVCoachSectionSuggestion,
    CoachChatResponse,
    FitAnalysis,
    JobDescriptionExtract,
    PromptRefineResponse,
    SectionChange,
)

logger = logging.getLogger(__name__)


def _coerce_string_field(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(item) for item in value if item is not None)
    return str(value)


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _parse_ats_payload(data: dict[str, Any]) -> ATSAnalysis:
    raw_score = data.get("overall_score", 0)
    overall_score = int(float(raw_score or 0))
    overall_score = max(0, min(100, overall_score))
    return ATSAnalysis(
        overall_score=overall_score,
        keyword_coverage=_coerce_string_list(data.get("keyword_coverage")),
        missing_keywords=_coerce_string_list(data.get("missing_keywords")),
        formatting_notes=_coerce_string_list(data.get("formatting_notes")),
        improvements=_coerce_string_list(data.get("improvements")),
        gaps=_coerce_string_list(data.get("gaps")),
        star_assessment=_coerce_string_list(data.get("star_assessment")),
    )


def _sanitize_job_extract_payload(data: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(data)
    for field in (
        "company",
        "title",
        "location",
        "working_model",
        "salary",
        "seniority",
        "visa_requirements",
    ):
        if field in sanitized:
            sanitized[field] = _coerce_string_field(sanitized[field])
    for field in (
        "responsibilities",
        "required_skills",
        "preferred_skills",
        "technologies",
        "industry_keywords",
    ):
        if field in sanitized:
            sanitized[field] = _coerce_string_list(sanitized[field])
    return sanitized


def _parse_fit_payload(data: dict[str, Any]) -> FitAnalysis:
    raw_fit = data.get("overall_fit", 0)
    overall_fit = int(float(raw_fit or 0))
    overall_fit = max(0, min(100, overall_fit))
    return FitAnalysis(
        overall_fit=overall_fit,
        strong_matches=_coerce_string_list(data.get("strong_matches")),
        recommended_emphasis=_coerce_string_list(data.get("recommended_emphasis")),
        potential_gaps=_coerce_string_list(data.get("potential_gaps")),
    )


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key or "sk-placeholder",
            timeout=settings.openai_timeout_seconds,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.openai_api_key)

    async def extract_job_description(self, text: str, source_url: str = "") -> JobDescriptionExtract:
        if not self.is_configured:
            return self._fallback_job_extract(text)

        prompt = f"""Extract structured job posting data from the text below.
Return valid JSON with keys: company, title, location, working_model, salary,
responsibilities (array), required_skills (array), preferred_skills (array),
technologies (array), seniority, industry_keywords (array), visa_requirements,
extraction_confidence (0-1 float).

Source URL: {source_url}

Job text:
{text[:12000]}"""

        response = await self._chat(
            system="You extract job posting fields accurately. Do not invent information not in the text.",
            user=prompt,
            json_mode=True,
        )
        try:
            data = _sanitize_job_extract_payload(json.loads(response))
            data["raw_text"] = text[:5000]
            return JobDescriptionExtract(**data)
        except (json.JSONDecodeError, ValueError) as error:
            logger.warning("Job extraction parse failed: %s", error)
            return self._fallback_job_extract(text)

    async def refine_prompt(
        self, raw_instruction: str, context: str = "", target_section: str = ""
    ) -> PromptRefineResponse:
        if not raw_instruction.strip():
            return PromptRefineResponse(
                refined_instruction=STAR_METHODOLOGY_INSTRUCTION,
                methodology_applied="STAR",
                suggestions=[
                    "No custom instruction provided — STAR methodology will be applied.",
                    "Experience bullets will follow Situation, Task, Action, Result structure.",
                    "ATS keyword alignment will be evaluated against the job description.",
                ],
            )

        if not self.is_configured:
            return PromptRefineResponse(
                refined_instruction=raw_instruction,
                methodology_applied="STAR",
                suggestions=["Configure OPENAI_API_KEY for AI-powered prompt refinement."],
            )

        prompt = f"""Refine this CV tailoring instruction to be clear, actionable, and ATS-friendly.
Preserve user intent. Apply STAR methodology for experience sections when relevant.
Mention what must NOT be invented.

Section: {target_section or "all sections"}
Context: {context[:2000]}
Raw instruction: {raw_instruction}

Return JSON with keys: refined_instruction, methodology_applied, suggestions (array of strings)."""

        response = await self._chat(
            system="You are an expert CV coach and ATS specialist.",
            user=prompt,
            json_mode=True,
        )
        try:
            data = json.loads(response)
            return PromptRefineResponse(**data)
        except (json.JSONDecodeError, ValueError):
            return PromptRefineResponse(
                refined_instruction=raw_instruction,
                methodology_applied="STAR",
                suggestions=["Could not refine — using original instruction."],
            )

    async def analyze_fit(
        self, cv_sections: dict[str, str], job: JobDescriptionExtract
    ) -> FitAnalysis:
        if not self.is_configured:
            return FitAnalysis(
                overall_fit=50,
                strong_matches=["Configure OpenAI for detailed fit analysis"],
                recommended_emphasis=["Upload API key in settings"],
                potential_gaps=["Unable to analyse without API key"],
            )

        cv_text = "\n\n".join(f"=== {k} ===\n{v}" for k, v in cv_sections.items())
        prompt = f"""Compare this CV against the job description. Return JSON with:
overall_fit (0-100 int), strong_matches (array), recommended_emphasis (array), potential_gaps (array).
Be evidence-based. Do not invent CV content.

Job:
Title: {job.title}
Company: {job.company}
Required skills: {job.required_skills}
Technologies: {job.technologies}
Responsibilities: {job.responsibilities[:10]}

CV:
{cv_text[:10000]}"""

        response = await self._chat(
            system="You are a career coach specialising in AI and consulting roles.",
            user=prompt,
            json_mode=True,
        )
        try:
            return _parse_fit_payload(json.loads(response))
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            logger.warning("Fit analysis parse failed: %s", error)
            return FitAnalysis(overall_fit=0)

    async def analyze_ats(
        self,
        cv_sections: dict[str, str],
        job: JobDescriptionExtract,
        global_instruction: str = "",
    ) -> ATSAnalysis:
        instruction = global_instruction.strip() or STAR_METHODOLOGY_INSTRUCTION

        if not self.is_configured:
            return ATSAnalysis(
                overall_score=50,
                improvements=["Configure OpenAI for ATS analysis"],
                gaps=["API key required"],
                star_assessment=[STAR_METHODOLOGY_INSTRUCTION],
            )

        cv_text = "\n\n".join(f"=== {k} ===\n{v}" for k, v in cv_sections.items())
        prompt = f"""Perform ATS analysis comparing CV to job description.
Apply STAR methodology assessment for experience bullets.
Instruction: {instruction}

Return JSON with: overall_score (0-100), keyword_coverage (array), missing_keywords (array),
formatting_notes (array), improvements (array), gaps (array), star_assessment (array of bullet assessments).

Job title: {job.title}
Required skills: {job.required_skills}
Technologies: {job.technologies}

CV:
{cv_text[:10000]}"""

        response = await self._chat(
            system="You are an ATS optimisation expert. Rate honestly. Never suggest inventing credentials.",
            user=prompt,
            json_mode=True,
        )
        try:
            return _parse_ats_payload(json.loads(response))
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            logger.warning("ATS analysis parse failed: %s", error)
            return ATSAnalysis(overall_score=0)

    async def tailor_sections(
        self,
        cv_sections: dict[str, str],
        editable_sections: list[str],
        job: JobDescriptionExtract,
        global_instruction: str,
        section_instructions: dict[str, str],
    ) -> list[SectionChange]:
        if not self.is_configured:
            return []

        changes: list[SectionChange] = []
        combined_instruction = global_instruction.strip() or DEFAULT_GLOBAL_INSTRUCTIONS
        if not global_instruction.strip():
            combined_instruction = f"{DEFAULT_GLOBAL_INSTRUCTIONS}\n{STAR_METHODOLOGY_INSTRUCTION}"

        for section_path in editable_sections:
            original = cv_sections.get(section_path, "")
            if not original.strip() and "objective" not in section_path:
                continue

            section_instruction = section_instructions.get(section_path, "")
            prompt = f"""Tailor this LaTeX CV section for the job below.
CRITICAL RULES:
- Do NOT invent employers, skills, certifications, dates, metrics, or projects.
- Do NOT add percentage improvements or numeric outcomes unless they already appear in the original text.
- Preserve all LaTeX commands, environments, and structure from the original (e.g. tabular, zitemize, \\skills, \\item).
- Never introduce macros not present in the original (e.g. do not use \\resumeSubheading if absent).
- Use real line breaks in proposed_text, not literal \\n escape sequences.
- Only strengthen, reorder, and rephrase existing evidence for ATS keyword alignment.

Return JSON with: proposed_text, reason, job_requirement, evidence_used.

Global instruction: {combined_instruction}
Section instruction: {section_instruction or STAR_METHODOLOGY_INSTRUCTION}

Job:
Title: {job.title} at {job.company}
Required skills: {job.required_skills}
Technologies: {job.technologies}
Key responsibilities: {job.responsibilities[:8]}

Original LaTeX section ({section_path}):
{original[:8000]}"""

            response = await self._chat(
                system="You are a LaTeX CV expert. Output valid LaTeX only. Never hallucinate credentials.",
                user=prompt,
                json_mode=True,
            )
            try:
                data = json.loads(response)
                if data.get("proposed_text", "").strip() == original.strip():
                    continue
                changes.append(
                    SectionChange(
                        id=str(uuid.uuid4()),
                        section_path=section_path,
                        original_text=original,
                        proposed_text=data.get("proposed_text", original),
                        reason=_coerce_string_field(data.get("reason")),
                        job_requirement=_coerce_string_field(data.get("job_requirement")),
                        evidence_used=_coerce_string_field(data.get("evidence_used")),
                    )
                )
            except (json.JSONDecodeError, ValueError) as error:
                logger.warning("Tailoring parse failed for %s: %s", section_path, error)

        return changes

    async def tailor_single_section(
        self,
        section_path: str,
        original: str,
        job: JobDescriptionExtract,
        global_instruction: str,
        section_instruction: str,
    ) -> SectionChange | None:
        if not self.is_configured:
            return None

        combined_instruction = global_instruction.strip() or DEFAULT_GLOBAL_INSTRUCTIONS
        if not global_instruction.strip():
            combined_instruction = f"{DEFAULT_GLOBAL_INSTRUCTIONS}\n{STAR_METHODOLOGY_INSTRUCTION}"

        prompt = f"""Tailor this LaTeX CV section for the job below.
CRITICAL RULES:
- Do NOT invent employers, skills, certifications, dates, metrics, or projects.
- Do NOT add percentage improvements or numeric outcomes unless they already appear in the original text.
- Preserve all LaTeX commands, environments, and structure from the original.
- Never introduce macros not present in the original.
- Use real line breaks in proposed_text, not literal \\n escape sequences.
- Only strengthen, reorder, and rephrase existing evidence for ATS keyword alignment.

Return JSON with: proposed_text, reason, job_requirement, evidence_used.

Global instruction: {combined_instruction}
Section instruction: {section_instruction or STAR_METHODOLOGY_INSTRUCTION}

Job:
Title: {job.title} at {job.company}
Required skills: {job.required_skills}
Technologies: {job.technologies}
Key responsibilities: {job.responsibilities[:8]}

Original LaTeX section ({section_path}):
{original[:8000]}"""

        response = await self._chat(
            system="You are a LaTeX CV expert. Output valid LaTeX only. Never hallucinate credentials.",
            user=prompt,
            json_mode=True,
        )
        try:
            data = json.loads(response)
            proposed_text = data.get("proposed_text", original)
            if not proposed_text.strip():
                return None
            return SectionChange(
                id=str(uuid.uuid4()),
                section_path=section_path,
                original_text=original,
                proposed_text=proposed_text,
                reason=_coerce_string_field(data.get("reason")),
                job_requirement=_coerce_string_field(data.get("job_requirement")),
                evidence_used=_coerce_string_field(data.get("evidence_used")),
            )
        except (json.JSONDecodeError, ValueError) as error:
            logger.warning("Single section tailoring parse failed for %s: %s", section_path, error)
            return None

    async def refine_master_section(
        self,
        section_path: str,
        original: str,
        instruction: str,
        global_instruction: str = "",
    ) -> dict[str, str] | None:
        if not instruction.strip() and not global_instruction.strip():
            raise ValueError("Provide an instruction describing how to update this section.")

        if not self.is_configured:
            return None

        combined_instruction = global_instruction.strip() or DEFAULT_GLOBAL_INSTRUCTIONS
        prompt = f"""Improve this LaTeX CV section according to the user's instruction.
CRITICAL RULES:
- Do NOT invent employers, skills, certifications, dates, metrics, or projects.
- Preserve LaTeX structure, commands, and environments from the original where possible.
- Use real line breaks in content, not literal \\n escape sequences.
- Only rephrase, reorder, tighten, or clarify content already present unless the user explicitly asks to add placeholder guidance.

Return JSON with: content (the full updated LaTeX section body), reason (short explanation).

Global instruction: {combined_instruction}
Section instruction: {instruction or "Improve clarity, impact, and professional tone."}

Section path: {section_path}

Original LaTeX section:
{original[:8000]}"""

        response = await self._chat(
            system="You are a LaTeX CV expert. Output valid LaTeX only. Never hallucinate credentials.",
            user=prompt,
            json_mode=True,
        )
        try:
            data = json.loads(response)
            content = data.get("content", original)
            if not str(content).strip():
                return None
            return {
                "content": str(content),
                "reason": _coerce_string_field(data.get("reason")),
            }
        except (json.JSONDecodeError, ValueError) as error:
            logger.warning("Master section refine parse failed for %s: %s", section_path, error)
            return None

    async def parse_cv_from_text(self, text: str) -> dict[str, object]:
        if not text.strip():
            return {"contact": {}, "sections": {}}

        if not self.is_configured:
            return {"contact": {}, "sections": {}}

        prompt = f"""Parse the CV/resume text below into structured LaTeX section content.
Return valid JSON with keys:
- contact: object with optional name, phone, city, email, linkedin, github, role
- sections: object mapping these exact keys to LaTeX body content (no document wrappers):
  - sections/objective.tex
  - sections/skills.tex
  - sections/experience.tex
  - sections/education.tex
  - sections/activities.tex

Rules:
- Use \\item for bullet lists inside sections when appropriate.
- For experience, prefer \\subsection{{Title \\hfill Dates}}, \\subtext{{Company \\hfill Location}}, \\begin{{zitemize}} ... \\end{{zitemize}} when structure is clear.
- Do not invent employers, degrees, or credentials not present in the source text.
- Escape LaTeX special characters in plain text.
- Leave a section as empty string if no matching content exists.

CV text:
{text[:14000]}"""

        response = await self._chat(
            system="You parse CVs into LaTeX section files accurately without hallucination.",
            user=prompt,
            json_mode=True,
        )
        try:
            data = json.loads(response)
            contact = data.get("contact") or {}
            sections = data.get("sections") or {}
            if not isinstance(contact, dict):
                contact = {}
            if not isinstance(sections, dict):
                sections = {}
            sanitized_contact = {
                key: _coerce_string_field(value)
                for key, value in contact.items()
                if key in {"name", "phone", "city", "email", "linkedin", "github", "role"}
            }
            sanitized_sections = {
                str(key): str(value)
                for key, value in sections.items()
                if str(key).startswith("sections/") and str(value).strip()
            }
            return {"contact": sanitized_contact, "sections": sanitized_sections}
        except (json.JSONDecodeError, ValueError) as error:
            logger.warning("CV parse failed: %s", error)
            return {"contact": {}, "sections": {}}

    async def review_master_cv(
        self,
        sections: dict[str, str],
        target_role: str = "",
        focus: str = "",
    ) -> CVCoachReviewResponse:
        if not sections:
            return CVCoachReviewResponse(
                overall_score=0,
                summary="No CV sections found to review.",
                top_improvements=["Upload or create a CV with editable sections first."],
            )

        if not self.is_configured:
            return self._fallback_coach_review(sections, target_role)

        section_blocks = "\n\n".join(
            f"--- {path} ---\n{content[:4000]}" for path, content in sections.items()
        )
        focus_line = focus.strip() or "clarity, impact, ATS readability, and STAR-style experience bullets"
        role_line = target_role.strip() or "a senior professional role aligned with the CV content"

        prompt = f"""You are an expert CV coach. Review this master CV (LaTeX sections) and coach the candidate.
Target role: {role_line}
Focus areas: {focus_line}

Rules:
- Do NOT invent employers, skills, dates, or metrics.
- Score based on what is present: clarity, impact, structure, keyword richness, evidence quality.
- For each section, provide a concrete suggested_instruction the user can run to improve that section.
- suggested_instruction must be actionable and reference only content already in the CV.

Return JSON with keys:
- overall_score (0-100 int)
- summary (2-3 sentences)
- strengths (array of strings, max 5)
- top_improvements (array of strings, max 5, cross-cutting)
- section_suggestions (array of objects with: section_path, score 0-100, priority "high"|"medium"|"low", issues (array), suggested_instruction)

CV sections:
{section_blocks[:20000]}"""

        response = await self._chat(
            system="You are a supportive CV coach. Be specific and practical. Never hallucinate credentials.",
            user=prompt,
            json_mode=True,
        )
        try:
            data = json.loads(response)
            raw_suggestions = data.get("section_suggestions") or []
            section_suggestions: list[CVCoachSectionSuggestion] = []
            if isinstance(raw_suggestions, list):
                for item in raw_suggestions:
                    if not isinstance(item, dict):
                        continue
                    section_path = _coerce_string_field(item.get("section_path"))
                    if section_path not in sections:
                        continue
                    priority_raw = _coerce_string_field(item.get("priority", CoachPriority.MEDIUM)).lower()
                    priority = (
                        CoachPriority.HIGH
                        if priority_raw == CoachPriority.HIGH
                        else CoachPriority.LOW
                        if priority_raw == CoachPriority.LOW
                        else CoachPriority.MEDIUM
                    )
                    raw_score = item.get("score", 70)
                    score = max(0, min(100, int(float(raw_score or 70))))
                    section_suggestions.append(
                        CVCoachSectionSuggestion(
                            section_path=section_path,
                            score=score,
                            priority=priority,
                            issues=_coerce_string_list(item.get("issues")),
                            suggested_instruction=_coerce_string_field(
                                item.get("suggested_instruction")
                            )
                            or "Improve clarity, impact, and professional tone without adding new facts.",
                        )
                    )

            raw_overall = data.get("overall_score", 70)
            overall_score = max(0, min(100, int(float(raw_overall or 70))))

            return CVCoachReviewResponse(
                overall_score=overall_score,
                summary=_coerce_string_field(data.get("summary")),
                strengths=_coerce_string_list(data.get("strengths")),
                top_improvements=_coerce_string_list(data.get("top_improvements")),
                section_suggestions=section_suggestions,
            )
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            logger.warning("CV coach review parse failed: %s", error)
            return self._fallback_coach_review(sections, target_role)

    def _fallback_coach_review(
        self, sections: dict[str, str], target_role: str
    ) -> CVCoachReviewResponse:
        suggestions: list[CVCoachSectionSuggestion] = []
        for section_path, content in sections.items():
            word_count = len(content.split())
            issues: list[str] = []
            score = 75
            if word_count < 20:
                issues.append("Section looks thin — add more detail from your existing experience.")
                score = 55
            if "\\item" not in content and "experience" in section_path:
                issues.append("Experience may read better as bullet points with measurable outcomes.")
                score = min(score, 65)
            suggestions.append(
                CVCoachSectionSuggestion(
                    section_path=section_path,
                    score=score,
                    priority=CoachPriority.HIGH if score < 65 else CoachPriority.MEDIUM,
                    issues=issues or ["Review tone, clarity, and impact."],
                    suggested_instruction=(
                        "Tighten wording, use strong action verbs, and highlight measurable outcomes "
                        "already present. Do not invent new facts."
                    ),
                )
            )
        role_hint = f" for {target_role}" if target_role.strip() else ""
        return CVCoachReviewResponse(
            overall_score=70,
            summary=f"Basic review complete{role_hint}. Configure OPENAI_API_KEY for deeper AI coaching.",
            strengths=["CV structure is in place across all sections."],
            top_improvements=[
                "Strengthen experience bullets with STAR structure and metrics where evidence exists.",
                "Ensure skills are grouped and aligned with your target role.",
            ],
            section_suggestions=suggestions,
        )

    async def coach_chat(
        self,
        sections: dict[str, str],
        message: str,
        history: list[dict[str, str]],
        target_role: str = "",
        focus: str = "",
    ) -> CoachChatResponse:
        section_blocks = "\n\n".join(
            f"--- {path} ---\n{content[:2500]}" for path, content in sections.items()
        )
        history_lines = "\n".join(
            f"{entry.get('role', 'user').upper()}: {entry.get('content', '')[:800]}"
            for entry in history[-8:]
        )
        focus_line = focus.strip() or "clarity, impact, ATS readability"
        role_line = target_role.strip() or "the candidate's target role"

        if not self.is_configured:
            return CoachChatResponse(
                reply=(
                    "Configure OPENAI_API_KEY for conversational coaching. "
                    "Meanwhile, use Analyze my CV for structured suggestions."
                )
            )

        prompt = f"""You are a supportive CV coach helping improve a LaTeX CV through conversation.
Target role: {role_line}
Focus: {focus_line}

Rules:
- Never invent employers, skills, dates, or metrics.
- Give practical, concise coaching in plain English.
- When the user asks to change a section, include suggested_section_path and suggested_instruction
  so the app can apply the edit. Use exact section paths from the CV.
- If no section edit is needed, set suggested_section_path and suggested_instruction to empty strings.

Recent conversation:
{history_lines or "(none)"}

User message: {message}

CV sections:
{section_blocks[:18000]}

Return JSON with keys:
- reply (string, conversational response)
- suggested_section_path (string or empty)
- suggested_instruction (string or empty, actionable LaTeX edit instruction)"""

        response = await self._chat(
            system="You are an expert CV coach. Be concise, friendly, and evidence-based.",
            user=prompt,
            json_mode=True,
        )
        try:
            data = json.loads(response)
            suggested_path = _coerce_string_field(data.get("suggested_section_path"))
            if suggested_path and suggested_path not in sections:
                suggested_path = ""
            suggested_instruction = _coerce_string_field(data.get("suggested_instruction"))
            if suggested_path and not suggested_instruction:
                suggested_instruction = message.strip()
            return CoachChatResponse(
                reply=_coerce_string_field(data.get("reply")) or "How would you like to improve your CV next?",
                suggested_section_path=suggested_path or None,
                suggested_instruction=suggested_instruction or None,
            )
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            logger.warning("Coach chat parse failed: %s", error)
            return CoachChatResponse(
                reply="I had trouble processing that. Try rephrasing or use Analyze my CV for structured tips."
            )

    async def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        kwargs: dict[str, Any] = {
            "model": self._settings.openai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        completion = await self._client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content or ""

    def _fallback_job_extract(self, text: str) -> JobDescriptionExtract:
        words = text.split()
        skills_pattern = re.compile(r"\b(python|java|sql|aws|azure|ai|ml|llm|rag)\b", re.I)
        found_skills = list({m.group(0).lower() for m in skills_pattern.finditer(text)})
        return JobDescriptionExtract(
            raw_text=text[:5000],
            required_skills=found_skills[:20],
            extraction_confidence=0.2 if len(words) > 50 else 0.0,
        )
