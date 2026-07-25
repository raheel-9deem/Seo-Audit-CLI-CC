"""WordPress detection and security checks for the SEO Audit tool.

This module provides functions to detect WordPress sites, check for
common security exposures, and extract the WordPress version.
"""

import re
from urllib.parse import urljoin

import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def detect_wordpress(base_url, html):
    """Check if a site appears to be powered by WordPress.

    Uses multiple heuristics: presence of wp-content paths, wp-json API
    links, and the WordPress generator meta tag.

    Args:
        base_url: The base URL of the site (used for link analysis).
        html: The raw HTML content of the page.

    Returns:
        True if WordPress signatures are detected, False otherwise.
    """
    if not html:
        return False

    html_lower = html.lower()

    # Check 1: wp-content or wp-includes in the HTML (themes, plugins, uploads).
    if "wp-content" in html_lower or "wp-includes" in html_lower:
        return True

    # Check 2: wp-json API link in the HTML.
    if "wp-json" in html_lower:
        return True

    # Check 3: Generator meta tag containing "WordPress".
    if "wordpress" in html_lower:
        # Look for the generator meta tag specifically.
        generator_match = re.search(
            r'<meta\s[^>]*name=["\']generator["\'][^>]*content=["\']([^"\']*)["\'][^>]*>',
            html,
            re.IGNORECASE,
        )
        if generator_match and "wordpress" in generator_match.group(1).lower():
            return True
        # Also check the reverse order (content before name).
        generator_match = re.search(
            r'<meta\s[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']generator["\'][^>]*>',
            html,
            re.IGNORECASE,
        )
        if generator_match and "wordpress" in generator_match.group(1).lower():
            return True

    return False


def check_wp_exposures(base_url):
    """Check for publicly accessible WordPress files that pose security risks.

    Checks four common paths:
        - /wp-config.php.bak: Backup config file that may expose database credentials.
        - /readme.html: Reveals the WordPress version (should be removed).
        - /wp-json/: REST API endpoint (information disclosure, potential attack surface).
        - /xmlrpc.php: XML-RPC endpoint (common brute-force and DDoS vector).

    Args:
        base_url: The base URL of the WordPress site.

    Returns:
        Dict with status, message, and details about exposed paths.
        - pass: no risky files exposed.
        - warning: some non-critical paths accessible.
        - fail: critical security exposures found.
    """
    paths_to_check = {
        "/wp-config.php.bak": {
            "severity": "critical",
            "message": "Backup config file exposed — may contain database credentials.",
        },
        "/readme.html": {
            "severity": "medium",
            "message": "readme.html accessible — reveals WordPress version.",
        },
        "/wp-json/": {
            "severity": "low",
            "message": "REST API enabled — information disclosure risk.",
        },
        "/xmlrpc.php": {
            "severity": "high",
            "message": "XML-RPC enabled — common brute-force and DDoS attack vector.",
        },
    }

    exposures = []

    for path, info in paths_to_check.items():
        url = urljoin(base_url, path)
        try:
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code < 400:
                exposures.append({
                    "path": path,
                    "status_code": response.status_code,
                    "severity": info["severity"],
                    "message": info["message"],
                })
        except requests.RequestException:
            pass

    if not exposures:
        return {
            "name": "WordPress Security",
            "status": "pass",
            "message": "No common WordPress security exposures detected.",
            "details": {"exposures": []},
        }

    # Determine overall status based on the worst severity found.
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    worst_severity = max(exposures, key=lambda e: severity_order.get(e["severity"], 0))

    if worst_severity["severity"] in ("critical", "high"):
        status = "fail"
    else:
        status = "warning"

    exposed_paths = [e["path"] for e in exposures]
    return {
        "name": "WordPress Security",
        "status": status,
        "message": f"{len(exposures)} WordPress exposure(ies) found: {', '.join(exposed_paths)}.",
        "details": {"exposures": exposures},
    }


def get_wp_version(html):
    """Extract the WordPress version from page HTML.

    Looks for the version in:
        1. The generator meta tag (most common).
        2. The content of /readme.html if accessible.

    Args:
        html: The raw HTML content of the page.

    Returns:
        The WordPress version as a string (e.g., "6.4.2"), or None if
        the version cannot be determined.
    """
    if not html:
        return None

    # Check 1: Generator meta tag.
    # Matches: <meta name="generator" content="WordPress 6.4.2" />
    generator_match = re.search(
        r'<meta\s[^>]*name=["\']generator["\'][^>]*content=["\']([^"\']*)["\'][^>]*>',
        html,
        re.IGNORECASE,
    )
    if not generator_match:
        # Try reverse attribute order.
        generator_match = re.search(
            r'<meta\s[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']generator["\'][^>]*>',
            html,
            re.IGNORECASE,
        )

    if generator_match:
        content = generator_match.group(1)
        version_match = re.search(r"WordPress\s+([\d.]+)", content, re.IGNORECASE)
        if version_match:
            return version_match.group(1)

    return None
