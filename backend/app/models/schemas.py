from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.constants import BatchStatus, ChangeStatus, CoachPriority, JobStatus


class SectionInstruction(BaseModel):
    section_path: str
    instruction: str = ""


class InstructionProfile(BaseModel):
    id: str
    name: str
    global_instruction: str = ""
    section_instructions: list[SectionInstruction] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CVProjectCreate(BaseModel):
    name: str = "Master CV"


class CVProjectResponse(BaseModel):
    id: str
    name: str
    master_file: str
    sections: list[str]
    locked_files: list[str]
    source_type: str = "zip"
    template_id: str | None = None
    created_at: datetime


class CVTemplateSummary(BaseModel):
    id: str
    name: str
    description: str
    preview_color: str
    category: str
    section_order: list[str]
    preview_url: str


class MasterSectionRefineRequest(BaseModel):
    section_path: str
    instruction: str = ""
    global_instruction: str = ""


class MasterSectionRefineResponse(BaseModel):
    section_path: str
    content: str
    reason: str = ""


class CVCoachReviewRequest(BaseModel):
    target_role: str = ""
    focus: str = ""


class CVCoachSectionSuggestion(BaseModel):
    section_path: str
    score: int = Field(ge=0, le=100, default=70)
    priority: CoachPriority = CoachPriority.MEDIUM
    issues: list[str] = Field(default_factory=list)
    suggested_instruction: str = ""


class CVCoachReviewResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100, default=70)
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    top_improvements: list[str] = Field(default_factory=list)
    section_suggestions: list[CVCoachSectionSuggestion] = Field(default_factory=list)


class CoachChatMessage(BaseModel):
    role: str
    content: str


class CoachChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[CoachChatMessage] = Field(default_factory=list)
    target_role: str = ""
    focus: str = ""


class CoachChatResponse(BaseModel):
    reply: str
    suggested_section_path: str | None = None
    suggested_instruction: str | None = None


class TailoringPreferencesResponse(BaseModel):
    global_instruction: str = ""
    section_instructions: dict[str, str] = Field(default_factory=dict)
    active_profile_id: str | None = None


class TailoringPreferencesUpdate(BaseModel):
    global_instruction: str | None = None
    section_instructions: dict[str, str] | None = None
    active_profile_id: str | None = None


class SectionContentUpdateRequest(BaseModel):
    content: str


class SectionVersionSummary(BaseModel):
    version_id: str
    section_path: str
    source: str
    created_at: str
    preview: str = ""


class SectionRestoreRequest(BaseModel):
    version_id: str


class CreateFromTemplateRequest(BaseModel):
    name: str = "Master CV"
    template_id: str


class ApplyTemplateRequest(BaseModel):
    template_id: str


class JobDescriptionExtract(BaseModel):
    company: str = ""
    title: str = ""
    location: str = ""
    working_model: str = ""
    salary: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    seniority: str = ""
    industry_keywords: list[str] = Field(default_factory=list)
    visa_requirements: str = ""
    raw_text: str = ""
    extraction_confidence: float = 0.0


class ATSAnalysis(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    keyword_coverage: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    formatting_notes: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    star_assessment: list[str] = Field(default_factory=list)


class FitAnalysis(BaseModel):
    overall_fit: int = Field(ge=0, le=100)
    strong_matches: list[str] = Field(default_factory=list)
    recommended_emphasis: list[str] = Field(default_factory=list)
    potential_gaps: list[str] = Field(default_factory=list)


class SectionChange(BaseModel):
    id: str
    section_path: str
    original_text: str
    proposed_text: str
    reason: str
    job_requirement: str
    evidence_used: str
    status: ChangeStatus = ChangeStatus.PENDING


class TailorRequest(BaseModel):
    cv_project_id: str
    job_url: str | None = None
    job_description: str | None = None
    editable_sections: list[str] = Field(default_factory=list)
    global_instruction: str = ""
    section_instructions: list[SectionInstruction] = Field(default_factory=list)
    instruction_profile_id: str | None = None
    refine_prompt: bool = True


class TailorResponse(BaseModel):
    job_id: str
    fit_analysis: FitAnalysis
    ats_analysis: ATSAnalysis
    changes: list[SectionChange]
    refined_instructions: str = ""
    status: JobStatus


class AnalyzeResponse(BaseModel):
    job_id: str | None = None
    fit_analysis: FitAnalysis
    ats_analysis: ATSAnalysis
    job_description: JobDescriptionExtract
    refined_instructions: str = ""
    status: JobStatus


class TailorPreviewResponse(BaseModel):
    job_id: str | None = None
    fit_analysis: FitAnalysis
    ats_analysis: ATSAnalysis
    changes: list[SectionChange]
    refined_instructions: str = ""
    status: JobStatus


class SectionRefineRequest(BaseModel):
    cv_project_id: str
    section_path: str
    instruction: str = ""
    job_url: str | None = None
    job_description: str | None = None


class SectionRefineResponse(BaseModel):
    job_id: str
    change: SectionChange
    changes: list[SectionChange]
    status: JobStatus = JobStatus.COMPLETED


class CrawlJobRequest(BaseModel):
    url: str
    manual_description: str | None = None


class BatchJobEntry(BaseModel):
    url: str | None = None
    manual_description: str | None = None
    company: str = ""
    title: str = ""
    location: str = ""
    priority: int = 0


class BatchCreateRequest(BaseModel):
    cv_project_id: str
    name: str
    jobs: list[BatchJobEntry]
    global_instruction: str = ""
    section_instructions: list[SectionInstruction] = Field(default_factory=list)
    editable_sections: list[str] = Field(default_factory=list)
    instruction_profile_id: str | None = None


class BatchJobStatus(BaseModel):
    id: str
    url: str | None = None
    company: str = ""
    title: str = ""
    location: str = ""
    status: JobStatus
    fit_score: int | None = None
    key_skills: list[str] = Field(default_factory=list)
    tailoring_status: str = ""
    warnings: list[str] = Field(default_factory=list)
    job_description: JobDescriptionExtract | None = None


class BatchResponse(BaseModel):
    id: str
    name: str
    status: BatchStatus
    cv_project_id: str
    total_jobs: int
    completed: int
    processing: int
    needs_manual: int
    failed: int
    jobs: list[BatchJobStatus]
    created_at: datetime


class PromptRefineRequest(BaseModel):
    raw_instruction: str
    context: str = ""
    target_section: str = ""


class PromptRefineResponse(BaseModel):
    refined_instruction: str
    methodology_applied: str
    suggestions: list[str] = Field(default_factory=list)


class ReportRequest(BaseModel):
    job_id: str | None = None
    batch_id: str | None = None
    include_ats: bool = True
    include_fit: bool = True
    include_changes: bool = True
    include_gaps: bool = True


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


class JobSearchRequest(BaseModel):
    job_title: str = Field(min_length=2, max_length=200)
    location: str = "London, UK"
    max_days_old: int = Field(default=7, ge=1, le=30)
    sources: list[str] = Field(default_factory=lambda: ["indeed_uk", "reed_uk", "web_search"])
    max_results_per_source: int = Field(default=15, ge=1, le=50)


class JobListingResult(BaseModel):
    id: str
    title: str
    company: str = ""
    location: str = ""
    url: str
    source: str
    source_label: str = ""
    posted_date: str = ""
    posted_days_ago: int | None = None
    snippet: str = ""


class JobSearchResponse(BaseModel):
    query: str
    location: str
    max_days_old: int
    total_results: int
    results: list[JobListingResult]
    sources_searched: list[str]
    warnings: list[str] = Field(default_factory=list)
