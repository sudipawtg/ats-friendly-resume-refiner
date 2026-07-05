"""Live AI Engineer simulation — tailor Resume_latex for high ATS score."""

from __future__ import annotations

import asyncio
import io
import json
import shutil
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app
from app.services.cv_storage import CVStorageService
from app.services.llm_service import LLMService
from app.models.schemas import JobDescriptionExtract
from tests.conftest import make_resume_latex_zip

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = REPO_ROOT / "exports"

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

AI_ENGINEER_JOB = """
AI Engineer — TechNova Ltd, London, UK (Hybrid)

Salary: £90,000–£110,000

We are hiring an AI Engineer to design, build, and deploy production LLM applications at scale.
You will own RAG pipelines, model integration, and cloud-native microservices for enterprise clients.

Responsibilities:
- Design and implement retrieval-augmented generation (RAG) systems with LangChain and vector databases
- Build and fine-tune LLM features using Python, PyTorch, and OpenAI/Azure APIs
- Develop FastAPI microservices and deploy on AWS with Docker and Kubernetes
- Implement MLOps practices: evaluation, monitoring, CI/CD, and model versioning
- Collaborate with product and data teams on prompt engineering and model evaluation
- Mentor engineers on production AI delivery and responsible AI governance

Required skills:
Python, PyTorch, LLMs, RAG, LangChain, FastAPI, AWS, Docker, Kubernetes, REST APIs,
3+ years machine learning engineering experience, production deployment experience

Preferred skills:
MLOps, vector databases (Pinecone, Weaviate), Azure OpenAI, stakeholder communication,
hybrid search, GraphRAG, AI agents, LangGraph

Technologies: Python, PyTorch, OpenAI API, LangChain, FastAPI, AWS, Docker, Kubernetes,
PostgreSQL, Redis, vector databases, Git, CI/CD

Seniority: Senior AI Engineer
Visa: Right to work in the UK required
""".strip()

ATS_GLOBAL_INSTRUCTION = """
Position this candidate as a Senior AI Engineer for a production LLM / RAG role.
Maximize ATS keyword alignment with the job posting while staying truthful to existing evidence.

Priorities:
1. Mirror exact job keywords in skills and experience: Python, PyTorch, LLMs, RAG, LangChain,
   FastAPI, AWS, Docker, Kubernetes, MLOps, vector databases, OpenAI API, microservices.
2. Strengthen experience bullets with STAR structure using only evidence already in the CV.
3. Do NOT invent metrics, percentages, employers, or tools not already supported in the CV.
4. Keep all LaTeX structure intact — preserve tabular, zitemize, \\skills, and \\item blocks.
5. Emphasize Docker, Kubernetes, MLOps, and LangChain in skills where already credible.
""".strip()

EDITABLE_SECTIONS = [
    "sections/skills.tex",
    "sections/experience.tex",
]

TENANT_HEADERS = {"X-Tenant-ID": DEFAULT_TENANT_ID}


