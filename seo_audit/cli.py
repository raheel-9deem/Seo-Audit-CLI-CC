"""CLI entry point for the SEO Audit tool.

This module defines the command-line interface using argparse. It accepts
a URL as input, validates it, orchestrates the scraping, checking, and
reporting pipeline, and prints the final SEO audit report.

Usage:
    python -m seo_audit.cli <url> [options]

Options:
    --output FILE      Write the report to a file.
    --format FORMAT    Output format: terminal, markdown, json, csv, html (default: terminal).
    --no-links         Skip broken link checking (faster scan).
    --wordpress        Run WordPress detection and security checks.
    --save-history     Save scan results to the local history database.
    --compare          Show a diff against the last scan of the same URL.
    --db-path PATH     Path to the history database (default: .seo_audit_history.db).
    --timeout SECONDS  Request timeout (default 10).
    --version          Show the version and exit.
"""

import json
import sys
from datetime import datetime
from urllib.parse import urlparse

from . import __version__
from .checks import ALL_CHECKS, URL_CHECKS, check_broken_links, check_links
from .config import load_config
from .crawler import crawl_site
from .history import compare_with_previous, init_db, save_scan
from .report import generate_csv_report, generate_html_report, generate_markdown_report, generate_report, print_report
from .scraper import fetch_page, parse_html
from .wordpress import check_wp_exposures, detect_wordpress, get_wp_version


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

    from .config import load_config, DEFAULTS

    # Load config for defaults.
    config = load_config()
    crawl_settings = config.get("crawl", DEFAULTS["crawl"])
    general_settings = config.get("general", DEFAULTS["general"])

    parser = argparse.ArgumentParser(
        description="Audit a web page for common SEO issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  %(prog)s example.com\n"
        "  %(prog)s https://example.com --output report.md\n"
        "  %(prog)s https://example.com --crawl --max-pages 50\n"
        "  %(prog)s https://example.com --no-links --timeout 5\n",
    )
    parser.add_argument(
        "url",
        help="The URL of the page to audit (scheme optional).",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the report to a file instead of stdout.",
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "markdown", "json", "csv", "html"],
        default="terminal",
        help="Output format (default: terminal).",
    )
    parser.add_argument(
        "--no-links",
        action="store_true",
        help="Skip broken link checking for a faster scan.",
    )
    parser.add_argument(
        "--wordpress",
        action="store_true",
        help="Run WordPress detection and security checks.",
    )
    parser.add_argument(
        "--crawl",
        action="store_true",
        help="Crawl the site and audit all discovered pages.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=crawl_settings.get("max_pages", DEFAULTS["crawl"]["max_pages"]),
        metavar="N",
        help="Maximum pages to crawl (default: 20).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=crawl_settings.get("max_depth", DEFAULTS["crawl"]["max_depth"]),
        metavar="N",
        help="Maximum crawl depth (default: 2).",
    )
    parser.add_argument(
        "--save-history",
        action="store_true",
        help="Save scan results to the local history database.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Show a diff against the last scan of the same URL.",
    )
    parser.add_argument(
        "--db-path",
        default=".seo_audit_history.db",
        metavar="PATH",
        help="Path to the history database (default: .seo_audit_history.db).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=general_settings.get("timeout", DEFAULTS["general"]["timeout"]),
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
        if args.crawl:
            # Crawl mode: crawl the site and audit all discovered pages.
            pages = crawl_site(url, max_pages=args.max_pages, max_depth=args.max_depth, timeout=args.timeout)
            if not pages:
                print("Error: No pages were discovered during crawling.", file=sys.stderr)
                sys.exit(1)

            all_results = {}
            for page in pages:
                page_soup = page["soup"]
                page_url = page["url"]
                page_results = []

                for check_fn in ALL_CHECKS:
                    try:
                        if check_fn is check_links:
                            result = check_fn(page_soup, page_url)
                        else:
                            result = check_fn(page_soup)
                        page_results.append(result)
                    except Exception as exc:
                        page_results.append({
                            "name": getattr(check_fn, "__name__", "unknown"),
                            "status": "fail",
                            "message": f"Check error: {exc}",
                            "details": {},
                        })

                # URL-based checks.
                for check_fn in URL_CHECKS:
                    try:
                        result = check_fn(page_url)
                        page_results.append(result)
                    except Exception as exc:
                        page_results.append({
                            "name": getattr(check_fn, "__name__", "unknown"),
                            "status": "fail",
                            "message": f"Check error: {exc}",
                            "details": {},
                        })

                all_results[page_url] = page_results

            # Optionally run WordPress checks for the first page.
            if args.wordpress:
                first_url = pages[0]["url"]
                first_html = pages[0]["html"]
                is_wp = detect_wordpress(first_url, first_html)
                if is_wp:
                    wp_version = get_wp_version(first_html)
                    if wp_version:
                        all_results[first_url].append({
                            "name": "WordPress Version",
                            "status": "pass",
                            "message": f"WordPress version detected: {wp_version}.",
                            "details": {"version": wp_version},
                        })
                    else:
                        all_results[first_url].append({
                            "name": "WordPress Version",
                            "status": "warning",
                            "message": "WordPress detected but version could not be determined.",
                            "details": {},
                        })
                    wp_exposures = check_wp_exposures(first_url)
                    all_results[first_url].append(wp_exposures)

            # Generate report for all crawled pages.
            if args.format == "csv":
                content = generate_csv_report(all_results)
            elif args.format == "json":
                # Flatten for JSON: include all pages.
                report = {
                    "url": url,
                    "timestamp": datetime.now().isoformat(),
                    "pages": {
                        page_url: {
                            "summary": {
                                "total": len(results),
                                "passed": sum(1 for r in results if r["status"] == "pass"),
                                "warnings": sum(1 for r in results if r["status"] == "warning"),
                                "failed": sum(1 for r in results if r["status"] == "fail"),
                            },
                            "checks": results,
                        }
                        for page_url, results in all_results.items()
                    },
                }
                content = json.dumps(report, indent=2)
            else:
                # For terminal/markdown/html, show the first page's results.
                first_url = list(all_results.keys())[0]
                results = all_results[first_url]
                if args.format == "markdown":
                    content = generate_markdown_report(first_url, results)
                elif args.format == "html":
                    content = generate_html_report(first_url, results)
                else:
                    content = generate_report(first_url, results)
                # Note: in crawl mode, only the first page is shown in terminal mode.

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Report written to {args.output}")
            else:
                try:
                    print(content)
                except UnicodeEncodeError:
                    import sys
                    buf = getattr(sys.stdout, "buffer", None)
                    if buf:
                        buf.write(content.encode(sys.stdout.encoding or "utf-8", errors="replace"))
                    else:
                        print(content.encode("ascii", errors="replace").decode("ascii"))
        else:
            # Single-page mode.
            data = fetch_page(url, timeout=args.timeout)
            if "error" in data:
                print(f"Error: {data['error']}", file=sys.stderr)
                sys.exit(1)

            html = data["html"]
            final_url = data["final_url"]

            soup = parse_html(html)
            if soup is None:
                print("Error: The page returned empty or unparseable content.", file=sys.stderr)
                sys.exit(1)

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

            # URL-based checks.
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

            # Broken link checking.
            if not args.no_links:
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

            # WordPress checks.
            is_wordpress = detect_wordpress(final_url, html)
            if is_wordpress or args.wordpress:
                wp_version = get_wp_version(html)
                if wp_version:
                    results.append({
                        "name": "WordPress Version",
                        "status": "pass",
                        "message": f"WordPress version detected: {wp_version}.",
                        "details": {"version": wp_version},
                    })
                else:
                    results.append({
                        "name": "WordPress Version",
                        "status": "warning",
                        "message": "WordPress detected but version could not be determined.",
                        "details": {},
                    })

                wp_exposures = check_wp_exposures(final_url)
                results.append(wp_exposures)

            # History comparison.
            if args.compare:
                init_db(args.db_path)
                diff = compare_with_previous(args.db_path, final_url, results)
                if diff["no_previous"]:
                    results.append({
                        "name": "History Comparison",
                        "status": "pass",
                        "message": "No previous scan found for this URL. This scan will be saved as the baseline.",
                        "details": {},
                    })
                else:
                    improved_count = len(diff["improved"])
                    worsened_count = len(diff["worsened"])
                    unchanged_count = len(diff["unchanged"])
                    if diff["previous_score"] is not None:
                        score_delta = diff["current_score"] - diff["previous_score"]
                        if score_delta > 0:
                            score_msg = f"Score improved by {score_delta} points ({diff['previous_score']} → {diff['current_score']})."
                        elif score_delta < 0:
                            score_msg = f"Score dropped by {abs(score_delta)} points ({diff['previous_score']} → {diff['current_score']})."
                        else:
                            score_msg = f"Score unchanged at {diff['current_score']}."
                    else:
                        score_msg = ""
                    results.append({
                        "name": "History Comparison",
                        "status": "warning" if worsened_count > 0 else "pass",
                        "message": f"Compared to scan on {diff['previous_date']}: {improved_count} improved, {worsened_count} worsened, {unchanged_count} unchanged. {score_msg}".strip(),
                        "details": {
                            "improved": diff["improved"],
                            "worsened": diff["worsened"],
                            "unchanged": diff["unchanged"],
                            "previous_score": diff["previous_score"],
                            "current_score": diff["current_score"],
                        },
                    })

            # Save history.
            if args.save_history:
                init_db(args.db_path)
                save_scan(args.db_path, final_url, results)

            # Generate and print the report.
            print_report(results, final_url, fmt=args.format, output=args.output)

    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"Error: An unexpected error occurred: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
