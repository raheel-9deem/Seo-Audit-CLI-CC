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
    try:
        soup_copy = BeautifulSoup(str(soup), "lxml")
    except Exception:
        soup_copy = BeautifulSoup(str(soup), "html.parser")
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


def check_schema(soup):
    """Detect JSON-LD structured data and microdata markup.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details including found schema types.
        - fail: no structured data found.
        - pass: at least one schema type detected.
    """
    schema_types = []

    # Check for JSON-LD scripts.
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    for script in json_ld_scripts:
        text = script.string or ""
        text = text.strip()
        if not text:
            continue
        # Try to extract @type values from the JSON.
        try:
            import json as _json
            data = _json.loads(text)
            # Handle both single objects and @graph arrays.
            items = data.get("@graph", [data]) if isinstance(data, dict) else []
            if not items and isinstance(data, dict):
                items = [data]
            for item in items:
                if isinstance(item, dict):
                    item_type = item.get("@type", "")
                    if item_type:
                        if isinstance(item_type, list):
                            schema_types.extend(item_type)
                        else:
                            schema_types.append(item_type)
        except Exception:
            # JSON parse failure — still note that a script was present.
            schema_types.append("unknown (parse error)")

    # Check for microdata (itemscope attribute).
    microdata_items = soup.find_all(attrs={"itemscope": True})
    for item in microdata_items:
        itemtype = item.get("itemtype", "")
        if itemtype:
            # Extract the schema.org type name from the URL.
            type_name = itemtype.rsplit("/", 1)[-1] if itemtype else ""
            if type_name:
                schema_types.append(type_name)

    if not schema_types:
        return {
            "name": "Schema.org",
            "status": "fail",
            "message": "No structured data (JSON-LD or microdata) found.",
            "details": {"types": []},
        }

    # Deduplicate while preserving order.
    unique_types = list(dict.fromkeys(schema_types))
    return {
        "name": "Schema.org",
        "status": "pass",
        "message": f"Found {len(unique_types)} schema type(s): {', '.join(unique_types)}.",
        "details": {"types": unique_types, "json_ld_count": len(json_ld_scripts), "microdata_count": len(microdata_items)},
    }


def check_open_graph(soup):
    """Check for Open Graph meta tags.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details about found/missing OG tags.
        - fail: no OG tags found.
        - warning: some OG tags present but missing recommended ones.
        - pass: all four core OG tags present.
    """
    required_tags = ["og:title", "og:description", "og:image", "og:url"]
    found = {}
    missing = []

    for tag_name in required_tags:
        meta = soup.find("meta", property=tag_name)
        if meta:
            content = meta.get("content", "").strip()
            found[tag_name] = content if content else "(empty)"
        else:
            missing.append(tag_name)

    total_required = len(required_tags)
    found_count = total_required - len(missing)

    if found_count == 0:
        return {
            "name": "Open Graph",
            "status": "fail",
            "message": "No Open Graph meta tags found.",
            "details": {"found": {}, "missing": required_tags},
        }

    if missing:
        return {
            "name": "Open Graph",
            "status": "warning",
            "message": f"Open Graph tags found ({found_count}/{total_required}), but missing: {', '.join(missing)}.",
            "details": {"found": found, "missing": missing},
        }

    return {
        "name": "Open Graph",
        "status": "pass",
        "message": f"All {total_required} core Open Graph tags are present.",
        "details": {"found": found, "missing": []},
    }


def check_twitter_cards(soup):
    """Check for Twitter Card meta tags.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details about found/missing Twitter Card tags.
        - fail: no Twitter Card tags found.
        - warning: some tags present but missing recommended ones.
        - pass: twitter:card, twitter:title, and twitter:description all present.
    """
    required_tags = ["twitter:card", "twitter:title", "twitter:description"]
    found = {}
    missing = []

    for tag_name in required_tags:
        meta = soup.find("meta", attrs={"name": tag_name})
        if meta:
            content = meta.get("content", "").strip()
            found[tag_name] = content if content else "(empty)"
        else:
            missing.append(tag_name)

    total_required = len(required_tags)
    found_count = total_required - len(missing)

    if found_count == 0:
        return {
            "name": "Twitter Cards",
            "status": "fail",
            "message": "No Twitter Card meta tags found.",
            "details": {"found": {}, "missing": required_tags},
        }

    if missing:
        return {
            "name": "Twitter Cards",
            "status": "warning",
            "message": f"Twitter Card tags found ({found_count}/{total_required}), but missing: {', '.join(missing)}.",
            "details": {"found": found, "missing": missing},
        }

    return {
        "name": "Twitter Cards",
        "status": "pass",
        "message": f"All {total_required} core Twitter Card tags are present.",
        "details": {"found": found, "missing": []},
    }


