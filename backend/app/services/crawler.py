import json
import logging
import re
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.config import Settings
from app.models.schemas import JobDescriptionExtract

logger = logging.getLogger(__name__)

JS_CHALLENGE_MARKERS = (
    "enable javascript",
    "please enable cookies",
    "access denied",
    "cf-browser-verification",
)

MIN_CONTENT_TOKENS = 50
MIN_MANUAL_JOB_CHARS = 50


class JobCrawlerService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def extract_job(self, url: str, manual_description: str | None = None) -> JobDescriptionExtract:
        manual_text = (manual_description or "").strip()
        if manual_text:
            if len(manual_text) >= self._settings.min_job_content_chars:
                return await self._structure_description(manual_text, source_url=url)
            if len(manual_text) >= MIN_MANUAL_JOB_CHARS:
                structured = await self._structure_description(manual_text, source_url=url)
                if structured.extraction_confidence < 0.2:
                    structured.extraction_confidence = 0.5
                if not structured.raw_text:
                    structured.raw_text = manual_text
                return structured
            return JobDescriptionExtract(raw_text=manual_text, extraction_confidence=0.0)

        raw_text = await self._fetch_page_text(url)
        if len(raw_text.strip()) < self._settings.min_job_content_chars:
            return JobDescriptionExtract(
                raw_text=raw_text,
                extraction_confidence=0.0,
            )

        structured = await self._structure_description(raw_text, source_url=url)
        if structured.extraction_confidence < 0.3:
            structured.raw_text = raw_text
        return structured

    async def _fetch_page_text(self, url: str) -> str:
        headers = {"User-Agent": self._settings.crawl_user_agent, "Accept-Language": "en-GB,en;q=0.9"}
        timeout = aiohttp.ClientTimeout(total=self._settings.crawl_timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status >= 400:
                        logger.warning("Crawl failed for %s with status %s", url, response.status)
                        return ""
                    html = await response.text(errors="ignore")
        except aiohttp.ClientError as error:
            logger.warning("Crawl error for %s: %s", url, error)
            return ""

        if any(marker in html.lower() for marker in JS_CHALLENGE_MARKERS):
            logger.info("JS challenge detected for %s — content may be incomplete", url)
            return self._extract_visible_text(html)

        text = self._extract_visible_text(html)
        if len(text.split()) <= MIN_CONTENT_TOKENS:
            json_ld = self._extract_json_ld_job_posting(html)
            if json_ld:
                return json_ld
        return text

    def _extract_visible_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup.find("body")
        if not main:
            return ""
        text = " ".join(main.stripped_strings)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_json_ld_job_posting(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_type = item.get("@type", "")
                if item_type == "JobPosting" or "JobPosting" in str(item_type):
                    parts = [
                        item.get("title", ""),
                        item.get("description", ""),
                        str(item.get("hiringOrganization", {})),
                        str(item.get("jobLocation", {})),
                    ]
                    return " ".join(p for p in parts if p)
        return ""

    async def _structure_description(self, text: str, source_url: str = "") -> JobDescriptionExtract:
        from app.services.llm_service import LLMService

        llm = LLMService(self._settings)
        return await llm.extract_job_description(text, source_url)
