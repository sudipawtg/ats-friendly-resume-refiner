from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.models.schemas import JobListingResult
from app.services.job_search import JobSearchService


@pytest.fixture
def search_service(tmp_path):
    return JobSearchService(Settings(storage_dir=tmp_path))


class TestParseRelativeDate:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Just posted", 0),
            ("Today", 0),
            ("Just now", 0),
            ("Active today", 0),
            ("3 days ago", 3),
            ("14 days ago", 14),
            ("1 day ago", 1),
            ("", None),
            ("Posted recently", None),
        ],
    )
    def test_parse_relative_date(self, search_service, text, expected):
        assert search_service._parse_relative_date(text) == expected


class TestParseIsoDateDaysAgo:
    def test_parses_iso_date_with_time(self, search_service):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        result = search_service._parse_iso_date_days_ago(yesterday)
        assert result in (0, 1)

    def test_parses_date_only(self, search_service):
        date_str = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        result = search_service._parse_iso_date_days_ago(date_str)
        assert result == 5

    def test_returns_none_for_invalid(self, search_service):
        assert search_service._parse_iso_date_days_ago("not-a-date") is None

    def test_returns_none_for_empty(self, search_service):
        assert search_service._parse_iso_date_days_ago("") is None


class TestFilterByDate:
    def test_includes_items_within_range(self, search_service):
        results = [
            JobListingResult(id="1", title="A", url="http://a.com", source="test", posted_days_ago=3),
            JobListingResult(id="2", title="B", url="http://b.com", source="test", posted_days_ago=10),
        ]
        filtered = search_service._filter_by_date(results, 7)
        assert len(filtered) == 1
        assert filtered[0].title == "A"

    def test_includes_items_with_unknown_date(self, search_service):
        results = [
            JobListingResult(id="1", title="A", url="http://a.com", source="test", posted_days_ago=None),
        ]
        assert len(search_service._filter_by_date(results, 7)) == 1


class TestDeduplicateResults:
    def test_removes_duplicate_urls(self, search_service):
        results = [
            JobListingResult(id="1", title="A", url="https://example.com/jobs/1", source="a"),
            JobListingResult(id="2", title="B", url="https://example.com/jobs/1/", source="b"),
            JobListingResult(id="3", title="C", url="https://other.com/job", source="c"),
        ]
        deduped = search_service._deduplicate_results(results)
        assert len(deduped) == 2

    def test_skips_empty_urls(self, search_service):
        results = [
            JobListingResult(id="1", title="A", url="", source="a"),
            JobListingResult(id="2", title="B", url="https://example.com", source="b"),
        ]
        deduped = search_service._deduplicate_results(results)
        assert len(deduped) == 1


class TestNormalizeUrl:
    def test_strips_query_and_normalizes(self, search_service):
        url = "https://Example.COM/Jobs/123/?ref=abc"
        normalized = search_service._normalize_url(url)
        assert normalized == "example.com/jobs/123"

    def test_empty_url(self, search_service):
        assert search_service._normalize_url("") == ""


class TestIsJobUrl:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.linkedin.com/jobs/view/123", True),
            ("https://uk.indeed.com/viewjob?jk=abc", True),
            ("https://www.reed.co.uk/jobs/engineer/123", True),
            ("https://remotive.com/remote-jobs/software-engineer", True),
            ("https://example.com/blog/post", False),
            ("https://google.com", False),
        ],
    )
    def test_is_job_url(self, search_service, url, expected):
        assert search_service._is_job_url(url) == expected


class TestParseReedCard:
    def test_parses_valid_reed_card(self, search_service):
        from bs4 import BeautifulSoup

        html = """
        <div data-qa="job-card">
          <a data-qa="job-card-title" href="/jobs/engineer/123456">Senior AI Engineer</a>
          <a href="/jobs/engineer/123456">Link</a>
          <a href="/p99999">Acme Corp</a>
          <span data-qa="job-posted-by">2 days ago</span>
          <span data-qa="job-metadata-location">London</span>
        </div>
        """
        card = BeautifulSoup(html, "lxml").select_one("[data-qa='job-card']")
        result = search_service._parse_reed_card(card, "UK")
        assert result is not None
        assert result.title == "Senior AI Engineer"
        assert result.company == "Acme Corp"
        assert result.posted_days_ago == 2
        assert "reed.co.uk" in result.url

    def test_returns_none_for_incomplete_card(self, search_service):
        from bs4 import BeautifulSoup

        html = '<div data-qa="job-card"><span>No title</span></div>'
        card = BeautifulSoup(html, "lxml").select_one("[data-qa='job-card']")
        assert search_service._parse_reed_card(card, "UK") is None


class TestParseIndeedCard:
    def test_parses_indeed_card(self, search_service):
        from bs4 import BeautifulSoup

        html = """
        <div class="job_seen_beacon">
          <a class="jcs-JobTitle" href="/viewjob?jk=abc123">Python Developer</a>
          <span data-testid="company-name">Tech Co</span>
          <div data-testid="text-location">Manchester</div>
          <span class="date">1 day ago</span>
        </div>
        """
        card = BeautifulSoup(html, "lxml").select_one(".job_seen_beacon")
        result = search_service._parse_indeed_card(card)
        assert result is not None
        assert result.title == "Python Developer"
        assert result.company == "Tech Co"
        assert result.posted_days_ago == 1

    def test_returns_none_without_link(self, search_service):
        from bs4 import BeautifulSoup

        html = "<div class='job_seen_beacon'><span>No link</span></div>"
        card = BeautifulSoup(html, "lxml").select_one(".job_seen_beacon")
        assert search_service._parse_indeed_card(card) is None
