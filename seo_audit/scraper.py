"""Web scraper module for fetching and parsing HTML pages.

This module handles all HTTP interactions and HTML parsing. It fetches
a given URL, handles basic errors (timeouts, non-200 responses, redirects
to different domains), and parses the response into a BeautifulSoup object.

Exports:
    fetch_page(url, timeout=10) -> dict:
        Fetch a URL and return a dict with html, status_code,
        response_time, final_url, or an error field on failure.
    parse_html(html) -> BeautifulSoup | None:
        Parse an HTML string into a BeautifulSoup object.
"""

from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_page(url, timeout=10):
    """Fetch a URL and return a dict with response data.

    Handles redirects gracefully. If the final URL after redirects is on
    a different domain than the original, the final_url is still reported
    but the caller may want to validate this.

    Args:
        url: The URL to fetch. Must include a scheme (http/https).
        timeout: Request timeout in seconds (default 10).

    Returns:
        A dict with keys:
            - html (str): The response body text.
            - status_code (int): HTTP status code.
            - response_time (float): Time in seconds.
            - final_url (str): URL after any redirects.
        On error, returns {"error": str} instead.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return {"error": f"Invalid URL '{url}' — must include http:// or https://"}

    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
    except requests.Timeout:
        return {"error": f"Request timed out after {timeout}s"}
    except requests.ConnectionError:
        return {"error": f"Could not connect to {url}"}
    except requests.HTTPError as exc:
        return {"error": f"HTTP error: {exc}"}
    except requests.RequestException as exc:
        return {"error": f"Request failed: {exc}"}

    # Validate that the response looks like HTML.
    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return {
            "error": (
                f"Expected HTML content (got '{content_type}'). "
                "The URL may not point to an HTML page."
            ),
        }

    return {
        "html": response.text,
        "status_code": response.status_code,
        "response_time": response.elapsed.total_seconds(),
        "final_url": response.url,
    }


def parse_html(html):
    """Parse an HTML string into a BeautifulSoup object.

    Args:
        html: The raw HTML content as a string.

    Returns:
        A BeautifulSoup object parsed with the lxml parser, or None
        if the html is empty or None. Falls back to html.parser if
        lxml is not installed.
    """
    if not html or not html.strip():
        return None
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")
