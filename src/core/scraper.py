import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import markdownify
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors."""

    pass


class Scraper:
    """Enhanced web scraper with improved metadata handling, markdown processing, smart wait/actions, JS rendering, and proxy support."""

    def __init__(self):
        self._session = None
        self._session_kwargs = {}
        self.ua = UserAgent()
        self.default_headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Create or reuse aiohttp session with random user agent."""
        if self._session is None:
            headers = {**self.default_headers, "User-Agent": self.ua.random}
            self._session = aiohttp.ClientSession(headers=headers, **self._session_kwargs)
        return self._session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None

    def _clean_markdown(self, markdown: str) -> str:
        """Enhanced markdown clearning for LLM-ready output."""
        # Remove extra whitespace and normalize line endings
        markdown = re.sub(r"\r\n?", "\n", markdown)
        markdown = re.sub(r"[ \t]+$", "", markdown, flags=re.MULTILINE)

        # Fix headers
        markdown = re.sub(r"^(#+)\s*(.+?)[\s#]*$", r"\1 \2", markdown, flags=re.MULTILINE)

        # Fix quotes
        markdown = re.sub(r'^"(.+?)"$', r"> \1", markdown, flags=re.MULTILINE)
        markdown = re.sub(r"^by\s+(.+?)\s*$", r"By \1", markdown, flags=re.MULTILINE)

        # Fix lists
        markdown = re.sub(r"^\s*[-*+]\s*(.+)$", r"- \1", markdown, flags=re.MULTILINE)

        # Fix links
        markdown = re.sub(r"\[(.*?)\]\(([^)]+)\)", lambda m: f"[{m.group(1).strip()}]({m.group(2).strip()})", markdown)

        # Fix spacing around sections
        sections = markdown.split("\n\n")
        cleaned_sections = []
        for section in sections:
            if section.strip():
                lines = [line.strip() for line in section.split("\n") if line.strip()]

                # Special handling for quotes and attributions
                if any(line.startswith(">") for line in lines):
                    quote_lines = []
                    for line in lines:
                        if line.startswith(">"):
                            quote_lines.append(line)
                        elif line.startswith("By "):
                            quote_lines.append("\n" + line)
                        else:
                            quote_lines.append(line)
                    cleaned_sections.append("\n".join(quote_lines))
                else:
                    cleaned_sections.append("\n".join(lines))

        # Join cleaned sections with double newlines
        markdown = "\n\n".join(cleaned_sections)

        # Final cleanup
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = markdown.strip()

        return markdown

    def _extract_metadata(self, soup: BeautifulSoup, url: str, final_url: str, status: int) -> Dict[str, Any]:
        """Comprehensive metadata extraction with improve URL handling."""
        metadata = {
            "title": "",
            "description": "",
            "language": "",
            "cannonical": "",
            "final_url": final_url,
            "source_url": url,
            "status": status,
            "headers": {},
            "og_data": {},
            "twitter_data": {},
            "schema_org": {},
            "page_type": "unknown",
            "content_type": "text/html",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            base_tag = soup.find("base", href=True)
            base_url = urljoin(final_url, base_tag["href"]) if base_tag else final_url

            title_tag = soup.find("title")
            metadata["title"] = title_tag.get_text(strip=True) if title_tag else ""

            html_tag = soup.find("html")
            metadata["language"] = html_tag.get("lang", "").lower()[:5] if html_tag else ""

            description_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
            metadata["description"] = description_tag.get("content", "").strip() if description_tag else ""

            keywords_meta = soup.find("meta", attrs={"name": re.compile(r"keywords", re.I)})
            if keywords_meta:
                metadata["keywords"] = keywords_meta.get("content", "").strip()

            viewport_meta = soup.find("meta", attrs={"name": re.compile(r"viewport", re.I)})
            if viewport_meta:
                metadata["viewport"] = viewport_meta.get("content", "").strip()

            canonical = soup.find("link", rel="canonical")
            if canonical and canonical.get("href"):
                metadata["cannonical"] = urljoin(base_url, canonical["href"])

            open_graph_props = soup.find_all("meta", property=re.compile(r"og:", re.I))
            for prop in open_graph_props:
                key = prop["property"][3:].lower()
                metadata["og_data"][key] = prop.get("content", "").strip()
                if key == "type":
                    metadata["page_type"] = prop.get("content", "").strip()

            twitter_meta = soup.find_all("meta", attrs={"name": re.compile(r"twitter:", re.I)})
            for meta in twitter_meta:
                key = meta["name"][8:].lower()
                metadata["twitter_data"][key] = meta.get("content", "").strip()

            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        metadata["schema_org"] = data
                        break
                    elif isinstance(data, list) and len(data) > 0:
                        metadata["schema_org"] = data[0]
                        break
                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")

        return metadata

    async def _fetch_url(self, url: str, max_retries: int = 3, proxy: Optional[str] = None) -> tuple[str, str, int]:
        """Fetch URL with retry logic and proper redirect handling using aiohttp."""
        session = await self._get_session()
        for attempt in range(max_retries):
            try:
                async with session.get(
                    url, allow_redirects=True, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    content = await response.text()
                    return content, str(response.url), response.status
            except (aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError) as e:
                if attempt == max_retries - 1:
                    raise ScraperError(f"Connection error after {max_retries} attempts: {str(e)}")
                await asyncio.sleep(2**attempt)  # Exponential backoff
            except aiohttp.ClientError as e:
                raise ScraperError(f"Client error: {str(e)}")
        raise ScraperError(f"Failed to fetch {url} after {max_retries} attempts")

    async def _fetch_url_browser(self, url: str, page_options: Dict) -> tuple[str, str, int]:
        """
        Fetch URL using Playwright for JavaScript rendering, smart wait, and actions.
        Expects page_options to potentially include:
            - 'wait_for': miliseconds to wait after page load
            - 'actions': list of actions (dicts) with types: wait, click, scroll, write, press
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.ua.random)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")

            if page_options.get("wait_for"):
                await page.wait_for_timeout(page_options["wait_for"])

            actions = page_options.get("actions", [])
            for action in actions:
                action_type = action.get("type")
                if action_type == "wait":
                    ms = action.get("milliseconds", 1000)
                    await page.wait_for_timeout(ms)
                elif action_type == "click":
                    selector = action.get("selector")
                    if selector:
                        await page.click(selector)
                elif action_type == "scroll":
                    pixels = action.get("pixels", 1000)
                    await page.evaluate(f"window.scrollBy(0, {pixels});")
                elif action_type == "write":
                    text = action.get("text", "")
                    selector = action.get("selector")
                    if selector:
                        await page.fill(selector, text)
                elif action_type == "press":
                    key = action.get("key")
                    if key:
                        await page.keyboard.press(key)
        if page_options.get("post_action_wait"):
            await page.wait_for_timeout(page_options["post_action_wait"])

        content = await page.content()
        final_url = page.url
        status = 200
        await browser.close()
        return content, final_url, status

    def _generate_formats(self, soup: BeautifulSoup, formats: List[str], page_options: Dict) -> Dict[str, Any]:
        """Generate content in requested formats with improved HTML processing."""
        result = {}
        processed_html = str(soup)

        if "markdown" in formats:
            markdown = markdownify.markdownify(
                processed_html, heading_style="ATX", bullets=["•", "◦", "▪"], default_title=False
            )
            if page_options.get("clean_markdown", True):
                markdown = self._clean_markdown(markdown)
            result["markdown"] = markdown
        if "html" in formats:
            result["html"] = processed_html

        if "text" in formats:
            text = soup.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            result["text"] = text.strip()

        return result

    async def scrape(self, url: str, formats: List[str] = None, page_options: Dict = None) -> Dict[str, Any]:
        """Enhanced scraping method with improved content selection, JS rendering, and structured JSON output."""
        formats = formats or ["markdown"]
        page_options = page_options or {}
        result = {
            "error": None,
            "metadata": {
                "title": "",
                "description": "",
                "language": "",
                "source_url": url,
                "status": None,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            },
            "content": {},
            "links": [],
        }

        try:
            logger.debug(f"Starting scrape of {url} with formats: {formats}")
            logger.debug(f"Page options: {page_options}")

            use_browser = page_options.get("use_browser", False)
            proxy = page_options.get("proxy") if not use_browser else None

            try:
                if use_browser:
                    logger.debug("Starting browser fetch")
                    content, final_url, status = await self._fetch_url_browser(url, page_options)
                else:
                    logger.debug("Starting direct fetch")
                    content, final_url, status = await self._fetch_url(
                        url, max_retries=page_options.get("max_retries", 3), proxy=proxy
                    )

                result["metadata"]["status"] = status
                result["metadata"]["final_url"] = final_url

                if not content:
                    raise ScraperError("No content retrieved from the URL.")

                soup = BeautifulSoup(content, "lxml")

                for tag in page_options.get("exclude_tags", ["script", "style", "noscript"]):
                    for element in soup.find_all(tag):
                        element.decompose()

                if page_options.get("extract_main_content"):
                    css_selector = page_options.get("main_content_selector", "main, article, .main-content")
                    main_content = soup.select_one(css_selector)
                    if main_content:
                        soup = BeautifulSoup(main_content, "lxml")
                    else:
                        body = soup.find("body")
                        if body:
                            soup = BeautifulSoup(str(body), "lxml")

                metadata = self._extract_metadata(soup, url, final_url, status)
                result["metadata"].update(metadata)

                content_formats = self._generate_formats(soup, formats, page_options)
                if not content_formats:
                    raise ScraperError("Failed to generate content formats")
                result["content"] = content_formats

                if page_options.get("include_links"):
                    for link in soup.find_all("a", href=True):
                        absolute_url = urljoin(final_url, link["href"])
                        result["links"].append(
                            {
                                "text": link.get_text(strip=True),
                                "url": absolute_url,
                                "nofollow": "nofollow" in link.get("rel", []),
                            }
                        )

                result["json"] = {"metadata": result["metadata"], "content": result["content"]}
            except Exception as e:
                logger.error(f"Content processing error: {str(e)}")
                result["metadata"]["error"] = f"Content processing failed: {str(e)}"
                result["content"] = {}
                return result

            return result
        except ScraperError as e:
            error_msg = str(e)
            logger.error(error_msg)
            result["error"] = error_msg
            return result

        except Exception as e:
            error_msg = f"Scraping failed for {url}: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
            result["metadata"] = {
                "source_url": url,
                "status": "failed",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
            return result

    async def scrape_batch(
        self, urls: List[str], formats: List[str] = None, page_options: Dict = None, concurrency: int = 5
    ) -> Dict[str, dict]:
        """Batch scraping with improved concurrency control."""
        results = {}
        semaphore = asyncio.Semaphore(concurrency)

        async def _scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape(url, formats, page_options)

        tasks = [_scrape_with_semaphore(url) for url in urls]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for url, result in zip(urls, batch_results):
            if isinstance(result, Exception):
                results[url] = {"error": str(result), "metadata": {"source_url": url}}
            else:
                results[url] = result

        return results
