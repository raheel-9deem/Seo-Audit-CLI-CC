"""CLI entry point for the SEO Audit tool.

This module defines the command-line interface using argparse. It accepts
a URL as input, validates it, orchestrates the scraping, checking, and
reporting pipeline, and prints the final SEO audit report.

Usage:
    python -m seo_audit.cli <url> [options]

Options:
    --output FILE      Write the markdown report to a file.
    --no-links         Skip broken link checking (faster scan).
    --timeout SECONDS  Request timeout (default 10).
    --version          Show the version and exit.
"""

import sys
from urllib.parse import urlparse

from . import __version__
from .checks import ALL_CHECKS, URL_CHECKS, check_broken_links, check_links
from .report import print_report
from .scraper import fetch_page, parse_html


def normalize_url(url):
    """Add https:// scheme if missing and return the normalized URL.

    Args:
        url: A URL string, optionally without a scheme.

    Returns:
        The URL with a scheme prepended if necessary.
    """
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


def create_parser():
    """Create and return the argument parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit a web page for common SEO issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  %(prog)s example.com\n"
        "  %(prog)s https://example.com --output report.md\n"
        "  %(prog)s https://example.com --no-links --timeout 5\n",
    )
    parser.add_argument(
        "url",
        help="The URL of the page to audit (scheme optional).",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the markdown report to a file instead of stdout.",
    )
    parser.add_argument(
        "--no-links",
        action="store_true",
        help="Skip broken link checking for a faster scan.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        metavar="SECONDS",
        help="Request timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main():
    """Main entry point for the CLI.

    Parses arguments, validates the URL, fetches the page, runs all SEO
    checks (optionally including broken link checking), and outputs the
    report. All unexpected errors are caught and shown as clean messages.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Normalize the URL — add https:// if no scheme was provided.
    url = normalize_url(args.url)

    # Validate that it looks like a valid URL after normalization.
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        print(f"Error: '{args.url}' is not a valid URL.", file=sys.stderr)
        sys.exit(1)

    try:
        # Fetch the page.
        data = fetch_page(url, timeout=args.timeout)
        if "error" in data:
            print(f"Error: {data['error']}", file=sys.stderr)
            sys.exit(1)

        html = data["html"]
        final_url = data["final_url"]

        # Parse the HTML.
        soup = parse_html(html)
        if soup is None:
            print("Error: The page returned empty or unparseable content.", file=sys.stderr)
            sys.exit(1)

        # Run all standard checks (soup-based).
        results = []
        for check_fn in ALL_CHECKS:
            try:
                if check_fn is check_links:
                    result = check_fn(soup, final_url)
                else:
                    result = check_fn(soup)
                results.append(result)
            except Exception as exc:
                results.append({
                    "name": getattr(check_fn, "__name__", "unknown"),
                    "status": "fail",
                    "message": f"Check error: {exc}",
                    "details": {},
                })

        # Run URL-based checks (require base_url, not soup).
        for check_fn in URL_CHECKS:
            try:
                result = check_fn(final_url)
                results.append(result)
            except Exception as exc:
                results.append({
                    "name": getattr(check_fn, "__name__", "unknown"),
                    "status": "fail",
                    "message": f"Check error: {exc}",
                    "details": {},
                })

        # Optionally run broken link checking.
        if not args.no_links:
            # Collect all absolute links from the page for broken-link checking.
            all_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith(("http://", "https://")):
                    all_links.append(href)

            if all_links:
                broken = check_broken_links(all_links)
                if broken:
                    results.append({
                        "name": "Broken Links",
                        "status": "fail",
                        "message": f"{len(broken)} broken link(s) found.",
                        "details": {"broken": broken[:10]},
                    })
                else:
                    results.append({
                        "name": "Broken Links",
                        "status": "pass",
                        "message": f"All {len(all_links)} links are reachable.",
                        "details": {"checked": len(all_links)},
                    })

        # Generate and print the report.
        print_report(results, final_url, fmt="markdown", output=args.output)

    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"Error: An unexpected error occurred: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
