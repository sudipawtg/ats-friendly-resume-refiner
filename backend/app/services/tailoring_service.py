import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.constants import INSTRUCTION_PROFILES, JobStatus
from app.models.schemas import (
    AnalyzeResponse,
    BatchCreateRequest,
    BatchJobStatus,
    BatchResponse,
    BatchStatus,
    FitAnalysis,
    JobDescriptionExtract,
    SectionChange,
    SectionRefineRequest,
    SectionRefineResponse,
    TailorPreviewResponse,
    TailorRequest,
    TailorResponse,
)
from app.services.crawler import JobCrawlerService
from app.services.cv_storage import CVStorageService
from app.services.tenant_storage_paths import resolve_tenant_storage_root
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def normalize_proposed_latex(content: str) -> str:
    normalized = content.replace("\\n", "\n")
    normalized = normalized.replace(" \\ ", " \\\\ ")
    normalized = normalized.replace("\n\\ ", "\n\\\\ ")
    return normalized


class TailoringService:
    def __init__(self, settings: Settings, tenant_id: str | None = None) -> None:
        self._settings = settings
        self._tenant_id = tenant_id
        self._tenant_root = resolve_tenant_storage_root(settings, tenant_id)
        self._storage = CVStorageService(settings, tenant_id=tenant_id)
        self._crawler = JobCrawlerService(settings)
        self._llm = LLMService(settings)
        self._jobs_path = self._tenant_root / "jobs.json"
        self._batches_path = self._tenant_root / "batches.json"

    def _load_jobs(self) -> dict[str, dict]:
        if not self._jobs_path.exists():
            return {}
        return json.loads(self._jobs_path.read_text(encoding="utf-8"))

    def _save_jobs(self, jobs: dict[str, dict]) -> None:
        self._jobs_path.write_text(json.dumps(jobs, indent=2, default=str), encoding="utf-8")

    def _load_batches(self) -> dict[str, dict]:
        if not self._batches_path.exists():
            return {}
        return json.loads(self._batches_path.read_text(encoding="utf-8"))

    def _save_batches(self, batches: dict[str, dict]) -> None:
        self._batches_path.write_text(json.dumps(batches, indent=2, default=str), encoding="utf-8")

    def get_job(self, job_id: str) -> dict | None:
        return self._load_jobs().get(job_id)

    def get_batch(self, batch_id: str) -> dict | None:
        return self._load_batches().get(batch_id)

    def list_batches(self) -> list[dict]:
        return list(self._load_batches().values())

    async def tailor_single(self, request: TailorRequest) -> TailorResponse:
        job_id = str(uuid.uuid4())
        return await self.tailor_single_for_job_id(request, job_id)

    async def tailor_single_for_job_id(self, request: TailorRequest, job_id: str) -> TailorResponse:
        context = await self._prepare_tailoring_context(request)
        if context["status"] == JobStatus.NEEDS_MANUAL:
            return self._build_needs_manual_response(job_id, request, context)

        fit = context["fit"]
        ats = context["ats"]
        changes = context["changes"]
        job_description = context["job_description"]
        refined_instructions = context["refined_instructions"]

        self._storage.copy_master_to_output(request.cv_project_id, job_id)
        for change in changes:
            self._storage.write_output_section(
                request.cv_project_id,
                job_id,
                change.section_path,
                normalize_proposed_latex(change.proposed_text),
            )

        summary = {
            "job_id": job_id,
            "fit_analysis": fit.model_dump(),
            "ats_analysis": ats.model_dump(),
            "changes": [c.model_dump() for c in changes],
            "job_description": job_description.model_dump(),
            "refined_instructions": refined_instructions,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._storage.save_tailoring_summary(request.cv_project_id, job_id, summary)

        status = JobStatus.COMPLETED
        job_record = self._build_job_record(
            job_id, request, job_description, status, changes, fit, ats
        )
        self._persist_job(job_record)

        return TailorResponse(
            job_id=job_id,
            fit_analysis=fit,
            ats_analysis=ats,
            changes=changes,
            refined_instructions=refined_instructions,
            status=status,
        )

    async def analyze_single(self, request: TailorRequest) -> AnalyzeResponse:
        context = await self._prepare_tailoring_context(request, include_changes=False)
        if context["status"] == JobStatus.NEEDS_MANUAL:
            from app.models.schemas import ATSAnalysis

            empty_job = context["job_description"] or JobDescriptionExtract(
                raw_text=request.job_description or ""
            )
            return AnalyzeResponse(
                fit_analysis=FitAnalysis(
                    overall_fit=0,
                    potential_gaps=[
                        "Could not extract enough job information. Paste the full job description manually."
                    ],
                ),
                ats_analysis=ATSAnalysis(
                    overall_score=0,
                    gaps=["Insufficient job description for ATS analysis"],
                    improvements=["Paste the full job description manually to continue"],
                ),
                job_description=empty_job,
                refined_instructions=context["refined_instructions"],
                status=JobStatus.NEEDS_MANUAL,
            )

        return AnalyzeResponse(
            fit_analysis=context["fit"],
            ats_analysis=context["ats"],
            job_description=context["job_description"],
            refined_instructions=context["refined_instructions"],
            status=JobStatus.COMPLETED,
        )

    async def preview_single(self, request: TailorRequest) -> TailorPreviewResponse:
        context = await self._prepare_tailoring_context(request, include_changes=True)
        if context["status"] == JobStatus.NEEDS_MANUAL:
            from app.models.schemas import ATSAnalysis

            return TailorPreviewResponse(
                fit_analysis=FitAnalysis(
                    overall_fit=0,
                    potential_gaps=[
                        "Could not extract enough job information. Paste the full job description manually."
                    ],
                ),
                ats_analysis=ATSAnalysis(
                    overall_score=0,
                    gaps=["Insufficient job description for ATS analysis"],
                    improvements=["Paste the full job description manually to continue"],
                ),
                changes=[],
                refined_instructions=context["refined_instructions"],
                status=JobStatus.NEEDS_MANUAL,
            )

        return TailorPreviewResponse(
            fit_analysis=context["fit"],
            ats_analysis=context["ats"],
            changes=context["changes"],
            refined_instructions=context["refined_instructions"],
            status=JobStatus.COMPLETED,
            job_id=self._write_preview_output(request, context),
        )

    def _write_preview_output(self, request: TailorRequest, context: dict) -> str:
        preview_job_id = str(uuid.uuid4())
        changes: list[SectionChange] = context["changes"]
        job_description = context["job_description"]
        refined_instructions = context["refined_instructions"]

        self._storage.copy_master_to_output(request.cv_project_id, preview_job_id)
        for change in changes:
            self._storage.write_output_section(
                request.cv_project_id,
                preview_job_id,
                change.section_path,
                normalize_proposed_latex(change.proposed_text),
            )

        summary = {
            "job_id": preview_job_id,
            "preview": True,
            "fit_analysis": context["fit"].model_dump(),
            "ats_analysis": context["ats"].model_dump(),
            "changes": [change.model_dump() for change in changes],
            "job_description": job_description.model_dump(),
            "refined_instructions": refined_instructions,
            "request": request.model_dump(),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._storage.save_tailoring_summary(request.cv_project_id, preview_job_id, summary)
        return preview_job_id

    async def refine_preview_section(
        self, preview_job_id: str, request: SectionRefineRequest
    ) -> SectionRefineResponse:
        summary = self._storage.load_tailoring_summary(request.cv_project_id, preview_job_id)
        if summary is None:
            raise ValueError("Preview session not found. Run Preview first.")

        job_description_data = summary.get("job_description") or {}
        job_description = JobDescriptionExtract.model_validate(job_description_data)

        if request.job_description:
            job_description = await self._crawler.extract_job("", request.job_description)
        elif request.job_url:
            job_description = await self._crawler.extract_job(request.job_url)

        stored_request = summary.get("request") or {}
        global_instruction = stored_request.get("global_instruction", "")
        profile_id = stored_request.get("instruction_profile_id")
        if profile_id and profile_id in INSTRUCTION_PROFILES:
            global_instruction = f"{INSTRUCTION_PROFILES[profile_id]}\n{global_instruction}".strip()

        master_sections = self._storage.read_all_sections(request.cv_project_id)
        original_text = master_sections.get(request.section_path, "")
        try:
            current_output = self._storage.read_output_section(
                request.cv_project_id, preview_job_id, request.section_path
            )
        except FileNotFoundError:
            current_output = original_text

        section_instruction = request.instruction.strip() or stored_request.get(
            "global_instruction", ""
        )
        change = await self._llm.tailor_single_section(
            request.section_path,
            original_text or current_output,
            job_description,
            global_instruction,
            section_instruction,
        )
        if change is None:
            raise ValueError(f"Could not regenerate section {request.section_path}")

        self._storage.write_output_section(
            request.cv_project_id,
            preview_job_id,
            change.section_path,
            normalize_proposed_latex(change.proposed_text),
        )

        existing_changes = [
            SectionChange.model_validate(entry) for entry in summary.get("changes", [])
        ]
        updated_changes = [
            change if entry.section_path == change.section_path else entry
            for entry in existing_changes
        ]
        if not any(entry.section_path == change.section_path for entry in updated_changes):
            updated_changes.append(change)

        summary["changes"] = [entry.model_dump() for entry in updated_changes]
        self._storage.save_tailoring_summary(request.cv_project_id, preview_job_id, summary)

        return SectionRefineResponse(
            job_id=preview_job_id,
            change=change,
            changes=updated_changes,
            status=JobStatus.COMPLETED,
        )

    async def _prepare_tailoring_context(
        self, request: TailorRequest, include_changes: bool = True
    ) -> dict:
        project = self._storage.get_project(request.cv_project_id)
        if not project:
            raise ValueError("CV project not found")

        global_instruction = request.global_instruction
        if request.instruction_profile_id and request.instruction_profile_id in INSTRUCTION_PROFILES:
            profile_text = INSTRUCTION_PROFILES[request.instruction_profile_id]
            global_instruction = f"{profile_text}\n{global_instruction}".strip()

        refined_instructions = ""
        if request.refine_prompt:
            refine_result = await self._llm.refine_prompt(
                raw_instruction=global_instruction,
                context=f"Tailoring for job URL: {request.job_url or 'manual'}",
            )
            if refine_result.refined_instruction:
                global_instruction = refine_result.refined_instruction
            refined_instructions = refine_result.refined_instruction

        job_description = None
        if request.job_description:
            job_description = await self._crawler.extract_job("", request.job_description)
        elif request.job_url:
            job_description = await self._crawler.extract_job(request.job_url)

        if not job_description or job_description.extraction_confidence < 0.2:
            if not request.job_description and not request.job_url:
                raise ValueError("Job URL or description is required")
            empty_job = job_description or JobDescriptionExtract(
                raw_text=request.job_description or ""
            )
            return {
                "status": JobStatus.NEEDS_MANUAL,
                "job_description": empty_job,
                "refined_instructions": refined_instructions,
                "fit": None,
                "ats": None,
                "changes": [],
            }

        cv_sections = self._storage.read_all_sections(request.cv_project_id)
        editable = request.editable_sections or project["sections"]
        section_map = {si.section_path: si.instruction for si in request.section_instructions}

        fit = await self._llm.analyze_fit(cv_sections, job_description)
        ats = await self._llm.analyze_ats(cv_sections, job_description, global_instruction)
        changes: list[SectionChange] = []
        if include_changes:
            changes = await self._llm.tailor_sections(
                cv_sections, editable, job_description, global_instruction, section_map
            )

        return {
            "status": JobStatus.COMPLETED,
            "job_description": job_description,
            "refined_instructions": refined_instructions,
            "fit": fit,
            "ats": ats,
            "changes": changes,
        }

    def _build_needs_manual_response(
        self, job_id: str, request: TailorRequest, context: dict
    ) -> TailorResponse:
        from app.models.schemas import ATSAnalysis

        empty_job = context["job_description"]
        job_record = self._build_job_record(
            job_id, request, empty_job, JobStatus.NEEDS_MANUAL, [], FitAnalysis(overall_fit=0), None
        )
        self._persist_job(job_record)
        return TailorResponse(
            job_id=job_id,
            fit_analysis=FitAnalysis(
                overall_fit=0,
                potential_gaps=[
                    "Could not extract enough job information. Paste the full job description manually."
                ],
            ),
            ats_analysis=ATSAnalysis(
                overall_score=0,
                gaps=["Insufficient job description for ATS analysis"],
                improvements=["Paste the full job description manually to continue"],
            ),
            changes=[],
            refined_instructions=context["refined_instructions"],
            status=JobStatus.NEEDS_MANUAL,
        )

    async def create_batch(self, request: BatchCreateRequest) -> BatchResponse:
        batch_id = str(uuid.uuid4())
        seen_urls: set[str] = set()
        job_entries: list[dict] = []

        for entry in request.jobs:
            url_key = (entry.url or "").strip().lower()
            if url_key and url_key in seen_urls:
                continue
            if url_key:
                seen_urls.add(url_key)

            job_id = str(uuid.uuid4())
            job_entries.append(
                {
                    "id": job_id,
                    "url": entry.url,
                    "manual_description": entry.manual_description,
                    "company": entry.company,
                    "title": entry.title,
                    "location": entry.location,
                    "priority": entry.priority,
                    "status": JobStatus.PENDING.value,
                    "fit_score": None,
                    "key_skills": [],
                    "tailoring_status": "pending",
                    "warnings": [],
                }
            )

        batch_record = {
            "id": batch_id,
            "name": request.name,
            "status": BatchStatus.PROCESSING.value,
            "cv_project_id": request.cv_project_id,
            "global_instruction": request.global_instruction,
            "section_instructions": [si.model_dump() for si in request.section_instructions],
            "editable_sections": request.editable_sections,
            "instruction_profile_id": request.instruction_profile_id,
            "jobs": job_entries,
            "created_at": datetime.utcnow().isoformat(),
        }
        batches = self._load_batches()
        batches[batch_id] = batch_record
        self._save_batches(batches)

        asyncio.create_task(self._process_batch(batch_id))

        return self._to_batch_response(batch_record)

    async def _process_batch(self, batch_id: str) -> None:
        batches = self._load_batches()
        batch = batches.get(batch_id)
        if not batch:
            return

        project = self._storage.get_project(batch["cv_project_id"])
        if not project:
            batch["status"] = BatchStatus.PARTIAL.value
            self._save_batches(batches)
            return

        editable = batch.get("editable_sections") or project["sections"]
        section_instructions = {
            si["section_path"]: si["instruction"]
            for si in batch.get("section_instructions", [])
        }

        for job_entry in batch["jobs"]:
            if job_entry["status"] not in (JobStatus.PENDING.value, JobStatus.FAILED.value):
                continue

            job_entry["status"] = JobStatus.CRAWLING.value
            self._save_batches(batches)

            try:
                job_description = await self._crawler.extract_job(
                    job_entry.get("url") or "",
                    job_entry.get("manual_description"),
                )
                if job_description.extraction_confidence < 0.2:
                    job_entry["status"] = JobStatus.NEEDS_MANUAL.value
                    job_entry["warnings"] = ["Could not extract enough job information."]
                    continue

                job_entry["company"] = job_entry["company"] or job_description.company
                job_entry["title"] = job_entry["title"] or job_description.title
                job_entry["location"] = job_entry["location"] or job_description.location
                job_entry["key_skills"] = (
                    job_description.required_skills[:8] + job_description.technologies[:4]
                )
                job_entry["job_description"] = job_description.model_dump()

                job_entry["status"] = JobStatus.TAILORING.value
                self._save_batches(batches)

                cv_sections = self._storage.read_all_sections(batch["cv_project_id"])
                global_instruction = batch.get("global_instruction", "")
                fit = await self._llm.analyze_fit(cv_sections, job_description)
                job_entry["fit_score"] = fit.overall_fit

                changes = await self._llm.tailor_sections(
                    cv_sections,
                    editable,
                    job_description,
                    global_instruction,
                    section_instructions,
                )

                self._storage.copy_master_to_output(batch["cv_project_id"], job_entry["id"])
                for change in changes:
                    self._storage.write_output_section(
                        batch["cv_project_id"],
                        job_entry["id"],
                        change.section_path,
                        normalize_proposed_latex(change.proposed_text),
                    )

                ats = await self._llm.analyze_ats(cv_sections, job_description, global_instruction)
                summary = {
                    "job_id": job_entry["id"],
                    "batch_id": batch_id,
                    "fit_analysis": fit.model_dump(),
                    "ats_analysis": ats.model_dump(),
                    "changes": [c.model_dump() for c in changes],
                    "job_description": job_description.model_dump(),
                }
                self._storage.save_tailoring_summary(
                    batch["cv_project_id"], job_entry["id"], summary
                )

                job_entry["status"] = JobStatus.COMPLETED.value
                job_entry["tailoring_status"] = "completed"
            except Exception as error:
                logger.exception("Batch job failed: %s", error)
                job_entry["status"] = JobStatus.FAILED.value
                job_entry["warnings"] = [str(error)]

        completed = sum(1 for j in batch["jobs"] if j["status"] == JobStatus.COMPLETED.value)
        failed = sum(1 for j in batch["jobs"] if j["status"] == JobStatus.FAILED.value)
        needs_manual = sum(1 for j in batch["jobs"] if j["status"] == JobStatus.NEEDS_MANUAL.value)

        if completed == len(batch["jobs"]):
            batch["status"] = BatchStatus.COMPLETED.value
        elif completed > 0:
            batch["status"] = BatchStatus.PARTIAL.value
        else:
            batch["status"] = BatchStatus.PROCESSING.value

        self._save_batches(batches)

    def update_change_status(
        self, job_id: str, change_id: str, status: str, edited_text: str | None = None
    ) -> SectionChange | None:
        jobs = self._load_jobs()
        job = jobs.get(job_id)
        if not job:
            return None

        for change in job.get("changes", []):
            if change["id"] == change_id:
                change["status"] = status
                if edited_text is not None:
                    change["proposed_text"] = edited_text
                    change["status"] = "edited"
                self._save_jobs(jobs)
                return SectionChange(**change)
        return None

    def _build_job_record(
        self,
        job_id: str,
        request: TailorRequest,
        job_description,
        status: JobStatus,
        changes: list[SectionChange],
        fit: FitAnalysis,
        ats,
    ) -> dict:
        return {
            "id": job_id,
            "cv_project_id": request.cv_project_id,
            "url": request.job_url,
            "status": status.value,
            "job_description": job_description.model_dump() if job_description else None,
            "fit_analysis": fit.model_dump(),
            "ats_analysis": ats.model_dump() if ats else None,
            "changes": [c.model_dump() for c in changes],
            "created_at": datetime.utcnow().isoformat(),
        }

    def _persist_job(self, job_record: dict) -> None:
        jobs = self._load_jobs()
        jobs[job_record["id"]] = job_record
        self._save_jobs(jobs)

    def _to_batch_response(self, batch: dict) -> BatchResponse:
        jobs = batch.get("jobs", [])
        return BatchResponse(
            id=batch["id"],
            name=batch["name"],
            status=BatchStatus(batch["status"]),
            cv_project_id=batch["cv_project_id"],
            total_jobs=len(jobs),
            completed=sum(1 for j in jobs if j["status"] == JobStatus.COMPLETED.value),
            processing=sum(
                1
                for j in jobs
                if j["status"] in (JobStatus.CRAWLING.value, JobStatus.TAILORING.value, JobStatus.PENDING.value)
            ),
            needs_manual=sum(1 for j in jobs if j["status"] == JobStatus.NEEDS_MANUAL.value),
            failed=sum(1 for j in jobs if j["status"] == JobStatus.FAILED.value),
            jobs=[BatchJobStatus(**j) for j in jobs],
            created_at=datetime.fromisoformat(batch["created_at"]),
        )
