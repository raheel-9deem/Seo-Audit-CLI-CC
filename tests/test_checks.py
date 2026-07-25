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
    check_schema,
    check_open_graph,
    check_twitter_cards,
    check_hreflang,
    check_viewport,
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


# ── check_schema ──────────────────────────────────────────────────────────

class TestCheckSchema:
    def test_no_structured_data(self):
        soup = _soup("<html><body><p>Hello</p></body></html>")
        result = check_schema(soup)
        assert result["status"] == "fail"
        assert "No structured data" in result["message"]

    def test_json_ld_single_type(self):
        soup = _soup("""
            <html>
            <head>
                <script type="application/ld+json">
                {"@type": "Article", "name": "Test"}
                </script>
            </head>
            <body></body>
            </html>
        """)
        result = check_schema(soup)
        assert result["status"] == "pass"
        assert "Article" in result["details"]["types"]

    def test_json_ld_graph(self):
        soup = _soup("""
            <html>
            <head>
                <script type="application/ld+json">
                {
                    "@graph": [
                        {"@type": "Organization", "name": "TestOrg"},
                        {"@type": "WebSite", "name": "TestSite"}
                    ]
                }
                </script>
            </head>
            <body></body>
            </html>
        """)
        result = check_schema(soup)
        assert result["status"] == "pass"
        assert "Organization" in result["details"]["types"]
        assert "WebSite" in result["details"]["types"]

    def test_microdata(self):
        soup = _soup("""
            <html>
            <body>
                <div itemscope itemtype="https://schema.org/Person">
                    <span itemprop="name">John</span>
                </div>
            </body>
            </html>
        """)
        result = check_schema(soup)
        assert result["status"] == "pass"
        assert "Person" in result["details"]["types"]

    def test_invalid_json_still_passes_as_present(self):
        soup = _soup("""
            <html>
            <head>
                <script type="application/ld+json">not valid json{{{</script>
            </head>
            <body></body>
            </html>
        """)
        result = check_schema(soup)
        # Has JSON-LD script but parse failed — should still detect presence
        # via the "unknown (parse error)" fallback.
        assert result["status"] == "pass"
        assert "unknown (parse error)" in result["details"]["types"]

    def test_empty_json_ld(self):
        soup = _soup("""
            <html>
            <head>
                <script type="application/ld+json">   </script>
            </head>
            <body></body>
            </html>
        """)
        result = check_schema(soup)
        # Empty JSON-LD script — no types extracted, no microdata → fail.
        assert result["status"] == "fail"

    def test_returns_name(self):
        soup = _soup("<html><body></body></html>")
        result = check_schema(soup)
        assert result["name"] == "Schema.org"


# ── check_open_graph ─────────────────────────────────────────────────────

class TestCheckOpenGraph:
    def test_no_og_tags(self):
        soup = _soup("<html><body></body></html>")
        result = check_open_graph(soup)
        assert result["status"] == "fail"
        assert "No Open Graph" in result["message"]

    def test_all_og_tags_present(self):
        soup = _soup("""
            <html>
            <head>
                <meta property="og:title" content="Test Title">
                <meta property="og:description" content="Test Description">
                <meta property="og:image" content="https://example.com/image.jpg">
                <meta property="og:url" content="https://example.com/page">
            </head>
            <body></body>
            </html>
        """)
        result = check_open_graph(soup)
        assert result["status"] == "pass"
        assert len(result["details"]["missing"]) == 0

    def test_partial_og_tags(self):
        soup = _soup("""
            <html>
            <head>
                <meta property="og:title" content="Test Title">
                <meta property="og:image" content="https://example.com/image.jpg">
            </head>
            <body></body>
            </html>
        """)
        result = check_open_graph(soup)
        assert result["status"] == "warning"
        assert "og:description" in result["details"]["missing"]
        assert "og:url" in result["details"]["missing"]

    def test_empty_og_content(self):
        soup = _soup("""
            <html>
            <head>
                <meta property="og:title" content="">
                <meta property="og:description" content="Desc">
                <meta property="og:image" content="img.jpg">
                <meta property="og:url" content="url">
            </head>
            <body></body>
            </html>
        """)
        result = check_open_graph(soup)
        assert result["status"] == "warning"
        assert result["details"]["found"]["og:title"] == "(empty)"

    def test_returns_name(self):
        soup = _soup("<html><body></body></html>")
        result = check_open_graph(soup)
        assert result["name"] == "Open Graph"