def check_hreflang(soup):
    """Check for hreflang link tags for multi-language support.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details about hreflang tags.
        - warning: hreflang tags found but missing x-default.
        - pass: hreflang tags present including x-default.
        - pass (no hreflang): no hreflang tags (neutral — not all sites need them).
    """
    hreflang_links = soup.find_all("link", hreflang=True)

    if not hreflang_links:
        return {
            "name": "Hreflang",
            "status": "pass",
            "message": "No hreflang tags found (not required for single-language sites).",
            "details": {"languages": [], "has_x_default": False},
        }

    languages = []
    has_x_default = False

    for link in hreflang_links:
        hreflang_val = link.get("hreflang", "").strip()
        href = link.get("href", "").strip()
        if hreflang_val:
            languages.append({"hreflang": hreflang_val, "href": href})
            if hreflang_val == "x-default":
                has_x_default = True

    if not has_x_default:
        lang_codes = [l["hreflang"] for l in languages]
        return {
            "name": "Hreflang",
            "status": "warning",
            "message": f"Found {len(languages)} hreflang tag(s) ({', '.join(lang_codes)}), but no x-default fallback.",
            "details": {"languages": languages, "has_x_default": False},
        }

    return {
        "name": "Hreflang",
        "status": "pass",
        "message": f"Found {len(languages)} hreflang tag(s) including x-default.",
        "details": {"languages": languages, "has_x_default": True},
    }


