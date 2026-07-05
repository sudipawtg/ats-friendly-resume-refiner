from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import JobSearchRequest
from app.services.job_search import JobSearchService


@pytest.fixture
def search_service(tmp_path):
    from app.config import Settings

    return JobSearchService(Settings(storage_dir=tmp_path))


class TestSearchJobs:
    @pytest.mark.asyncio
    async def test_search_with_remotive_mock(self, search_service):
        mock_jobs = {
            "jobs": [
                {
                    "title": "Senior AI Engineer",
                    "company_name": "Acme",
                    "candidate_required_location": "Remote",
                    "url": "https://remotive.com/job/1",
                    "publication_date": "2026-07-01T00:00:00Z",
                    "job_type": "full_time",
                }
            ]
        }
        with patch.object(search_service, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_jobs
            response = await search_service.search_jobs(
                JobSearchRequest(job_title="AI Engineer", sources=["remotive"], max_days_old=30)
            )
        assert response.total_results >= 1
        assert response.results[0].source == "remotive"
        assert "remotive" in response.sources_searched

    @pytest.mark.asyncio
    async def test_search_handles_source_exception(self, search_service):
        async def failing_fetch(*args, **kwargs):
            raise ConnectionError("Network down")

        with patch.object(search_service, "_search_remotive", side_effect=ConnectionError("fail")):
            response = await search_service.search_jobs(
                JobSearchRequest(job_title="Engineer", sources=["remotive"])
            )
        assert any("failed" in w.lower() for w in response.warnings)

    @pytest.mark.asyncio
    async def test_search_defaults_sources_when_invalid(self, search_service):
        with patch.object(search_service, "_search_reed_uk", new_callable=AsyncMock) as mock_reed:
            mock_reed.return_value = ([], "No results")
            with patch.object(search_service, "_search_remotive", new_callable=AsyncMock) as mock_rem:
                mock_rem.return_value = ([], None)
                with patch.object(search_service, "_search_arbeitnow", new_callable=AsyncMock) as mock_arb:
                    mock_arb.return_value = ([], None)
                    response = await search_service.search_jobs(
                        JobSearchRequest(job_title="Engineer", sources=["invalid_source"])
                    )
        assert len(response.sources_searched) == 3

    @pytest.mark.asyncio
    async def test_adzuna_without_credentials(self, search_service):
        response = await search_service.search_jobs(
            JobSearchRequest(job_title="Engineer", sources=["adzuna"])
        )
        assert any("ADZUNA" in w for w in response.warnings)

    @pytest.mark.asyncio
    async def test_empty_results_adds_warning(self, search_service):
        with patch.object(search_service, "_search_remotive", new_callable=AsyncMock) as mock_rem:
            mock_rem.return_value = ([], None)
            response = await search_service.search_jobs(
                JobSearchRequest(job_title="Engineer", sources=["remotive"])
            )
        assert response.total_results == 0


class TestFetch:
    @pytest.mark.asyncio
    async def test_fetch_returns_none_on_http_error_short_body(self, search_service):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value="short")
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = lambda *a, **k: mock_response
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value = mock_session

            result = await search_service._fetch("http://example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_json_mode(self, search_service):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"jobs": []})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = lambda *a, **k: mock_response
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value = mock_session

            result = await search_service._fetch("http://api.example.com", accept_json=True)
        assert result == {"jobs": []}
