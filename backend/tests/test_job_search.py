import pytest
from bs4 import BeautifulSoup

from app.config import Settings
from app.models.schemas import JobListingResult, JobSearchRequest
from app.services.job_search import JobSearchService


@pytest.fixture
def search_service(tmp_path):
    return JobSearchService(Settings(storage_dir=tmp_path))


def test_parse_relative_date_today(search_service):
    assert search_service._parse_relative_date("Just posted") == 0
    assert search_service._parse_relative_date("Today") == 0


def test_parse_relative_date_days_ago(search_service):
    assert search_service._parse_relative_date("3 days ago") == 3
    assert search_service._parse_relative_date("2 days agobyNewto Training") == 2


def test_parse_iso_date_days_ago(search_service):
    days = search_service._parse_iso_date_days_ago("2026-07-02T07:39:11")
    assert days is not None
    assert days >= 0


def test_filter_by_date(search_service):
    results = [
        JobListingResult(id="1", title="A", url="https://a.com/1", source="reed_uk", posted_days_ago=2),
        JobListingResult(id="2", title="B", url="https://b.com/2", source="reed_uk", posted_days_ago=10),
        JobListingResult(id="3", title="C", url="https://c.com/3", source="reed_uk", posted_days_ago=None),
    ]
    filtered = search_service._filter_by_date(results, 7)
    assert len(filtered) == 2


def test_deduplicate_results(search_service):
    results = [
        JobListingResult(id="1", title="A", url="https://indeed.com/viewjob?jk=abc", source="indeed_uk"),
        JobListingResult(id="2", title="A dup", url="https://indeed.com/viewjob?jk=abc", source="web_search"),
        JobListingResult(id="3", title="B", url="https://reed.co.uk/jobs/123", source="reed_uk"),
    ]
    deduped = search_service._deduplicate_results(results)
    assert len(deduped) == 2


def test_parse_reed_card(search_service):
    html = """
    <div data-qa="job-card">
      <a href="/jobs/trainee-ai-engineer/57079982">Trainee AI Engineer</a>
      <span data-qa="job-card-title">Trainee AI Engineer</span>
      <span data-qa="job-posted-by">2 days agobyAcme Ltd</span>
      <span data-qa="job-metadata-location">London, UK</span>
      <a href="/jobs/acme-ltd/p90206">Acme Ltd</a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one("[data-qa='job-card']")
    listing = search_service._parse_reed_card(card, "London, UK")
    assert listing is not None
    assert listing.title == "Trainee AI Engineer"
    assert listing.posted_days_ago == 2
    assert "57079982" in listing.url


@pytest.mark.asyncio
async def test_search_jobs_with_mocked_sources(search_service, monkeypatch):
    async def mock_reed(*_args):
        return [
            JobListingResult(
                id="1",
                title="AI Engineer",
                company="Test Co",
                url="https://www.reed.co.uk/jobs/ai-engineer/123",
                source="reed_uk",
                source_label="Reed.co.uk",
                posted_days_ago=1,
            )
        ], None

    async def mock_remotive(*_args):
        return [], None

    monkeypatch.setattr(search_service, "_search_reed_uk", mock_reed)
    monkeypatch.setattr(search_service, "_search_remotive", mock_remotive)

    response = await search_service.search_jobs(
        JobSearchRequest(job_title="AI Engineer", sources=["reed_uk", "remotive"], max_days_old=7)
    )
    assert response.total_results == 1
    assert response.results[0].title == "AI Engineer"


@pytest.mark.asyncio
async def test_live_reed_search(search_service):
    """Integration test — hits Reed.co.uk if network available."""
    results, warning = await search_service._search_reed_uk("AI Engineer", "London, UK", 7, 5)
    if warning and not results:
        pytest.skip(warning)
    assert len(results) >= 1
    assert results[0].url.startswith("https://")
    assert len(results[0].title) > 3
