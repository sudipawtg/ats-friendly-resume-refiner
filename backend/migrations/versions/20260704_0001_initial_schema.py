"""Initial multi-tenant schema

Revision ID: 20260704_0001
Revises:
Create Date: 2026-07-04 10:35:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260704_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "tenant_api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_tenant_api_keys_tenant_id", "tenant_api_keys", ["tenant_id"], unique=False)

    op.create_table(
        "cv_projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("master_file", sa.String(length=255), nullable=False),
        sa.Column("master_root", sa.String(length=255), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("locked_files", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cv_projects_tenant_id", "cv_projects", ["tenant_id"], unique=False)

    op.create_table(
        "tailoring_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("cv_project_id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("job_description", sa.JSON(), nullable=True),
        sa.Column("fit_analysis", sa.JSON(), nullable=True),
        sa.Column("ats_analysis", sa.JSON(), nullable=True),
        sa.Column("refined_instructions", sa.Text(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queue_job_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["cv_project_id"], ["cv_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tailoring_jobs_tenant_id", "tailoring_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_tailoring_jobs_cv_project_id", "tailoring_jobs", ["cv_project_id"], unique=False)
    op.create_index("ix_tailoring_jobs_status", "tailoring_jobs", ["status"], unique=False)

    op.create_table(
        "section_changes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tailoring_job_id", sa.String(length=36), nullable=False),
        sa.Column("section_path", sa.String(length=255), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("proposed_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("job_requirement", sa.Text(), nullable=False),
        sa.Column("evidence_used", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["tailoring_job_id"], ["tailoring_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_section_changes_tailoring_job_id", "section_changes", ["tailoring_job_id"], unique=False)

    op.create_table(
        "batch_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("cv_project_id", sa.String(length=36), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["cv_project_id"], ["cv_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_campaigns_tenant_id", "batch_campaigns", ["tenant_id"], unique=False)
    op.create_index("ix_batch_campaigns_cv_project_id", "batch_campaigns", ["cv_project_id"], unique=False)

    op.create_table(
        "batch_job_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("tailoring_job_id", sa.String(length=36), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("fit_score", sa.Integer(), nullable=True),
        sa.Column("key_skills", sa.JSON(), nullable=False),
        sa.Column("tailoring_status", sa.String(length=50), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batch_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tailoring_job_id"], ["tailoring_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_job_items_batch_id", "batch_job_items", ["batch_id"], unique=False)

    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("job_description", sa.JSON(), nullable=True),
        sa.Column("fit_score", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "url", name="uq_saved_jobs_tenant_url"),
    )
    op.create_index("ix_saved_jobs_tenant_id", "saved_jobs", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_saved_jobs_tenant_id", table_name="saved_jobs")
    op.drop_table("saved_jobs")
    op.drop_index("ix_batch_job_items_batch_id", table_name="batch_job_items")
    op.drop_table("batch_job_items")
    op.drop_index("ix_batch_campaigns_cv_project_id", table_name="batch_campaigns")
    op.drop_index("ix_batch_campaigns_tenant_id", table_name="batch_campaigns")
    op.drop_table("batch_campaigns")
    op.drop_index("ix_section_changes_tailoring_job_id", table_name="section_changes")
    op.drop_table("section_changes")
    op.drop_index("ix_tailoring_jobs_status", table_name="tailoring_jobs")
    op.drop_index("ix_tailoring_jobs_cv_project_id", table_name="tailoring_jobs")
    op.drop_index("ix_tailoring_jobs_tenant_id", table_name="tailoring_jobs")
    op.drop_table("tailoring_jobs")
    op.drop_index("ix_cv_projects_tenant_id", table_name="cv_projects")
    op.drop_table("cv_projects")
    op.drop_index("ix_tenant_api_keys_tenant_id", table_name="tenant_api_keys")
    op.drop_table("tenant_api_keys")
    op.drop_table("tenants")