# ── check_twitter_cards ──────────────────────────────────────────────────

class TestCheckTwitterCards:
    def test_no_twitter_tags(self):
        soup = _soup("<html><body></body></html>")
        result = check_twitter_cards(soup)
        assert result["status"] == "fail"

    def test_all_twitter_tags_present(self):
        soup = _soup("""
            <html>
            <head>
                <meta name="twitter:card" content="summary">
                <meta name="twitter:title" content="Test Title">
                <meta name="twitter:description" content="Test Description">
            </head>
            <body></body>
            </html>
        """)
        result = check_twitter_cards(soup)
        assert result["status"] == "pass"

    def test_partial_twitter_tags(self):
        soup = _soup("""
            <html>
            <head>
                <meta name="twitter:card" content="summary">
            </head>
            <body></body>
            </html>
        """)
        result = check_twitter_cards(soup)
        assert result["status"] == "warning"
        assert "twitter:title" in result["details"]["missing"]
        assert "twitter:description" in result["details"]["missing"]

    def test_returns_name(self):
        soup = _soup("<html><body></body></html>")
        result = check_twitter_cards(soup)
        assert result["name"] == "Twitter Cards"


# ── check_hreflang ────────────────────────────────────────────────────────

class TestCheckHreflang:
    def test_no_hreflang(self):
        soup = _soup("<html><body></body></html>")
        result = check_hreflang(soup)
        assert result["status"] == "pass"
        assert "single-language" in result["message"]

    def test_hreflang_with_x_default(self):
        soup = _soup("""
            <html>
            <head>
                <link rel="alternate" hreflang="en" href="https://example.com/en">
                <link rel="alternate" hreflang="fr" href="https://example.com/fr">
                <link rel="alternate" hreflang="x-default" href="https://example.com/">
            </head>
            <body></body>
            </html>
        """)
        result = check_hreflang(soup)
        assert result["status"] == "pass"
        assert result["details"]["has_x_default"] is True
        assert len(result["details"]["languages"]) == 3

    def test_hreflang_without_x_default(self):
        soup = _soup("""
            <html>
            <head>
                <link rel="alternate" hreflang="en" href="https://example.com/en">
                <link rel="alternate" hreflang="fr" href="https://example.com/fr">
            </head>
            <body></body>
            </html>
        """)
        result = check_hreflang(soup)
        assert result["status"] == "warning"
        assert "no x-default" in result["message"]

    def test_returns_name(self):
        soup = _soup("<html><body></body></html>")
        result = check_hreflang(soup)
        assert result["name"] == "Hreflang"


# ── check_viewport ────────────────────────────────────────────────────────

class TestCheckViewport:
    def test_no_viewport(self):
        soup = _soup("<html><body></body></html>")
        result = check_viewport(soup)
        assert result["status"] == "fail"
        assert "No viewport" in result["message"]

    def test_good_viewport(self):
        soup = _soup(
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body></body></html>'
        )
        result = check_viewport(soup)
        assert result["status"] == "pass"

    def test_missing_device_width(self):
        soup = _soup(
            '<html><head><meta name="viewport" content="initial-scale=1.0"></head><body></body></html>'
        )
        result = check_viewport(soup)
        assert result["status"] == "warning"
        assert "width=device-width" in result["message"]

    def test_missing_initial_scale(self):
        soup = _soup(
            '<html><head><meta name="viewport" content="width=device-width"></head><body></body></html>'
        )
        result = check_viewport(soup)
        assert result["status"] == "warning"
        assert "initial-scale" in result["message"]

    def test_restricts_zoom(self):
        soup = _soup(
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1"></head><body></body></html>'
        )
        result = check_viewport(soup)
        assert result["status"] == "warning"
        assert "zoom" in result["message"]

    def test_empty_content(self):
        soup = _soup(
            '<html><head><meta name="viewport" content=""></head><body></body></html>'
        )
        result = check_viewport(soup)
        assert result["status"] == "fail"

    def test_returns_name(self):
        soup = _soup(
            '<html><head><meta name="viewport" content="width=device-width"></head><body></body></html>'
        )
        result = check_viewport(soup)
        assert result["name"] == "Viewport"
