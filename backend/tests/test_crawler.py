import pytest

from app.config import Settings
from app.services.crawler import JobCrawlerService
from tests.conftest import SAMPLE_JOB_DESCRIPTION


@pytest.fixture
def crawler(tmp_path):
    return JobCrawlerService(Settings(storage_dir=tmp_path, min_job_content_chars=200))


class TestExtractVisibleText:
    def test_extracts_main_content(self, crawler):
        html = """
        <html><body>
        <nav>Skip this nav</nav>
        <main><h1>Senior AI Engineer</h1><p>Python and AWS required.</p></main>
        <footer>Footer text</footer>
        </body></html>
        """
        text = crawler._extract_visible_text(html)
        assert "Senior AI Engineer" in text
        assert "Python and AWS required" in text
        assert "Skip this nav" not in text
        assert "Footer text" not in text

    def test_returns_empty_for_no_body(self, crawler):
        assert crawler._extract_visible_text("<html></html>") == ""

    def test_strips_scripts_and_styles(self, crawler):
        html = """
        <html><body>
        <script>alert('x')</script>
        <style>.hidden{}</style>
        <p>Visible job description content here.</p>
        </body></html>
        """
        text = crawler._extract_visible_text(html)
        assert "alert" not in text
        assert "Visible job description" in text


class TestExtractJsonLdJobPosting:
    def test_extracts_job_posting_json_ld(self, crawler):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "JobPosting", "title": "ML Engineer", "description": "Build models"}
        </script>
        </head><body></body></html>
        """
        text = crawler._extract_json_ld_job_posting(html)
        assert "ML Engineer" in text
        assert "Build models" in text

    def test_handles_array_json_ld(self, crawler):
        html = """
        <script type="application/ld+json">
        [{"@type": "Organization", "name": "Acme"},
         {"@type": "JobPosting", "title": "Data Scientist", "description": "Analyze data"}]
        </script>
        """
        text = crawler._extract_json_ld_job_posting(html)
        assert "Data Scientist" in text

    def test_returns_empty_for_invalid_json(self, crawler):
        html = '<script type="application/ld+json">not valid json</script>'
        assert crawler._extract_json_ld_job_posting(html) == ""

    def test_returns_empty_when_no_job_posting(self, crawler):
        html = '<script type="application/ld+json">{"@type": "Organization"}</script>'
        assert crawler._extract_json_ld_job_posting(html) == ""


class TestExtractJob:
    @pytest.mark.asyncio
    async def test_manual_description_above_threshold(self, crawler):
        result = await crawler.extract_job("", SAMPLE_JOB_DESCRIPTION)
        assert result.extraction_confidence >= 0.2
        assert len(result.raw_text) > 0

    @pytest.mark.asyncio
    async def test_short_manual_description_returns_low_confidence(self, crawler):
        result = await crawler.extract_job("http://example.com", "Too short")
        assert result.extraction_confidence == 0.0
        assert result.raw_text == "Too short"

    @pytest.mark.asyncio
    async def test_medium_manual_description_is_accepted(self, crawler):
        manual_text = (
            "Senior AI Engineer role requiring Python, LLM, RAG, and AWS experience "
            "building production ML systems."
        )
        result = await crawler.extract_job("", manual_text)
        assert result.extraction_confidence >= 0.2
        assert manual_text in result.raw_text or len(result.raw_text) > 0

    @pytest.mark.asyncio
    async def test_empty_url_returns_low_confidence(self, crawler):
        result = await crawler.extract_job("", None)
        assert result.extraction_confidence == 0.0

    @pytest.mark.asyncio
    async def test_whitespace_only_manual_ignored(self, crawler):
        result = await crawler.extract_job("http://invalid.test", "   ")
        assert result.extraction_confidence == 0.0
