"""Tests for seo_audit.checks module.

Run with: pytest tests/test_checks.py -v
"""

import pytest
from bs4 import BeautifulSoup

from seo_audit.checks import (
    check_title,
    check_meta_description,
    check_headings,
    check_images,
    check_word_count,
    check_links,
    check_canonical,
    check_robots_meta,
    check_broken_links,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _soup(html):
    """Parse an HTML string into a BeautifulSoup object."""
    return BeautifulSoup(html, "lxml")


# ── check_title ──────────────────────────────────────────────────────────

class TestCheckTitle:
    def test_missing_title(self):
        soup = _soup("<html><head></head><body></body></html>")
        result = check_title(soup)
        assert result["status"] == "fail"
        assert "No <title> tag found" in result["message"]

    def test_empty_title(self):
        soup = _soup("<html><head><title>   </title></head><body></body></html>")
        result = check_title(soup)
        assert result["status"] == "fail"
        assert "empty" in result["message"]

    def test_short_title(self):
        soup = _soup("<html><head><title>Hi</title></head><body></body></html>")
        result = check_title(soup)
        assert result["status"] == "fail"
        assert "too short" in result["message"]

    def test_good_title(self):
        soup = _soup(
            "<html><head><title>This Is A Good Title For SEO Testing</title></head><body></body></html>"
        )
        result = check_title(soup)
        assert result["status"] == "pass"
        # "This Is A Good Title For SEO Testing" = 36 chars (between 30-60)
        assert result["details"]["length"] == 36

    def test_long_title(self):
        soup = _soup(
            "<html><head><title>" + "A" * 80 + "</title></head><body></body></html>"
        )
        result = check_title(soup)
        assert result["status"] == "warning"
        assert "too long" in result["message"]

    def test_returns_name(self):
        soup = _soup("<html><head><title>Test</title></head><body></body></html>")
        result = check_title(soup)
        assert result["name"] == "Title Tag"


# ── check_meta_description ───────────────────────────────────────────────

class TestCheckMetaDescription:
    def test_missing(self):
        soup = _soup("<html><head></head><body></body></html>")
        result = check_meta_description(soup)
        assert result["status"] == "fail"

    def test_empty(self):
        soup = _soup(
            '<html><head><meta name="description" content=""></head><body></body></html>'
        )
        result = check_meta_description(soup)
        assert result["status"] == "fail"

    def test_short(self):
        soup = _soup(
            '<html><head><meta name="description" content="Short desc."></head><body></body></html>'
        )
        result = check_meta_description(soup)
        assert result["status"] == "fail"
        assert "too short" in result["message"]

    def test_good(self):
        # Need at least 120 chars for a passing description
        desc = "This is a comprehensive page description that provides enough detail " \
               "to meet search engine guidelines and attract clicks from users."
        soup = _soup(
            f'<html><head><meta name="description" content="{desc}"></head><body></body></html>'
        )
        result = check_meta_description(soup)
        assert result["status"] == "pass"

    def test_long(self):
        desc = "A" * 200
        soup = _soup(
            f'<html><head><meta name="description" content="{desc}"></head><body></body></html>'
        )
        result = check_meta_description(soup)
        assert result["status"] == "warning"
        assert "too long" in result["message"]

    def test_returns_name(self):
        soup = _soup("<html><head></head><body></body></html>")
        result = check_meta_description(soup)
        assert result["name"] == "Meta Description"


# ── check_headings ───────────────────────────────────────────────────────

class TestCheckHeadings:
    def test_no_h1(self):
        soup = _soup("<html><body><h2>Subheading</h2></body></html>")
        result = check_headings(soup)
        assert result["status"] == "fail"
        assert "No <h1>" in result["message"]

    def test_multiple_h1(self):
        soup = _soup("<html><body><h1>A</h1><h1>B</h1></body></html>")
        result = check_headings(soup)
        assert result["status"] == "fail"
        assert "Multiple" in result["message"]

    def test_good_structure(self):
        soup = _soup(
            "<html><body><h1>Main</h1><h2>Sub</h2><h3>Detail</h3></body></html>"
        )
        result = check_headings(soup)
        assert result["status"] == "pass"

    def test_skipped_levels(self):
        soup = _soup("<html><body><h1>Main</h1><h3>Detail</h3></body></html>")
        result = check_headings(soup)
        assert result["status"] == "warning"
        assert "skipped" in result["message"]

    def test_no_headings(self):
        # With no headings at all (and no H1), the status is "fail"
        # because check_headings requires exactly one H1.
        soup = _soup("<html><body></body></html>")
        result = check_headings(soup)
        assert result["status"] == "fail"
        assert "No <h1>" in result["message"]

    def test_returns_name(self):
        soup = _soup("<html><body><h1>Hi</h1></body></html>")
        result = check_headings(soup)
        assert result["name"] == "Headings"


# ── check_images ─────────────────────────────────────────────────────────

class TestCheckImages:
    def test_no_images(self):
        soup = _soup("<html><body></body></html>")
        result = check_images(soup)
        assert result["status"] == "warning"

    def test_all_have_alt(self):
        soup = _soup(
            '<html><body>'
            '<img src="a.jpg" alt="Image A">'
            '<img src="b.jpg" alt="Image B">'
            "</body></html>"
        )
        result = check_images(soup)
        assert result["status"] == "pass"

    def test_missing_alt(self):
        soup = _soup(
            '<html><body>'
            '<img src="a.jpg">'
            '<img src="b.jpg" alt="B">'
            "</body></html>"
        )
        result = check_images(soup)
        assert result["status"] == "fail"
        assert "1 of 2" in result["message"]

    def test_empty_alt(self):
        soup = _soup(
            '<html><body><img src="a.jpg" alt=""></body></html>'
        )
        result = check_images(soup)
        assert result["status"] == "fail"

    def test_returns_name(self):
        soup = _soup('<html><body><img src="a.jpg" alt="A"></body></html>')
        result = check_images(soup)
        assert result["name"] == "Images"


# ── check_word_count ─────────────────────────────────────────────────────

class TestCheckWordCount:
    def test_short_content(self):
        soup = _soup("<html><body><p>Hello world.</p></body></html>")
        result = check_word_count(soup)
        assert result["status"] == "fail"
        assert "only 2 words" in result["message"]

    def test_sufficient_content(self):
        words = "word " * 350
        soup = _soup(f"<html><body><p>{words}</p></body></html>")
        result = check_word_count(soup)
        assert result["status"] == "pass"
        assert result["details"]["word_count"] == 350

    def test_returns_name(self):
        soup = _soup("<html><body><p>Hi</p></body></html>")
        result = check_word_count(soup)
        assert result["name"] == "Word Count"


# ── check_links ──────────────────────────────────────────────────────────

class TestCheckLinks:
    def test_no_links(self):
        soup = _soup("<html><body></body></html>")
        result = check_links(soup, "https://example.com")
        assert result["status"] == "warning"

    def test_internal_links(self):
        soup = _soup(
            '<html><body>'
            '<a href="/about">About</a>'
            '<a href="/contact">Contact</a>'
            "</body></html>"
        )
        result = check_links(soup, "https://example.com")
        assert result["status"] == "pass"
        assert result["details"]["internal_count"] == 2

    def test_external_links(self):
        soup = _soup(
            '<html><body><a href="https://other.com/page">External</a></body></html>'
        )
        result = check_links(soup, "https://example.com")
        assert result["status"] == "pass"
        assert result["details"]["external_count"] == 1

    def test_mixed_links(self):
        soup = _soup(
            '<html><body>'
            '<a href="/about">Internal</a>'
            '<a href="https://other.com">External</a>'
            "</body></html>"
        )
        result = check_links(soup, "https://example.com")
        assert result["details"]["internal_count"] == 1
        assert result["details"]["external_count"] == 1

    def test_ignores_special_hrefs(self):
        soup = _soup(
            '<html><body>'
            '<a href="#section">Anchor</a>'
            '<a href="mailto:test@example.com">Email</a>'
            '<a href="tel:+1234567890">Phone</a>'
            '<a href="javascript:void(0)">JS</a>'
            "</body></html>"
        )
        result = check_links(soup, "https://example.com")
        assert result["details"]["internal_count"] == 0
        assert result["details"]["external_count"] == 0

    def test_returns_name(self):
        soup = _soup('<html><body><a href="/a">A</a></body></html>')
        result = check_links(soup, "https://example.com")
        assert result["name"] == "Links"


# ── check_canonical ──────────────────────────────────────────────────────

class TestCheckCanonical:
    def test_missing(self):
        soup = _soup("<html><head></head><body></body></html>")
        result = check_canonical(soup)
        assert result["status"] == "fail"

    def test_present(self):
        soup = _soup(
            '<html><head><link rel="canonical" href="https://example.com/page"></head><body></body></html>'
        )
        result = check_canonical(soup)
        assert result["status"] == "pass"
        assert result["details"]["canonical_url"] == "https://example.com/page"

    def test_empty_href(self):
        soup = _soup(
            '<html><head><link rel="canonical" href=""></head><body></body></html>'
        )
        result = check_canonical(soup)
        assert result["status"] == "fail"

    def test_returns_name(self):
        soup = _soup(
            '<html><head><link rel="canonical" href="https://example.com"></head><body></body></html>'
        )
        result = check_canonical(soup)
        assert result["name"] == "Canonical"


# ── check_robots_meta ────────────────────────────────────────────────────

class TestCheckRobotsMeta:
    def test_missing(self):
        soup = _soup("<html><head></head><body></body></html>")
        result = check_robots_meta(soup)
        assert result["status"] == "pass"  # defaults to index,follow

    def test_noindex(self):
        soup = _soup(
            '<html><head><meta name="robots" content="noindex"></head><body></body></html>'
        )
        result = check_robots_meta(soup)
        assert result["status"] == "fail"

    def test_nofollow(self):
        soup = _soup(
            '<html><head><meta name="robots" content="nofollow"></head><body></body></html>'
        )
        result = check_robots_meta(soup)
        assert result["status"] == "fail"

    def test_safe_directive(self):
        soup = _soup(
            '<html><head><meta name="robots" content="index, follow"></head><body></body></html>'
        )
        result = check_robots_meta(soup)
        assert result["status"] == "pass"

    def test_empty_content(self):
        soup = _soup(
            '<html><head><meta name="robots" content=""></head><body></body></html>'
        )
        result = check_robots_meta(soup)
        assert result["status"] == "pass"

    def test_returns_name(self):
        soup = _soup("<html><head></head><body></body></html>")
        result = check_robots_meta(soup)
        assert result["name"] == "Robots Meta"


# ── check_broken_links ───────────────────────────────────────────────────

class TestCheckBrokenLinks:
    def test_empty_list(self):
        result = check_broken_links([])
        assert result == []

    def test_good_link(self):
        # Test with a real URL that should always work
        result = check_broken_links(["https://www.google.com/"], max_workers=1)
        broken_urls = [b["url"] for b in result]
        assert "https://www.google.com/" not in broken_urls

    def test_404_link(self):
        result = check_broken_links(
            ["https://www.google.com/this-page-does-not-exist-xyz123"],
            max_workers=1,
        )
        broken_urls = [b["url"] for b in result]
        assert "https://www.google.com/this-page-does-not-exist-xyz123" in broken_urls
