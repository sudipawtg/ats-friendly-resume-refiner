import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


def _json_type():
    return JSON().with_variant(JSONB, "postgresql")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    api_keys: Mapped[list["TenantApiKey"]] = relationship(back_populates="tenant")
    cv_projects: Mapped[list["CvProject"]] = relationship(back_populates="tenant")


class TenantApiKey(Base):
    __tablename__ = "tenant_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="api_keys")


class CvProject(Base):
    __tablename__ = "cv_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    master_file: Mapped[str] = mapped_column(String(255), nullable=False)
    master_root: Mapped[str] = mapped_column(String(255), nullable=False, default="master")
    sections: Mapped[list] = mapped_column(_json_type(), nullable=False, default=list)
    locked_files: Mapped[list] = mapped_column(_json_type(), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="cv_projects")
    tailoring_jobs: Mapped[list["TailoringJob"]] = relationship(back_populates="cv_project")


class TailoringJob(Base):
    __tablename__ = "tailoring_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    cv_project_id: Mapped[str] = mapped_column(ForeignKey("cv_projects.id", ondelete="CASCADE"), index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, default="tailor")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    job_description: Mapped[dict | None] = mapped_column(_json_type(), nullable=True)
    fit_analysis: Mapped[dict | None] = mapped_column(_json_type(), nullable=True)
    ats_analysis: Mapped[dict | None] = mapped_column(_json_type(), nullable=True)
    refined_instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    request_payload: Mapped[dict | None] = mapped_column(_json_type(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queue_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cv_project: Mapped["CvProject"] = relationship(back_populates="tailoring_jobs")
    changes: Mapped[list["SectionChangeRecord"]] = relationship(
        back_populates="tailoring_job", cascade="all, delete-orphan"
    )


class SectionChangeRecord(Base):
    __tablename__ = "section_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tailoring_job_id: Mapped[str] = mapped_column(
        ForeignKey("tailoring_jobs.id", ondelete="CASCADE"), index=True
    )
    section_path: Mapped[str] = mapped_column(String(255), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    job_requirement: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_used: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    tailoring_job: Mapped["TailoringJob"] = relationship(back_populates="changes")


class BatchCampaign(Base):
    __tablename__ = "batch_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processing")
    cv_project_id: Mapped[str] = mapped_column(ForeignKey("cv_projects.id", ondelete="CASCADE"), index=True)
    config: Mapped[dict] = mapped_column(_json_type(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list["BatchJobItem"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class BatchJobItem(Base):
    __tablename__ = "batch_job_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(ForeignKey("batch_campaigns.id", ondelete="CASCADE"), index=True)
    tailoring_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("tailoring_jobs.id", ondelete="SET NULL"), nullable=True
    )
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_skills: Mapped[list] = mapped_column(_json_type(), nullable=False, default=list)
    tailoring_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    warnings: Mapped[list] = mapped_column(_json_type(), nullable=False, default=list)

    batch: Mapped["BatchCampaign"] = relationship(back_populates="jobs")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("tenant_id", "url", name="uq_saved_jobs_tenant_url"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    job_description: Mapped[dict | None] = mapped_column(_json_type(), nullable=True)
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
