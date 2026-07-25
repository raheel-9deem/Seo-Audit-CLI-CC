"""Tests for seo_audit.crawler module.

Run with: pytest tests/test_crawler.py -v
"""

import pytest
import requests
from unittest.mock import patch, MagicMock

from seo_audit.crawler import crawl_site


class MockResponse:
    """Mock HTTP response for simulating page fetches."""

    def __init__(self, url, html, status_code=200, links=None):
        self.url = url
        self.html = html
        self.text = html  # crawler expects .text attribute
        self.status_code = status_code
        self.links = links or []
        self.headers = {"Content-Type": "text/html"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def _make_page_html(title, links=None):
    """Generate minimal HTML with a title and optional links.

    Args:
        title: Page title string.
        links: List of (href, text) tuples.

    Returns:
        HTML string.
    """
    link_tags = ""
    if links:
        for href, text in links:
            link_tags += f'<a href="{href}">{text}</a>\n'
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>{title}</title></head>
    <body>
        <h1>{title}</h1>
        {link_tags}
        <p>This is sample content with enough words to pass word count checks.
        {'word ' * 300}</p>
    </body>
    </html>
    """


@patch("seo_audit.crawler.requests.get")
class TestCrawlSite:
    def test_single_page_no_links(self, mock_get):
        """Crawling a page with no internal links should return just that page."""
        html = _make_page_html("Home")
        mock_get.return_value = MockResponse(
            "https://example.com/", html, links=[]
        )
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=1)
        assert len(urls) == 1
        assert urls[0]["url"] == "https://example.com/"
        assert urls[0]["depth"] == 0

    def test_follows_internal_links(self, mock_get):
        """Crawler should follow internal links."""
        home_html = _make_page_html("Home", [
            ("/about", "About"),
            ("/contact", "Contact"),
        ])
        about_html = _make_page_html("About")
        contact_html = _make_page_html("Contact")

        def _response(url, **kwargs):
            if "about" in url:
                return MockResponse(url, about_html)
            elif "contact" in url:
                return MockResponse(url, contact_html)
            else:
                return MockResponse(url, home_html)

        mock_get.side_effect = _response
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=2)
        assert len(urls) == 3
        found_urls = {u["url"] for u in urls}
        assert "https://example.com/" in found_urls
        assert "https://example.com/about" in found_urls
        assert "https://example.com/contact" in found_urls

    def test_respects_max_pages(self, mock_get):
        """Crawler should stop after max_pages is reached."""
        html = _make_page_html("Page", [
            ("/page1", "P1"),
            ("/page2", "P2"),
            ("/page3", "P3"),
        ])

        def _response(url, **kwargs):
            return MockResponse(url, html)

        mock_get.side_effect = _response
        urls = crawl_site("https://example.com/", max_pages=2, max_depth=5)
        assert len(urls) == 2

    def test_respects_max_depth(self, mock_get):
        """Crawler should not go deeper than max_depth."""
        home_html = _make_page_html("Home", [("/level1", "L1")])
        level1_html = _make_page_html("Level 1", [("/level2", "L2")])
        level2_html = _make_page_html("Level 2", [("/level3", "L3")])

        def _response(url, **kwargs):
            if "level1" in url:
                return MockResponse(url, level1_html)
            elif "level2" in url:
                return MockResponse(url, level2_html)
            elif "level3" in url:
                return MockResponse(url, _make_page_html("Level 3"))
            else:
                return MockResponse(url, home_html)

        mock_get.side_effect = _response
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=1)
        found_urls = {u["url"] for u in urls}
        assert "https://example.com/" in found_urls
        assert "https://example.com/level1" in found_urls
        # Should NOT include level2 or deeper.
        assert "https://example.com/level2" not in found_urls

    def test_skips_non_html_links(self, mock_get):
        """Crawler should skip images, PDFs, mailto, tel, etc."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Home</title></head>
        <body>
            <a href="/about">About</a>
            <a href="/image.jpg">Image</a>
            <a href="/doc.pdf">PDF</a>
            <a href="mailto:test@example.com">Email</a>
            <a href="tel:+1234567890">Phone</a>
            <a href="#section">Anchor</a>
            <a href="javascript:void(0)">JS</a>
        </body>
        </html>
        """
        mock_get.return_value = MockResponse("https://example.com/", html)
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=1)
        # Only the home page and /about should be found.
        found_urls = {u["url"] for u in urls}
        assert "https://example.com/" in found_urls
        assert "https://example.com/about" in found_urls
        assert len(found_urls) == 2

    def test_avoids_infinite_loops(self, mock_get):
        """Crawler should not revisit the same URL twice."""
        html = _make_page_html("Page", [("/page-a", "A"), ("/page-b", "B")])
        page_a_html = _make_page_html("Page A", [("/page-b", "B"), ("/", "Home")])
        page_b_html = _make_page_html("Page B", [("/page-a", "A"), ("/", "Home")])

        def _response(url, **kwargs):
            if "page-a" in url:
                return MockResponse(url, page_a_html)
            elif "page-b" in url:
                return MockResponse(url, page_b_html)
            else:
                return MockResponse(url, html)

        mock_get.side_effect = _response
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=5)
        found_urls = {u["url"] for u in urls}
        # Should have exactly 3 unique URLs.
        assert len(found_urls) == 3

    def test_skips_external_links(self, mock_get):
        """Crawler should not follow links to other domains."""
        html = _make_page_html("Home", [
            ("/about", "About"),
            ("https://other.com/page", "External"),
        ])
        mock_get.return_value = MockResponse("https://example.com/", html)
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=2)
        found_urls = {u["url"] for u in urls}
        assert "https://other.com/page" not in found_urls

    def test_handles_404_gracefully(self, mock_get):
        """Crawler should skip pages that return 404."""
        home_html = _make_page_html("Home", [("/missing", "Missing")])

        def _response(url, **kwargs):
            if "missing" in url:
                raise requests.HTTPError(f"HTTP 404")
            return MockResponse(url, home_html)

        mock_get.side_effect = _response
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=2)
        found_urls = {u["url"] for u in urls}
        assert "https://example.com/missing" not in found_urls
        assert "https://example.com/" in found_urls

    def test_normalizes_trailing_slash(self, mock_get):
        """Crawler should treat /page and /page/ as the same URL."""
        home_html = _make_page_html("Home", [("/about", "About")])
        about_html = _make_page_html("About", [("/", "Home")])

        def _response(url, **kwargs):
            if "about" in url:
                return MockResponse(url, about_html)
            return MockResponse(url, home_html)

        mock_get.side_effect = _response
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=2)
        found_urls = {u["url"] for u in urls}
        assert "https://example.com/about" in found_urls or "https://example.com/about/" in found_urls

    def test_empty_site(self, mock_get):
        """Crawling should handle a site that returns empty content."""
        mock_get.return_value = MockResponse("https://example.com/", "")
        urls = crawl_site("https://example.com/", max_pages=10, max_depth=1)
        # Should still include the starting URL even if content is empty.
        assert len(urls) >= 1
