import logging
from datetime import datetime
from typing import Any, Dict, List, Set
from urllib.parse import urljoin, urlparse

from .scraper import Scraper

logger = logging.getLogger(__name__)


class Crawler:
    """Web crawler with configurable options and job tracking."""

    def __init__(self):
        """Initialize the Crawler."""
        self.visited: Set[str] = set()
        self.queue: Set[str] = set()

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        """Exit the async context manager."""
        pass

    def _is_same_domain(
        self, url1: str, url2: str, include_subdomains: bool = False
    ) -> bool:
        """Check if two URLs belong to the same domain."""
        print("i'm here 3")
        parsed1 = urlparse(url1)
        parsed2 = urlparse(url2)
        if include_subdomains:
            domain1 = ".".join(parsed1.netloc.split(".")[-2:])
            domain2 = ".".join(parsed2.netloc.split(".")[-2:])
            return domain1 == domain2

        return parsed1.netloc == parsed2.netloc

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL by removing fragments and trailing slashes."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}{'?' + parsed.query if parsed.query else ''}"

    def _should_crawl(self, url: str, base_url: str, options: Dict) -> bool:
        """
        Check if a URL should be crawled based on options.

        Args:
            url: URL to check.
            base_url: Original starting URL.
            options: Crawling options including:
                - max_pages: Maximum number of pages to crawl
                - exclude_paths: Lis of path patterns to exclude
                - include_only_paths: List of path patterns to include
                - include_backwards: Allow crawling to parent directories
                - include_subdomains: Allow crawling to subdomains
        """
        if not url or not url.startswith(("http://", "https://")):
            return False
        include_subdomains = options.get("include_subdomains", False)
        if not options.get("allow_backwards", False) and not self._is_same_domain(
            url, base_url, include_subdomains
        ):
            return False

        normalized = self._normalize_url(url)
        if normalized in self.visited:
            return False

        if options.get("max_pages") and len(self.visited) >= options["max_pages"]:
            return False

        path = urlparse(normalized).path

        if any(
            p in path.lower()
            for p in [
                "/cdn-cgi/",
                "/wp-admin/",
                "/wp-includes/",
                "/assets/",
                "/static/",
            ]
        ):
            return False

        if options.get("exclude_paths"):
            for pattern in options["exclude_paths"]:
                if pattern.endswith("*"):
                    if path.startswith(pattern[:-1]):
                        return False
                elif path == pattern:
                    return False

        if options.get("include_only_paths"):
            matched = False
            for pattern in options["include_only_paths"]:
                if pattern.endswith("*"):
                    if path.startswith(pattern[:-1]):
                        matched = True
                        break
                elif path == pattern:
                    matched = True
                    break
            if not matched:
                return False

        return True

    async def map(self, url: str, options: Dict = None) -> List[str]:
        """
        Map all URLs on a domain.

        Args:
            url: The starting URL
            options: Mapping options including:
                - max_pages: Maximum number of pages to map
                - exclude_paths: List of path pattern to exclude
                - include_only_paths: List of path patterns to include
                - allow_backwards: Allow mapping parent directories
                - search: Optional search term to filter URLs
        Returns:
            List of discovered URLs
        """
        options = options or {}
        self.visited.clear()
        self.queue.clear()

        async with Scraper() as scraper:
            result = await scraper.scrape(
                url=url,
                formats=["markdown"],
                page_options=options.get(
                    "page_options", {"include_links": True, "structured_json": True}
                ),
            )

            if result.get("error"):
                raise Exception(result["error"])

            urls = {url}
            if result.get("links"):
                for link in result["links"]:
                    normalized = self._normalize_url(urljoin(url, link["url"]))
                    if self._should_crawl(normalized, url, options):
                        urls.add(normalized)

            if options.get("search"):
                urls = {u for u in urls if options["search"].lower() in u.lower()}

            if options.get("max_pages"):
                urls = set(list(urls)[: options["max_pages"]])

            return sorted(list(urls))

    async def crawl(self, url: str, options: Dict = None) -> Dict[str, Any]:
        """
        Crawl a website starting from URL.

        Args:
            url: The starting URL
            options: Crawling options including:
                - max_pages: Maximum link depth to crawl
                - max_pages: Maximum number of page"Crawling failed: slice indices must be integers or None or have an __index__ method"s to crawl
                - formats: List of output formats
                - page_options: Options for page processing
                - exclude_paths: List of path patterns to include
                - include_only_paths: List of path patterns to include
                - allow_backwards: Allow crawling to parent directories

        Returns:
            Dictionary containing the crawled pages and metadata.
        """
        options = options or {}
        max_depth = options.get("max_depth")
        if max_depth is None:
            max_depth = float("inf")
        elif not isinstance(max_depth, (int, float)) or max_depth < 0:
            raise ValueError("max_depth must be a non-negative number")

        max_pages = options.get("max_pages")
        if max_pages is not None:
            if not isinstance(max_pages, int) or max_pages < 1:
                raise ValueError("max_pages must be a positive integer")

        self.visited.clear()
        self.queue.clear()
        self.queue.add(url)

        results = {
            "pages": {},
            "metadata": {
                "start_url": url,
                "total_pages": 0,
                "start_time": datetime.now().isoformat(),
                "options": options,
            },
        }

        current_depth = 0

        async with Scraper() as scraper:
            while self.queue and (max_depth is None or current_depth < max_depth):
                current_urls = self.queue.copy()
                self.queue.clear()

                for current_url in current_urls:
                    print(f"Current URL: {current_url}")
                    print(
                        f"shoudl crawl: {self._should_crawl(current_url, url, options)}"
                    )
                    if not self._should_crawl(current_url, url, options):
                        continue

                    normalized = self._normalize_url(current_url)
                    print(f"Visiting {normalized}")

                    self.visited.add(normalized)

                    try:
                        result = await scraper.scrape(
                            normalized,
                            formats=options.get("formats", ["markdown"]),
                            page_options=options.get(
                                "page_options",
                                {
                                    "extract_main_content": True,
                                    "include_links": True,
                                    "structured_json": True,
                                },
                            ),
                        )

                        print(f"Scraped {normalized}: {result}")

                        if result and not result.get("error"):
                            results["pages"][normalized] = {
                                "content": result.get("content", {}),
                                "metadata": result.get("metadata", {}),
                                "links": result.get("links", []),
                            }

                            if result.get("links"):
                                for link in result["links"]:
                                    normalized_link = self._normalize_url(
                                        urljoin(current_url, link["url"])
                                    )
                                    if self._should_crawl(
                                        normalized_link, url, options
                                    ):
                                        self.queue.add(normalized_link)
                    except Exception as e:
                        logger.error(f"Error scrapping {normalized}: {str(e)}")
                        results["pages"][normalized] = {
                            "error": str(e),
                            "content": {},
                            "metadata": {},
                        }
                    results["metadata"]["total_pages"] += 1

                current_depth += 1

        results["metadata"]["end_time"] = datetime.now().isoformat()
        results["metadata"]["depth_reached"] = current_depth - 1

        return results
