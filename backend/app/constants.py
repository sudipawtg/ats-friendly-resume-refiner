from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PENDING = "pending"
    CRAWLING = "crawling"
    NEEDS_MANUAL = "needs_manual"
    READY = "ready"
    TAILORING = "tailoring"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchStatus(StrEnum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"


class ChangeStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class CoachPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


DEFAULT_GLOBAL_INSTRUCTIONS = (
    "Keep the tone professional, concise and credible. "
    "Do not invent experience, employers, certifications, metrics or skills. "
    "Only strengthen and reorder evidence already present in the CV. "
    "Use UK English unless instructed otherwise."
)

STAR_METHODOLOGY_INSTRUCTION = (
    "Apply the STAR methodology (Situation, Task, Action, Result) when rewriting "
    "experience bullets. Each bullet should implicitly or explicitly convey context, "
    "responsibility, actions taken, and measurable outcomes where evidence exists."
)

LOCKED_CV_FILES = frozenset({"resume.tex", "_header.tex", "TLCresume.sty", "LICENSE.txt", "README.md"})

DEFAULT_SECTIONS = (
    "sections/objective.tex",
    "sections/skills.tex",
    "sections/experience.tex",
    "sections/activities.tex",
    "sections/education.tex",
)

INSTRUCTION_PROFILES: dict[str, str] = {
    "ai_engineer": (
        "Position for AI/ML engineering roles. Emphasise LLMs, RAG, MLOps, "
        "production deployment, and measurable technical outcomes."
    ),
    "ai_consultant": (
        "Position for AI consulting and solution delivery. Emphasise stakeholder "
        "engagement, business value, workshops, governance, and enterprise delivery."
    ),
    "ai_product_manager": (
        "Position for AI product roles. Emphasise roadmap ownership, user research, "
        "cross-functional delivery, and product metrics."
    ),
    "data_analyst": (
        "Position for data analyst roles. Emphasise SQL, visualisation, reporting, "
        "statistical analysis, and business insights."
    ),
    "technical_product_manager": (
        "Position for technical PM roles. Emphasise API design, engineering "
        "collaboration, technical trade-offs, and delivery lifecycle."
    ),
    "research_academic": (
        "Position for research and academic roles. Emphasise publications, "
        "methodology, reproducibility, and scholarly contributions."
    ),
}

JOB_SEARCH_SOURCES: dict[str, str] = {
    "reed_uk": "Reed.co.uk",
    "remotive": "Remotive (Remote)",
    "arbeitnow": "Arbeitnow",
    "adzuna": "Adzuna UK",
    "indeed_uk": "Indeed UK",
    "totaljobs": "Totaljobs",
    "cv_library": "CV-Library",
    "web_search": "Web Search",
}

DATE_FILTER_OPTIONS: dict[str, int] = {
    "1": 1,
    "3": 3,
    "7": 7,
    "14": 14,
    "30": 30,
}
