"""Individual SEO check functions.

This module contains the core SEO analysis logic. Each function inspects
a specific aspect of the page (title tag, meta description, headings,
links, images, etc.) and returns a result dict with:

    {
        "name": str,       # Human-readable check name
        "status": str,     # "pass", "warning", or "fail"
        "message": str,    # Description of the finding
        "details": dict,   # Optional structured details
    }
"""

import concurrent.futures
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def check_title(soup):
    """Check the <title> tag for presence and optimal length.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details including title text and length.
        - fail: title missing or shorter than 30 characters.
        - warning: title longer than 60 characters.
        - pass: title present and between 30-60 characters.
    """
    title_tag = soup.find("title")
    if not title_tag:
        return {
            "name": "Title Tag",
            "status": "fail",
            "message": "No <title> tag found.",
            "details": {"length": 0},
        }

    text = title_tag.get_text(strip=True)
    length = len(text)

    if not text:
        return {
            "name": "Title Tag",
            "status": "fail",
            "message": "<title> tag is empty.",
            "details": {"length": 0},
        }

    if length < 30:
        return {
            "name": "Title Tag",
            "status": "fail",
            "message": f"Title is too short ({length} chars). Minimum recommended: 30.",
            "details": {"length": length, "title": text},
        }

    if length > 60:
        return {
            "name": "Title Tag",
            "status": "warning",
            "message": f"Title is too long ({length} chars). Maximum recommended: 60.",
            "details": {"length": length, "title": text},
        }

    return {
        "name": "Title Tag",
        "status": "pass",
        "message": f"Title length is good ({length} chars).",
        "details": {"length": length, "title": text},
    }


def check_meta_description(soup):
    """Check the meta description for presence and optimal length.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details including description text and length.
        - fail: missing or shorter than 120 characters.
        - warning: longer than 160 characters.
        - pass: between 120-160 characters.
    """
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta:
        return {
            "name": "Meta Description",
            "status": "fail",
            "message": "No meta description tag found.",
            "details": {"length": 0},
        }

    content = meta.get("content", "").strip()
    length = len(content)

    if not content:
        return {
            "name": "Meta Description",
            "status": "fail",
            "message": "Meta description is empty.",
            "details": {"length": 0},
        }

    if length < 120:
        return {
            "name": "Meta Description",
            "status": "fail",
            "message": f"Meta description is too short ({length} chars). Recommended: 120-160.",
            "details": {"length": length, "description": content},
        }

    if length > 160:
        return {
            "name": "Meta Description",
            "status": "warning",
            "message": f"Meta description is too long ({length} chars). Recommended max: 160.",
            "details": {"length": length, "description": content},
        }

    return {
        "name": "Meta Description",
        "status": "pass",
        "message": f"Meta description length is good ({length} chars).",
        "details": {"length": length, "description": content},
    }


def check_headings(soup):
    """Check heading structure — presence of H1 and hierarchy.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details including counts per level.
        - fail: no H1 found, or multiple H1 tags.
        - warning: no headings at all.
        - pass: exactly one H1 with proper hierarchy.
    """
    h1s = soup.find_all("h1")
    all_headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

    counts = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}

    if not h1s:
        return {
            "name": "Headings",
            "status": "fail",
            "message": "No <h1> tag found. Every page should have exactly one H1.",
            "details": {"counts": counts},
        }

    if len(h1s) > 1:
        return {
            "name": "Headings",
            "status": "fail",
            "message": f"Multiple <h1> tags found ({len(h1s)}). Use only one H1 per page.",
            "details": {"counts": counts},
        }

    if not all_headings:
        return {
            "name": "Headings",
            "status": "warning",
            "message": "No heading tags found on the page.",
            "details": {"counts": counts},
        }

    # Check for skipped heading levels
    levels_present = [i for i in range(1, 7) if counts[f"h{i}"] > 0]
    skipped = []
    for i in range(len(levels_present) - 1):
        if levels_present[i + 1] - levels_present[i] > 1:
            skipped.append(f"h{levels_present[i]} -> h{levels_present[i+1]}")

    if skipped:
        return {
            "name": "Headings",
            "status": "warning",
            "message": f"Heading levels skipped: {', '.join(skipped)}.",
            "details": {"counts": counts, "skipped_levels": skipped},
        }

    return {
        "name": "Headings",
        "status": "pass",
        "message": f"Heading structure looks good. H1: '{h1s[0].get_text(strip=True)[:50]}...'",
        "details": {"counts": counts},
    }


def check_images(soup):
    """Check images for missing alt text.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details about image alt attributes.
        - fail: any images missing alt text.
        - warning: no images found on page.
        - pass: all images have alt text.
    """
    images = soup.find_all("img")

    if not images:
        return {
            "name": "Images",
            "status": "warning",
            "message": "No <img> tags found on the page.",
            "details": {"total": 0, "missing_alt": 0},
        }

    missing_alt = []
    for img in images:
        alt = img.get("alt", "").strip()
        if not alt:
            missing_alt.append(img.get("src", "unknown"))

    total = len(images)
    missing_count = len(missing_alt)

    if missing_count > 0:
        return {
            "name": "Images",
            "status": "fail",
            "message": f"{missing_count} of {total} images are missing alt text.",
            "details": {
                "total": total,
                "missing_alt": missing_count,
                "missing_sources": missing_alt[:10],
            },
        }

    return {
        "name": "Images",
        "status": "pass",
        "message": f"All {total} images have alt text.",
        "details": {"total": total, "missing_alt": 0},
    }


