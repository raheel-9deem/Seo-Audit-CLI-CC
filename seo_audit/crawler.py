"""Site crawler module using BFS to discover and audit multiple pages.

This module provides a breadth-first crawler that follows internal links
up to a configurable depth and page limit. It is used by the CLI when
the --crawl flag is provided.

Exports:
    crawl_site(start_url, max_pages=20, max_depth=2, timeout=10) -> list:
        Returns a list of dicts with 'url', 'depth', 'html', and 'soup' keys.
"""

from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _is_internal(href, base_domain):
    """Check if a link is internal (same domain)."""
    parsed = urlparse(href)
    if not parsed.scheme:
        return True  # Relative URL is internal.
    return parsed.netloc == base_domain or parsed.netloc.startswith(base_domain)


def _normalize(url):
    """Normalize a URL by removing trailing slashes for comparison."""
    parsed = urlparse(url)
    # Normalize: strip trailing slashes from path.
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}{('?' + parsed.query) if parsed.query else ''}"


def crawl_site(start_url, max_pages=20, max_depth=2, timeout=10):
    """Crawl a site starting from start_url using BFS.

    Args:
        start_url: The URL to start crawling from.
        max_pages: Maximum number of pages to crawl (default 20).
        max_depth: Maximum link depth to follow (default 2).
        timeout: Request timeout in seconds (default 10).

    Returns:
        List of dicts, each containing:
            - url: The page URL.
            - depth: The crawl depth at which this page was found.
            - html: The raw HTML content.
            - soup: Parsed BeautifulSoup object.
    """
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    visited = set()
    results = []
    queue = deque([(start_url, 0)])  # (url, depth)

    while queue and len(results) < max_pages:
        url, depth = queue.popleft()
        normalized = _normalize(url)

        if normalized in visited:
            continue
        visited.add(normalized)

        if depth > max_depth:
            continue

        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if response.status_code >= 400:
                continue
        except requests.RequestException:
            continue

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            continue

        html = response.text
        soup = BeautifulSoup(html, "lxml")

        results.append({
            "url": url,
            "depth": depth,
            "html": html,
            "soup": soup,
        })

        # Extract links for next level.
        if depth < max_depth:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                # Skip non-HTML file extensions.
                if href.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx", ".zip")):
                    continue

                next_url = urljoin(url, href)
                next_normalized = _normalize(next_url)

                if next_normalized not in visited and _is_internal(href, base_domain):
                    queue.append((next_url, depth + 1))

    return results
