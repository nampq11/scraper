import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Set, Dict, Optional
from urllib.parse import urljoin, urlparse


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

    def _is_same_domain(self, url1: str, url2: str, include_subdomains: bool = False) -> bool:
        """Check if two URLs belong to the same domain."""
        parsed1 = urlparse(url1)
        parsed2 = urlparse(url2)

        if include_subdomains:
            domain1 = '.'.join(parsed1.netloc.split('.')[-2:])
            domain2 = '.'.join(parsed2.netloc.split('.')[-2:])
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
        if not url or not url.startswith('http://', 'https://'):
            return False
        
        include_subdomains = options.get('include_subdomains', False)
        if not options.get('allow_backwards', False) and not self._is_same_domain(url, base_url, include_subdomains):
            return False

        normalized = self._normalize_url(url)
        if normalized in self.visited:
            return False
        
        if options.get('max_pages') and len(self.visited) >= options['max_pages']:
            return False
        
        path = urlparse(normalized).path

        if any(p in path.lower() for p in ['/cdn-cgi/', '/wp-admin/', '/wp-includes/', '/assets/', '/static/']):
            return False

        if options.get('exclude_paths'):
            for pattern in options['exclude_paths']:
                if pattern.endswith('*'):
                    if path.startswith(pattern[:-1]):
                        return False
                elif path == pattern:
                    return False
        
        if options.get('include_only_paths'):
            matched = False
            for pattern in options['include_only_paths']:
                if pattern.endswith('*'):
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

        # async with 
