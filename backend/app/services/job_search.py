import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus, unquote, urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.config import Settings
from app.constants import JOB_SEARCH_SOURCES
from app.models.schemas import JobListingResult, JobSearchRequest, JobSearchResponse

logger = logging.getLogger(__name__)

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

RELATIVE_DATE_PATTERN = re.compile(
    r"(\d+)\s*(?:day|days)\s*ago|just\s*posted|today|just\s*now",
    re.IGNORECASE,
)

REED_JOB_LINK_PATTERN = re.compile(r"^/jobs/[^/]+/\d+(?:\?|$)")
REED_COMPANY_LINK_PATTERN = re.compile(r"/p\d+")

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


class JobSearchService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search_jobs(self, request: JobSearchRequest) -> JobSearchResponse:
        handlers = {
            "indeed_uk": self._search_indeed_uk,
            "reed_uk": self._search_reed_uk,
            "totaljobs": self._search_totaljobs,
            "cv_library": self._search_cv_library,
            "remotive": self._search_remotive,
            "arbeitnow": self._search_arbeitnow,
            "adzuna": self._search_adzuna,
            "web_search": self._search_web,
        }

        selected_sources = [source for source in request.sources if source in handlers]
        if not selected_sources:
            selected_sources = ["reed_uk", "remotive", "arbeitnow"]

        warnings: list[str] = []
        all_results: list[JobListingResult] = []

        tasks = [
            handlers[source](
                request.job_title,
                request.location,
                request.max_days_old,
                request.max_results_per_source,
            )
            for source in selected_sources
        ]
        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        for source, result in zip(selected_sources, source_results):
            if isinstance(result, Exception):
                logger.warning("Job search failed for %s: %s", source, result)
                warnings.append(f"{JOB_SEARCH_SOURCES.get(source, source)}: search failed")
                continue
            listings, source_warning = result
            if source_warning:
                warnings.append(source_warning)
            all_results.extend(listings)

        deduped = self._deduplicate_results(all_results)
        filtered = self._filter_by_date(deduped, request.max_days_old)
        sorted_results = sorted(
            filtered,
            key=lambda item: (
                item.posted_days_ago if item.posted_days_ago is not None else 999,
                item.title.lower(),
            ),
        )

        if not sorted_results and not warnings:
            warnings.append("No jobs found. Try a broader title or extend the date range.")

        return JobSearchResponse(
            query=request.job_title,
            location=request.location,
            max_days_old=request.max_days_old,
            total_results=len(sorted_results),
            results=sorted_results,
            sources_searched=selected_sources,
            warnings=warnings,
        )

    async def _fetch(
        self,
        url: str,
        accept_json: bool = False,
    ) -> str | dict | None:
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept": "application/json, text/html" if accept_json else "text/html,application/xhtml+xml",
        }
        timeout = aiohttp.ClientTimeout(total=self._settings.crawl_timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status >= 400:
                        logger.warning("HTTP %s for %s", response.status, url)
                        if accept_json:
                            return None
                        text = await response.text(errors="ignore")
                        return text if len(text) > 1000 else None
                    if accept_json:
                        return await response.json(content_type=None)
                    return await response.text(errors="ignore")
        except (aiohttp.ClientError, json.JSONDecodeError) as error:
            logger.warning("Fetch failed for %s: %s", url, error)
            return None

    async def _search_reed_uk(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        slug = quote_plus(job_title.lower().replace(" ", "-"))
        city = quote_plus(location.split(",")[0].strip().lower())
        url = f"https://www.reed.co.uk/jobs/{slug}-jobs-in-{city}"
        html = await self._fetch(url)
        if not html or not isinstance(html, str):
            return [], "Reed.co.uk: could not fetch results"

        soup = BeautifulSoup(html, "lxml")
        results: list[JobListingResult] = []

        for card in soup.select("[data-qa='job-card']"):
            listing = self._parse_reed_card(card, location)
            if listing:
                results.append(listing)
            if len(results) >= max_results:
                break

        if not results:
            return [], "Reed.co.uk: no listings matched (page structure may have changed)"

        return results, None

    def _parse_reed_card(self, card, default_location: str) -> JobListingResult | None:
        title_el = card.select_one("[data-qa='job-card-title']")
        title = title_el.get_text(strip=True) if title_el else ""

        job_link = None
        for anchor in card.find_all("a", href=True):
            href = anchor.get("href", "").split("?")[0]
            if REED_COMPANY_LINK_PATTERN.search(href):
                continue
            if REED_JOB_LINK_PATTERN.match(href):
                job_link = anchor
                break

        if not job_link:
            for anchor in card.find_all("a", href=True):
                href = anchor.get("href", "").split("?")[0]
                if REED_COMPANY_LINK_PATTERN.search(href):
                    continue
                if "/jobs/" in href and re.search(r"/\d+$", href):
                    job_link = anchor
                    break

        if not job_link or not title:
            return None

        href = job_link.get("href", "")
        if href.startswith("/"):
            href = urljoin("https://www.reed.co.uk", href)

        posted_el = card.select_one("[data-qa='job-posted-by']")
        posted_text = posted_el.get_text(strip=True) if posted_el else ""
        days_ago = self._parse_relative_date(posted_text)

        location_el = card.select_one("[data-qa='job-metadata-location']")
        job_location = location_el.get_text(strip=True) if location_el else default_location

        company = ""
        for anchor in card.find_all("a", href=True):
            company_href = anchor.get("href", "")
            if REED_COMPANY_LINK_PATTERN.search(company_href):
                company = anchor.get_text(strip=True)
                break

        return JobListingResult(
            id=str(uuid.uuid4()),
            title=title,
            company=company,
            location=job_location,
            url=href,
            source="reed_uk",
            source_label=JOB_SEARCH_SOURCES["reed_uk"],
            posted_date=posted_text,
            posted_days_ago=days_ago,
            snippet=f"{company} · {job_location}".strip(" · "),
        )

    async def _search_remotive(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        query = quote_plus(job_title)
        url = f"https://remotive.com/api/remote-jobs?search={query}&limit={max_results}"
        data = await self._fetch(url, accept_json=True)
        if not data or not isinstance(data, dict):
            return [], "Remotive: could not fetch API results"

        results: list[JobListingResult] = []
        title_keywords = [word.lower() for word in job_title.split() if len(word) > 2]

        for job in data.get("jobs", []):
            title = job.get("title", "")
            if title_keywords and not any(kw in title.lower() for kw in title_keywords):
                continue

            pub_date = job.get("publication_date", "")
            days_ago = self._parse_iso_date_days_ago(pub_date)

            results.append(
                JobListingResult(
                    id=str(uuid.uuid4()),
                    title=title,
                    company=job.get("company_name", ""),
                    location=job.get("candidate_required_location", "Remote"),
                    url=job.get("url", ""),
                    source="remotive",
                    source_label=JOB_SEARCH_SOURCES["remotive"],
                    posted_date=pub_date[:10] if pub_date else "",
                    posted_days_ago=days_ago,
                    snippet=job.get("job_type", "Remote"),
                )
            )
            if len(results) >= max_results:
                break

        return results, None

    async def _search_arbeitnow(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        data = await self._fetch(url, accept_json=True)
        if not data or not isinstance(data, dict):
            return [], "Arbeitnow: could not fetch API results"

        results: list[JobListingResult] = []
        title_keywords = [word.lower() for word in job_title.split() if len(word) > 2]
        location_lower = location.lower()

        for job in data.get("data", []):
            title = job.get("title", "")
            if title_keywords and not any(kw in title.lower() for kw in title_keywords):
                continue

            job_location = job.get("location", "")
            if location_lower and location_lower not in job_location.lower() and "remote" not in job_location.lower():
                if "uk" in location_lower or "london" in location_lower:
                    if "uk" not in job_location.lower() and "london" not in job_location.lower() and "remote" not in job_location.lower():
                        continue

            created_at = job.get("created_at", "")
            days_ago = self._parse_iso_date_days_ago(str(created_at))
            slug = job.get("slug", "")
            job_url = f"https://www.arbeitnow.com/jobs/{slug}" if slug else ""

            results.append(
                JobListingResult(
                    id=str(uuid.uuid4()),
                    title=title,
                    company=job.get("company_name", ""),
                    location=job_location,
                    url=job_url,
                    source="arbeitnow",
                    source_label=JOB_SEARCH_SOURCES["arbeitnow"],
                    posted_date=str(created_at)[:10],
                    posted_days_ago=days_ago,
                    snippet=job.get("tags", [""])[0] if job.get("tags") else "",
                )
            )
            if len(results) >= max_results:
                break

        return results, None

    async def _search_adzuna(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        app_id = getattr(self._settings, "adzuna_app_id", "") or ""
        app_key = getattr(self._settings, "adzuna_app_key", "") or ""
        if not app_id or not app_key:
            return [], "Adzuna: set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env for this source"

        query = quote_plus(job_title)
        loc = quote_plus(location.split(",")[0])
        url = (
            f"https://api.adzuna.com/v1/api/jobs/gb/search/1"
            f"?app_id={app_id}&app_key={app_key}"
            f"&results_per_page={max_results}&what={query}&where={loc}&max_days_old={max_days}"
        )
        data = await self._fetch(url, accept_json=True)
        if not data or not isinstance(data, dict):
            return [], "Adzuna: API request failed"

        results: list[JobListingResult] = []
        for job in data.get("results", []):
            created = job.get("created", "")
            days_ago = self._parse_iso_date_days_ago(created)
            results.append(
                JobListingResult(
                    id=str(uuid.uuid4()),
                    title=job.get("title", ""),
                    company=job.get("company", {}).get("display_name", ""),
                    location=job.get("location", {}).get("display_name", location),
                    url=job.get("redirect_url", ""),
                    source="adzuna",
                    source_label=JOB_SEARCH_SOURCES["adzuna"],
                    posted_date=str(created)[:10],
                    posted_days_ago=days_ago,
                    snippet=job.get("description", "")[:150],
                )
            )

        return results, None

    async def _search_indeed_uk(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        fromage = min(max_days, 30)
        query = quote_plus(job_title)
        loc = quote_plus(location)
        url = f"https://uk.indeed.com/jobs?q={query}&l={loc}&fromage={fromage}&sort=date"
        html = await self._fetch(url)
        if not html or not isinstance(html, str):
            return [], "Indeed UK: blocked by anti-bot protection — try Reed or Remotive"

        soup = BeautifulSoup(html, "lxml")
        results: list[JobListingResult] = []

        for card in soup.select("div.job_seen_beacon, div.jobsearch-SerpJobCard, li div.cardOutline"):
            listing = self._parse_indeed_card(card)
            if listing:
                results.append(listing)
            if len(results) >= max_results:
                break

        if not results:
            return [], "Indeed UK: blocked or no results — try Reed or Remotive sources"

        return results, None

    def _parse_indeed_card(self, card) -> JobListingResult | None:
        link = card.select_one("a.jcs-JobTitle, a[data-jk], h2.jobTitle a, a[href*='viewjob']")
        if not link:
            return None

        title = link.get_text(strip=True)
        href = link.get("href", "")
        if href.startswith("/"):
            href = urljoin("https://uk.indeed.com", href)

        company_el = card.select_one("[data-testid='company-name'], span.companyName")
        company = company_el.get_text(strip=True) if company_el else ""

        location_el = card.select_one("[data-testid='text-location'], div.companyLocation")
        job_location = location_el.get_text(strip=True) if location_el else ""

        date_el = card.select_one("span.date, span[data-testid='myJobsStateDate']")
        date_text = date_el.get_text(strip=True) if date_el else ""

        return JobListingResult(
            id=str(uuid.uuid4()),
            title=title,
            company=company,
            location=job_location,
            url=href,
            source="indeed_uk",
            source_label=JOB_SEARCH_SOURCES["indeed_uk"],
            posted_date=date_text,
            posted_days_ago=self._parse_relative_date(date_text),
            snippet=f"{company} · {job_location}".strip(" · "),
        )

    async def _search_totaljobs(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        query = quote_plus(job_title)
        loc = quote_plus(location)
        url = f"https://www.totaljobs.com/jobs/{query}?postedWithin={max_days}&location={loc}"
        html = await self._fetch(url)
        if not html or not isinstance(html, str):
            return [], "Totaljobs: could not fetch results"

        soup = BeautifulSoup(html, "lxml")
        results: list[JobListingResult] = []

        for item in soup.select("article[data-at='job-item'], div[data-job-id]"):
            link = item.select_one("a[href*='/job/']")
            if not link:
                continue
            href = link.get("href", "")
            if href.startswith("/"):
                href = urljoin("https://www.totaljobs.com", href)

            company_el = item.select_one("[data-at='job-item-company-name']")
            date_el = item.select_one("[data-at='job-item-posted-date']")

            results.append(
                JobListingResult(
                    id=str(uuid.uuid4()),
                    title=link.get_text(strip=True),
                    company=company_el.get_text(strip=True) if company_el else "",
                    location=location,
                    url=href,
                    source="totaljobs",
                    source_label=JOB_SEARCH_SOURCES["totaljobs"],
                    posted_date=date_el.get_text(strip=True) if date_el else "",
                    posted_days_ago=self._parse_relative_date(date_el.get_text(strip=True) if date_el else ""),
                    snippet="",
                )
            )
            if len(results) >= max_results:
                break

        return results, None if results else ("Totaljobs: no listings found",)

    async def _search_cv_library(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        query = quote_plus(job_title)
        url = f"https://www.cv-library.co.uk/search-jobs?kw={query}&geo={quote_plus(location)}"
        html = await self._fetch(url)
        if not html or not isinstance(html, str):
            return [], "CV-Library: could not fetch results"

        soup = BeautifulSoup(html, "lxml")
        results: list[JobListingResult] = []

        for row in soup.select("article.job-search-card, div.results-item"):
            link = row.select_one("a[href*='/job/']")
            if not link:
                continue
            href = link.get("href", "")
            if href.startswith("/"):
                href = urljoin("https://www.cv-library.co.uk", href)

            results.append(
                JobListingResult(
                    id=str(uuid.uuid4()),
                    title=link.get_text(strip=True),
                    company="",
                    location=location,
                    url=href,
                    source="cv_library",
                    source_label=JOB_SEARCH_SOURCES["cv_library"],
                    posted_date="",
                    posted_days_ago=None,
                    snippet="",
                )
            )
            if len(results) >= max_results:
                break

        return results, None if results else ("CV-Library: no listings found",)

    async def _search_web(
        self, job_title: str, location: str, max_days: int, max_results: int
    ) -> tuple[list[JobListingResult], str | None]:
        query = quote_plus(f"{job_title} jobs {location}")
        url = f"https://html.duckduckgo.com/html/?q={query}"
        html = await self._fetch(url)
        if not html or not isinstance(html, str):
            return [], "Web search: could not fetch results"

        soup = BeautifulSoup(html, "lxml")
        results: list[JobListingResult] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            if "uddg=" not in href:
                continue
            match = re.search(r"uddg=([^&]+)", href)
            if not match:
                continue
            decoded = unquote(match.group(1))
            if not self._is_job_url(decoded):
                continue
            if "duckduckgo.com/y.js" in decoded:
                continue

            title = anchor.get_text(strip=True)
            if len(title) < 5:
                continue

            results.append(
                JobListingResult(
                    id=str(uuid.uuid4()),
                    title=title,
                    company="",
                    location=location,
                    url=decoded,
                    source="web_search",
                    source_label=JOB_SEARCH_SOURCES["web_search"],
                    posted_date="",
                    posted_days_ago=None,
                    snippet="",
                )
            )
            if len(results) >= max_results:
                break

        return results, None if results else ("Web search: no job URLs found in results",)

    def _parse_relative_date(self, text: str) -> int | None:
        if not text:
            return None
        lowered = text.lower().strip()
        if any(token in lowered for token in ("just posted", "today", "just now", "active today")):
            return 0
        match = RELATIVE_DATE_PATTERN.search(lowered)
        if match and match.group(1):
            return int(match.group(1))
        if match:
            return 0
        return None

    def _parse_iso_date_days_ago(self, date_str: str) -> int | None:
        if not date_str:
            return None
        try:
            if "T" in date_str:
                posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                posted = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - posted.astimezone(timezone.utc)
            return max(0, delta.days)
        except ValueError:
            return None

    def _filter_by_date(self, results: list[JobListingResult], max_days: int) -> list[JobListingResult]:
        filtered: list[JobListingResult] = []
        for item in results:
            if item.posted_days_ago is None:
                filtered.append(item)
                continue
            if item.posted_days_ago <= max_days:
                filtered.append(item)
        return filtered

    def _deduplicate_results(self, results: list[JobListingResult]) -> list[JobListingResult]:
        seen_urls: set[str] = set()
        deduped: list[JobListingResult] = []
        for item in results:
            normalized = self._normalize_url(item.url)
            if not normalized or normalized in seen_urls:
                continue
            seen_urls.add(normalized)
            deduped.append(item)
        return deduped

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        return f"{parsed.netloc}{parsed.path}".lower().rstrip("/")

    def _is_job_url(self, url: str) -> bool:
        job_indicators = (
            "linkedin.com/jobs",
            "indeed.com",
            "glassdoor.",
            "jobs.lever.co",
            "greenhouse.io",
            "myworkdayjobs.com",
            "careers.",
            "reed.co.uk/jobs/",
            "totaljobs.com",
            "cv-library.co.uk",
            "remotive.com/remote-jobs/",
            "arbeitnow.com/jobs/",
        )
        return any(indicator in url.lower() for indicator in job_indicators)
