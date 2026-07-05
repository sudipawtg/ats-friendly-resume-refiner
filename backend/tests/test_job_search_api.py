import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_job_search_sources_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/jobs/search/sources")
    assert response.status_code == 200
    data = response.json()
    assert "indeed_uk" in data
    assert "web_search" in data


@pytest.mark.asyncio
async def test_job_search_date_filters_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/jobs/search/date-filters")
    assert response.status_code == 200
    assert response.json()["7"] == 7


@pytest.mark.asyncio
async def test_job_search_post_endpoint(monkeypatch):
    from app.routers import job_search as job_search_router

    async def mock_search(self, request):
        from app.models.schemas import JobListingResult, JobSearchResponse

        return JobSearchResponse(
            query=request.job_title,
            location=request.location,
            max_days_old=request.max_days_old,
            total_results=1,
            results=[
                JobListingResult(
                    id="test-1",
                    title="AI Engineer",
                    url="https://example.com/job/1",
                    source="indeed_uk",
                    source_label="Indeed UK",
                )
            ],
            sources_searched=["indeed_uk"],
        )

    monkeypatch.setattr(
        job_search_router.JobSearchService,
        "search_jobs",
        mock_search,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/jobs/search",
            json={"job_title": "AI Engineer", "location": "London, UK", "max_days_old": 7},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert data["results"][0]["title"] == "AI Engineer"