async def run_ai_engineer_simulation() -> int:
    settings = get_settings()
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY is not set in backend/.env")
        return 1

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=== AI Engineer ATS Simulation ===")
    print(f"Model: {settings.openai_model}")
    print(f"Storage: {settings.storage_dir}")
    print("---")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=300.0) as client:
        print("1. Uploading Resume_latex master CV...")
        upload = await client.post(
            "/api/cvs/upload",
            headers=TENANT_HEADERS,
            files={"file": ("master_cv.zip", io.BytesIO(make_resume_latex_zip()), "application/zip")},
            data={"name": "Sudip Kandel — Master CV"},
        )
        upload.raise_for_status()
        project = upload.json()
        project_id = project["id"]
        print(f"   Project ID: {project_id}")
        print(f"   Sections: {', '.join(project['sections'])}")

        print("\n2. Extracting AI Engineer job requirements...")
        crawl = await client.post(
            "/api/crawl",
            json={"url": "", "manual_description": AI_ENGINEER_JOB},
        )
        crawl.raise_for_status()
        job_extract = crawl.json()
        print(f"   Title: {job_extract.get('title') or 'AI Engineer'}")
        print(f"   Confidence: {job_extract['extraction_confidence']}")
        print(f"   Required skills: {job_extract.get('required_skills', [])[:10]}")

        print("\n3. Baseline ATS analysis (before tailoring)...")
        analyze_before = await client.post(
            "/api/tailor/analyze",
            headers=TENANT_HEADERS,
            json={
                "cv_project_id": project_id,
                "job_description": AI_ENGINEER_JOB,
                "editable_sections": EDITABLE_SECTIONS,
                "global_instruction": ATS_GLOBAL_INSTRUCTION,
                "instruction_profile_id": "ai_engineer",
                "refine_prompt": True,
            },
        )
        analyze_before.raise_for_status()
        before = analyze_before.json()
        print(f"   Fit score (before): {before['fit_analysis']['overall_fit']}%")
        print(f"   ATS score (before): {before['ats_analysis']['overall_score']}")
        if before["ats_analysis"].get("missing_keywords"):
            print(f"   Missing keywords: {before['ats_analysis']['missing_keywords'][:12]}")

        print("\n4. Tailoring CV for AI Engineer role (OpenAI — ~2 min)...")
        tailor = await client.post(
            "/api/tailor",
            headers=TENANT_HEADERS,
            json={
                "cv_project_id": project_id,
                "job_description": AI_ENGINEER_JOB,
                "editable_sections": EDITABLE_SECTIONS,
                "global_instruction": ATS_GLOBAL_INSTRUCTION,
                "instruction_profile_id": "ai_engineer",
                "refine_prompt": True,
            },
        )
        tailor.raise_for_status()
        result = tailor.json()
        job_id = result["job_id"]

        print("\n5. Tailoring results")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {result['status']}")
        print(f"   Fit score: {result['fit_analysis']['overall_fit']}%")
        print(f"   ATS score (pre-apply analysis): {result['ats_analysis']['overall_score']}")
        print(f"   Section changes applied: {len(result['changes'])}")

        for change in result["changes"]:
            print(f"\n   --- {change['section_path']} ---")
            print(f"   Reason: {change['reason'][:140]}...")

        post_ats_score = result["ats_analysis"]["overall_score"]
        post_fit_score = result["fit_analysis"]["overall_fit"]

        if result["status"] == "completed":
            print("\n6. Post-tailor ATS re-analysis on updated sections...")
            storage = CVStorageService(settings, tenant_id=DEFAULT_TENANT_ID)
            output_sections: dict[str, str] = {}
            for section_path in EDITABLE_SECTIONS:
                try:
                    output_sections[section_path] = storage.read_output_section(
                        project_id, job_id, section_path
                    )
                except FileNotFoundError:
                    continue

            job_model = JobDescriptionExtract(**{**job_extract, "raw_text": AI_ENGINEER_JOB[:5000]})
            llm = LLMService(settings)
            post_ats = await llm.analyze_ats(output_sections, job_model, ATS_GLOBAL_INSTRUCTION)
            post_ats_score = post_ats.overall_score
            post_fit = await llm.analyze_fit(output_sections, job_model)
            post_fit_score = post_fit.overall_fit

            print(f"   ATS score (after tailoring): {post_ats_score}")
            print(f"   Fit score (after tailoring): {post_fit_score}%")
            print(f"   Keyword coverage: {post_ats.keyword_coverage[:15]}")
            if post_ats.missing_keywords:
                print(f"   Remaining gaps: {post_ats.missing_keywords[:8]}")

            print("\n7. Exporting artifacts...")
            zip_response = await client.get(
                f"/api/cvs/{project_id}/download/{job_id}",
                headers=TENANT_HEADERS,
            )
            zip_response.raise_for_status()
            zip_path = EXPORTS_DIR / "AI_Engineer_Tailored_CV.zip"
            zip_path.write_bytes(zip_response.content)
            print(f"   ZIP: {zip_path} ({len(zip_response.content):,} bytes)")

            report_response = await client.post(
                "/api/reports/html",
                headers=TENANT_HEADERS,
                json={
                    "job_id": job_id,
                    "include_ats": True,
                    "include_fit": True,
                    "include_changes": True,
                    "include_gaps": True,
                },
            )
            report_response.raise_for_status()
            report_path = EXPORTS_DIR / "AI_Engineer_ATS_Report.html"
            report_path.write_bytes(report_response.content)
            print(f"   Report: {report_path}")

            from app.services.pdf_service import CVPdfService

            pdf_source = CVPdfService(settings, tenant_id=DEFAULT_TENANT_ID).generate_tailored_pdf(
                project_id, job_id
            )
            pdf_dest = EXPORTS_DIR / "AI_Engineer_Tailored_CV.pdf"
            shutil.copy2(pdf_source, pdf_dest)
            print(f"   PDF: {pdf_dest} ({pdf_dest.stat().st_size:,} bytes)")

        summary = {
            "project_id": project_id,
            "job_id": job_id,
            "status": result["status"],
            "fit_score_before": before["fit_analysis"]["overall_fit"],
            "ats_score_before": before["ats_analysis"]["overall_score"],
            "fit_score_after": post_fit_score,
            "ats_score_after": post_ats_score,
            "changes_count": len(result["changes"]),
            "exports": {
                "pdf": str(EXPORTS_DIR / "AI_Engineer_Tailored_CV.pdf"),
                "zip": str(EXPORTS_DIR / "AI_Engineer_Tailored_CV.zip"),
                "report": str(EXPORTS_DIR / "AI_Engineer_ATS_Report.html"),
            },
        }
        summary_path = EXPORTS_DIR / "AI_Engineer_simulation_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        print("\n=== SIMULATION COMPLETE ===")
        print(json.dumps(summary, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_ai_engineer_simulation()))
