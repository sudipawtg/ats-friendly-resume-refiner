import logging

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.constants import DATE_FILTER_OPTIONS, JOB_SEARCH_SOURCES
from app.models.schemas import JobSearchRequest, JobSearchResponse
from app.services.job_search import JobSearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Job Discovery"])


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest) -> JobSearchResponse:
    service = JobSearchService(get_settings())
    try:
        return await service.search_jobs(request)
    except Exception as error:
        logger.exception("Job search failed")
        raise HTTPException(status_code=500, detail="Job search failed. Please try again.") from error


@router.get("/search/sources")
async def list_job_search_sources() -> dict[str, str]:
    return JOB_SEARCH_SOURCES


@router.get("/search/date-filters")
async def list_date_filters() -> dict[str, int]:
    return DATE_FILTER_OPTIONS
