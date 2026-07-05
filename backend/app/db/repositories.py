import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import CvProject, SavedJob, SectionChangeRecord, TailoringJob

logger = logging.getLogger(__name__)


class CvProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_project(
        self,
        tenant_id: str,
        project_id: str,
        name: str,
        master_file: str,
        master_root: str,
        sections: list[str],
        locked_files: list[str],
    ) -> CvProject:
        record = CvProject(
            id=project_id,
            tenant_id=tenant_id,
            name=name,
            master_file=master_file,
            master_root=master_root,
            sections=sections,
            locked_files=locked_files,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_projects_for_tenant(self, tenant_id: str) -> list[CvProject]:
        result = await self._session.execute(
            select(CvProject)
            .where(CvProject.tenant_id == tenant_id)
            .order_by(CvProject.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_project_for_tenant(self, tenant_id: str, project_id: str) -> CvProject | None:
        result = await self._session.execute(
            select(CvProject).where(
                CvProject.id == project_id,
                CvProject.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_queued_job(
        self,
        tenant_id: str,
        cv_project_id: str,
        job_type: str,
        request_payload: dict,
        job_url: str | None = None,
        job_id: str | None = None,
    ) -> TailoringJob:
        record = TailoringJob(
            id=job_id or str(uuid.uuid4()),
            tenant_id=tenant_id,
            cv_project_id=cv_project_id,
            job_type=job_type,
            status="queued",
            url=job_url,
            request_payload=request_payload,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def update_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
        queue_job_id: str | None = None,
    ) -> None:
        record = await self._session.get(TailoringJob, job_id)
        if record is None:
            return
        record.status = status
        record.error_message = error_message
        if queue_job_id:
            record.queue_job_id = queue_job_id
        record.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def save_tailor_result(
        self,
        job_id: str,
        status: str,
        fit_analysis: dict,
        ats_analysis: dict,
        changes: list[dict],
        job_description: dict | None,
        refined_instructions: str,
    ) -> None:
        record = await self._session.get(
            TailoringJob,
            job_id,
            options=[selectinload(TailoringJob.changes)],
        )
        if record is None:
            return
        record.status = status
        record.fit_analysis = fit_analysis
        record.ats_analysis = ats_analysis
        record.job_description = job_description
        record.refined_instructions = refined_instructions
        record.error_message = None
        record.updated_at = datetime.now(timezone.utc)
        record.changes.clear()
        for change in changes:
            record.changes.append(
                SectionChangeRecord(
                    id=change.get("id", str(uuid.uuid4())),
                    section_path=change["section_path"],
                    original_text=change.get("original_text", ""),
                    proposed_text=change.get("proposed_text", ""),
                    reason=change.get("reason", ""),
                    job_requirement=change.get("job_requirement", ""),
                    evidence_used=change.get("evidence_used", ""),
                    status=change.get("status", "pending"),
                )
            )
        await self._session.flush()

    async def get_job_for_tenant(self, tenant_id: str, job_id: str) -> TailoringJob | None:
        result = await self._session.execute(
            select(TailoringJob)
            .where(TailoringJob.id == job_id, TailoringJob.tenant_id == tenant_id)
            .options(selectinload(TailoringJob.changes))
        )
        return result.scalar_one_or_none()

    async def list_outputs_for_tenant(self, tenant_id: str, limit: int = 100) -> list[TailoringJob]:
        result = await self._session.execute(
            select(TailoringJob)
            .where(
                TailoringJob.tenant_id == tenant_id,
                TailoringJob.status.in_(["completed", "needs_manual", "failed"]),
            )
            .order_by(TailoringJob.updated_at.desc())
            .limit(limit)
            .options(selectinload(TailoringJob.changes))
        )
        return list(result.scalars().all())


class SavedJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_saved_jobs(self, tenant_id: str) -> list[SavedJob]:
        result = await self._session.execute(
            select(SavedJob)
            .where(SavedJob.tenant_id == tenant_id)
            .order_by(SavedJob.updated_at.desc())
        )
        return list(result.scalars().all())

    async def upsert_saved_job(
        self,
        tenant_id: str,
        url: str,
        title: str,
        company: str,
        location: str,
        job_description: dict | None,
        fit_score: int | None = None,
        notes: str = "",
    ) -> SavedJob:
        result = await self._session.execute(
            select(SavedJob).where(SavedJob.tenant_id == tenant_id, SavedJob.url == url)
        )
        saved = result.scalar_one_or_none()
        if saved is None:
            saved = SavedJob(
                tenant_id=tenant_id,
                url=url,
                title=title,
                company=company,
                location=location,
                job_description=job_description,
                fit_score=fit_score,
                notes=notes,
            )
            self._session.add(saved)
        else:
            saved.title = title or saved.title
            saved.company = company or saved.company
            saved.location = location or saved.location
            saved.job_description = job_description or saved.job_description
            if fit_score is not None:
                saved.fit_score = fit_score
            saved.notes = notes or saved.notes
            saved.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return saved

    async def delete_saved_job(self, tenant_id: str, saved_job_id: str) -> bool:
        saved = await self._session.get(SavedJob, saved_job_id)
        if saved is None or saved.tenant_id != tenant_id:
            return False
        await self._session.delete(saved)
        await self._session.flush()
        return True