def check_word_count(soup):
    """Check the visible text word count on the page.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and word count details.
        - fail: fewer than 300 words.
        - pass: 300 words or more.
    """
    # Work on a copy so we don't mutate the original soup for other checks.
    soup_copy = BeautifulSoup(str(soup), "lxml")
    for tag in soup_copy(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup_copy.get_text(separator=" ")
    words = text.split()
    count = len(words)

    if count < 300:
        return {
            "name": "Word Count",
            "status": "fail",
            "message": f"Page has only {count} words. Recommended minimum: 300.",
            "details": {"word_count": count},
        }

    return {
        "name": "Word Count",
        "status": "pass",
        "message": f"Page has {count} words — sufficient content length.",
        "details": {"word_count": count},
    }


def check_links(soup, base_url):
    """Analyze internal and external links on the page.

    Args:
        soup: BeautifulSoup object of the page.
        base_url: The base URL of the site for classifying internal vs external.

    Returns:
        Dict with status, message, and details including counts and lists
        of internal and external links.
    """
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    internal_links = []
    external_links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        parsed = urlparse(href)

        # Relative URLs or same-domain URLs are internal
        if not parsed.scheme:
            internal_links.append(href)
        elif parsed.netloc == base_domain or parsed.netloc.startswith(base_domain):
            internal_links.append(href)
        else:
            external_links.append(href)

    total = len(internal_links) + len(external_links)

    if total == 0:
        return {
            "name": "Links",
            "status": "warning",
            "message": "No links found on the page.",
            "details": {"internal_count": 0, "external_count": 0},
        }

    return {
        "name": "Links",
        "status": "pass",
        "message": f"Found {total} links ({len(internal_links)} internal, {len(external_links)} external).",
        "details": {
            "internal_count": len(internal_links),
            "external_count": len(external_links),
            "internal_links": internal_links[:20],
            "external_links": external_links[:20],
        },
    }


def check_canonical(soup):
    """Check for the presence of a canonical link tag.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and canonical URL if found.
        - fail: no canonical tag.
        - pass: canonical tag present.
    """
    canonical = soup.find("link", rel="canonical")

    if not canonical:
        return {
            "name": "Canonical",
            "status": "fail",
            "message": "No canonical <link> tag found.",
            "details": {},
        }

    href = canonical.get("href", "").strip()
    if not href:
        return {
            "name": "Canonical",
            "status": "fail",
            "message": "Canonical tag found but has no href attribute.",
            "details": {},
        }

    return {
        "name": "Canonical",
        "status": "pass",
        "message": f"Canonical URL: {href}",
        "details": {"canonical_url": href},
    }


def check_robots_meta(soup):
    """Check the meta robots tag for indexing directives.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and directive content.
        - fail: noindex or nofollow directives found.
        - pass: no robots meta (defaults to index,follow) or safe directives.
    """
    meta = soup.find("meta", attrs={"name": "robots"})

    if not meta:
        return {
            "name": "Robots Meta",
            "status": "pass",
            "message": "No robots meta tag found (defaults to index, follow).",
            "details": {"content": None},
        }

    content = meta.get("content", "").strip().lower()

    if not content:
        return {
            "name": "Robots Meta",
            "status": "pass",
            "message": "Robots meta tag found but empty (defaults to index, follow).",
            "details": {"content": ""},
        }

    directives = [d.strip() for d in content.split(",")]

    problematic = [d for d in directives if d in ("noindex", "nofollow", "noarchive", "nosnippet")]
    if problematic:
        return {
            "name": "Robots Meta",
            "status": "fail",
            "message": f"Robots directive may hinder indexing: '{content}'.",
            "details": {"content": content, "directives": directives, "problematic": problematic},
        }

    return {
        "name": "Robots Meta",
        "status": "pass",
        "message": f"Robots directive: '{content}'.",
        "details": {"content": content, "directives": directives},
    }


def check_broken_links(links, max_workers=10):
    """Check a list of links for broken URLs using parallel HEAD requests.

    Args:
        links: List of absolute URL strings to check.
        max_workers: Maximum number of concurrent threads (default 10).

    Returns:
        List of dicts for broken links, each containing:
            {"url": str, "status_code": int or None, "error": str or None}
    """
    if not links:
        return []

    broken = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })

    def _check_link(url):
        """Check a single URL, returning a dict if broken, None if OK."""
        try:
            response = session.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 405:
                # HEAD not allowed — fall back to GET
                response = session.get(url, timeout=5, allow_redirects=True, stream=True)
            if response.status_code >= 400:
                return {
                    "url": url,
                    "status_code": response.status_code,
                    "error": None,
                }
        except requests.Timeout:
            return {
                "url": url,
                "status_code": None,
                "error": "timeout",
            }
        except requests.ConnectionError:
            return {
                "url": url,
                "status_code": None,
                "error": "connection_error",
            }
        except requests.RequestException:
            return {
                "url": url,
                "status_code": None,
                "error": "request_error",
            }
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(_check_link, links)
        for result in results:
            if result is not None:
                broken.append(result)

    return broken


# Ordered list of all check functions (that take a soup) for easy iteration.
ALL_CHECKS = [
    check_title,
    check_meta_description,
    check_headings,
    check_images,
    check_word_count,
    check_links,
    check_canonical,
    check_robots_meta,
]