def check_robots_txt(base_url):
    """Fetch and validate the site's robots.txt file.

    Args:
        base_url: The base URL of the site (used to construct /robots.txt).

    Returns:
        Dict with status, message, and details about the robots.txt file.
        - fail: robots.txt missing or empty.
        - warning: robots.txt exists but contains no directives.
        - pass: robots.txt found with valid directives.
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        response = requests.get(robots_url, timeout=5)
        if response.status_code >= 400:
            return {
                "name": "Robots.txt",
                "status": "fail",
                "message": f"robots.txt not found (HTTP {response.status_code}).",
                "details": {"url": robots_url, "status_code": response.status_code},
            }
    except requests.RequestException as exc:
        return {
            "name": "Robots.txt",
            "status": "fail",
            "message": f"Could not fetch robots.txt: {exc}",
            "details": {"url": robots_url},
        }

    content = response.text.strip()
    if not content:
        return {
            "name": "Robots.txt",
            "status": "fail",
            "message": "robots.txt exists but is empty.",
            "details": {"url": robots_url, "size": 0},
        }

    # Check for at least one directive line.
    directive_lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not directive_lines:
        return {
            "name": "Robots.txt",
            "status": "warning",
            "message": "robots.txt found but contains no directives (only comments?).",
            "details": {"url": robots_url, "lines": len(content.splitlines())},
        }

    # Extract Sitemap URLs.
    sitemaps = []
    for line in content.splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            if sitemap_url:
                sitemaps.append(sitemap_url)

    return {
        "name": "Robots.txt",
        "status": "pass",
        "message": f"robots.txt found with {len(directive_lines)} directive(s){f', {len(sitemaps)} sitemap(s)' if sitemaps else '.'}",
        "details": {"url": robots_url, "directives": len(directive_lines), "sitemaps": sitemaps},
    }


def check_sitemap(base_url, sitemap_url=None):
    """Fetch and validate the site's XML sitemap.

    Args:
        base_url: The base URL of the site (used if sitemap_url is not provided).
        sitemap_url: Optional explicit sitemap URL. If not provided, checks
            /sitemap.xml by default.

    Returns:
        Dict with status, message, and details about the sitemap.
        - fail: sitemap not found or not valid XML.
        - warning: sitemap found but empty or with no URLs.
        - pass: sitemap contains URLs.
    """
    if not sitemap_url:
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

    try:
        response = requests.get(sitemap_url, timeout=10)
        if response.status_code >= 400:
            return {
                "name": "Sitemap",
                "status": "fail",
                "message": f"Sitemap not found at {sitemap_url} (HTTP {response.status_code}).",
                "details": {"url": sitemap_url, "status_code": response.status_code},
            }
    except requests.RequestException as exc:
        return {
            "name": "Sitemap",
            "status": "fail",
            "message": f"Could not fetch sitemap: {exc}",
            "details": {"url": sitemap_url},
        }

    content = response.text.strip()
    if not content:
        return {
            "name": "Sitemap",
            "status": "fail",
            "message": "Sitemap URL returned empty content.",
            "details": {"url": sitemap_url},
        }

    # Validate XML and count URLs.
    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(content)
    except ET.ParseError:
        return {
            "name": "Sitemap",
            "status": "fail",
            "message": "Sitemap content is not valid XML.",
            "details": {"url": sitemap_url},
        }

    # Count <url> elements (standard sitemap) or <sitemap> elements (sitemap index).
    # Handle XML namespaces.
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    url_elements = root.findall(".//ns:url", ns) or root.findall(".//url")
    sitemap_elements = root.findall(".//ns:sitemap", ns) or root.findall(".//sitemap")

    url_count = len(url_elements)
    sitemap_count = len(sitemap_elements)

    if url_count == 0 and sitemap_count == 0:
        return {
            "name": "Sitemap",
            "status": "warning",
            "message": "Sitemap found but contains no URLs or sub-sitemaps.",
            "details": {"url": sitemap_url, "url_count": 0, "is_index": bool(sitemap_elements)},
        }

    if sitemap_elements:
        return {
            "name": "Sitemap",
            "status": "pass",
            "message": f"Sitemap index found with {sitemap_count} sub-sitemap(s).",
            "details": {"url": sitemap_url, "sitemap_count": sitemap_count, "is_index": True},
        }

    return {
        "name": "Sitemap",
        "status": "pass",
        "message": f"Sitemap found with {url_count} URL(s).",
        "details": {"url": sitemap_url, "url_count": url_count, "is_index": False},
    }


def check_viewport(soup):
    """Check for a viewport meta tag (mobile-friendliness signal).

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        Dict with status, message, and details about the viewport tag.
        - fail: no viewport meta tag found.
        - warning: viewport tag found but with problematic content.
        - pass: viewport tag present with valid content.
    """
    viewport = soup.find("meta", attrs={"name": "viewport"})

    if not viewport:
        return {
            "name": "Viewport",
            "status": "fail",
            "message": "No viewport <meta> tag found. Page may not be mobile-friendly.",
            "details": {},
        }

    content = viewport.get("content", "").strip()
    if not content:
        return {
            "name": "Viewport",
            "status": "fail",
            "message": "Viewport meta tag found but has no content attribute.",
            "details": {},
        }

    # Check for problematic values.
    issues = []
    content_lower = content.lower()
    if "width=device-width" not in content_lower:
        issues.append("missing 'width=device-width'")
    if "initial-scale=" not in content_lower:
        issues.append("missing 'initial-scale'")
    if "maximum-scale=1" in content_lower or "user-scalable=no" in content_lower:
        issues.append("restricts user zoom (accessibility concern)")

    if issues:
        return {
            "name": "Viewport",
            "status": "warning",
            "message": f"Viewport tag found but has issues: {', '.join(issues)}.",
            "details": {"content": content, "issues": issues},
        }

    return {
        "name": "Viewport",
        "status": "pass",
        "message": f"Viewport tag is properly configured.",
        "details": {"content": content},
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
    check_schema,
    check_open_graph,
    check_twitter_cards,
    check_hreflang,
    check_viewport,
]

# Checks that require a base_url instead of (just) soup.
URL_CHECKS = [
    check_robots_txt,
    check_sitemap,
]
