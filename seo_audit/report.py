"""Report formatting and output module.

This module takes the results from the SEO checks and formats them into
a human-readable text report or structured JSON/CSV/HTML output. It handles
both stdout printing and file output.

Exports:
    generate_report(url, results) -> str:
        Colored terminal report with summary score and grouped categories.
    generate_markdown_report(url, results) -> str:
        Markdown-formatted report for saving or sharing.
    generate_json_report(url, results) -> str:
        JSON-formatted report for programmatic consumption.
    generate_csv_report(all_results) -> str:
        CSV-formatted report for spreadsheet analysis.
    generate_html_report(url, results) -> str:
        Standalone HTML dashboard with inline CSS.
    print_report(results, url, fmt="text", output=None) -> None:
        Print or write the report in the requested format.
"""

import csv
import io
import json
from datetime import datetime



# ANSI color codes for terminal output.
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "white": "\033[97m",
}

# Category mapping: check name -> category
CATEGORIES = {
    "title tag": "Meta Tags",
    "meta description": "Meta Tags",
    "canonical": "Meta Tags",
    "robots meta": "Meta Tags",
    "headings": "Content",
    "word count": "Content",
    "images": "Content",
    "links": "Links",
}

# Status-to-color mapping
STATUS_COLORS = {
    "pass": COLORS["green"],
    "warning": COLORS["yellow"],
    "fail": COLORS["red"],
}

# Status icon mapping
STATUS_ICONS = {
    "pass": "✓",
    "warning": "⚠",
    "fail": "✗",
}


def _colorize(text, color):
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{COLORS['reset']}"


def _categorize_results(results):
    """Group results into their categories.

    Returns a dict of {category: [result, ...]}.
    """
    grouped = {}
    for r in results:
        name = r.get("name", "").lower()
        category = CATEGORIES.get(name, "Other")
        grouped.setdefault(category, []).append(r)
    return grouped


def generate_report(url, results):
    """Format all check results into a colored terminal report.

    Shows a summary score at the top (X/Y checks passed), then groups
    results by category (Meta Tags, Content, Links, Technical).

    Args:
        url: The URL that was audited.
        results: List of check result dicts with 'name', 'status',
                 'message', and optional 'details' keys.

    Returns:
        A formatted string with ANSI color codes for terminal display.
    """
    lines = []
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    warnings = sum(1 for r in results if r["status"] == "warning")
    failed = sum(1 for r in results if r["status"] == "fail")

    # Header
    lines.append("")
    lines.append(_colorize("=" * 60, COLORS["cyan"]))
    lines.append(_colorize(f"  {'SEO AUDIT REPORT':^56}", COLORS["bold"] + COLORS["white"]))
    lines.append(_colorize("=" * 60, COLORS["cyan"]))
    lines.append(f"  URL:  {url}")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Summary score
    score_color = COLORS["green"] if failed == 0 else (COLORS["yellow"] if failed < total / 2 else COLORS["red"])
    lines.append(_colorize("  SUMMARY", COLORS["bold"]))
    lines.append(_colorize(f"  {passed}/{total} checks passed", score_color))
    if warnings:
        lines.append(_colorize(f"  {warnings} warnings", COLORS["yellow"]))
    if failed:
        lines.append(_colorize(f"  {failed} failed", COLORS["red"]))
    lines.append("")

    # Grouped results by category
    grouped = _categorize_results(results)
    category_order = ["Meta Tags", "Content", "Links", "Other"]
    for category in category_order:
        if category not in grouped:
            continue
        lines.append(_colorize(f"  {category}", COLORS["bold"] + COLORS["cyan"]))
        lines.append(_colorize("  " + "-" * 40, COLORS["cyan"]))
        for r in grouped[category]:
            color = STATUS_COLORS.get(r["status"], COLORS["white"])
            icon = STATUS_ICONS.get(r["status"], "?")
            lines.append(f"  {_colorize(f'  [{icon}]', color)} {_colorize(r['name'], COLORS['white'])}")
            lines.append(f"      {r['message']}")
            if r.get("details"):
                for k, v in r["details"].items():
                    if isinstance(v, list):
                        lines.append(f"      • {k}: {len(v)} items")
                    else:
                        lines.append(f"      • {k}: {v}")
        lines.append("")

    lines.append(_colorize("=" * 60, COLORS["cyan"]))
    lines.append("")

    return "\n".join(lines)


def generate_markdown_report(url, results):
    """Format check results as a markdown document.

    Args:
        url: The URL that was audited.
        results: List of check result dicts.

    Returns:
        A markdown-formatted string suitable for saving to a .md file.
    """
    lines = []
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    warnings = sum(1 for r in results if r["status"] == "warning")
    failed = sum(1 for r in results if r["status"] == "fail")

    lines.append("# SEO Audit Report")
    lines.append("")
    lines.append(f"**URL:** `{url}`")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    score_emoji = "🟢" if failed == 0 else ("🟡" if failed < total / 2 else "🔴")
    lines.append(f"{score_emoji} **{passed}/{total} checks passed**")
    if warnings:
        lines.append(f"⚠️ **{warnings} warnings**")
    if failed:
        lines.append(f"❌ **{failed} failed**")
    lines.append("")

    # Grouped results
    grouped = _categorize_results(results)
    category_order = ["Meta Tags", "Content", "Links", "Other"]
    for category in category_order:
        if category not in grouped:
            continue
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| Status | Check | Details |")
        lines.append("|--------|-------|---------|")
        for r in grouped[category]:
            icon = STATUS_ICONS.get(r["status"], "?")
            details_str = ""
            if r.get("details"):
                parts = []
                for k, v in r["details"].items():
                    if isinstance(v, list):
                        parts.append(f"{k}: {len(v)} items")
                    else:
                        parts.append(f"{k}: {v}")
                details_str = "; ".join(parts)
            lines.append(f"| {icon} | {r['name']} | {r['message']} ({details_str}) |")
        lines.append("")

    return "\n".join(lines)


def generate_json_report(url, results):
    """Format check results as a JSON document.

    Args:
        url: The URL that was audited.
        results: List of check result dicts.

    Returns:
        A JSON string with the full report data.
    """
    report = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "pass"),
            "warnings": sum(1 for r in results if r["status"] == "warning"),
            "failed": sum(1 for r in results if r["status"] == "fail"),
        },
        "categories": _categorize_results(results),
        "checks": results,
    }
    return json.dumps(report, indent=2)


def generate_csv_report(all_results):
    """Format check results as CSV rows for spreadsheet analysis.

    Each check result becomes one row with columns for URL, check name,
    status, message, and key detail fields.

    Args:
        all_results: A dict mapping page URLs to their result lists, or
            a single list of results for one page.

    Returns:
        A CSV-formatted string with header row.
    """
    # Normalize input: accept either {url: [results]} or a flat [results].
    if isinstance(all_results, list):
        all_results = {"": all_results}

    fieldnames = ["url", "check", "status", "message", "details"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for url, results in all_results.items():
        for r in results:
            details = r.get("details", {})
            # Flatten details into a semicolon-separated string.
            details_str = "; ".join(
                f"{k}={v}" if not isinstance(v, (list, dict)) else f"{k}={json.dumps(v)}"
                for k, v in details.items()
            )
            writer.writerow({
                "url": url,
                "check": r.get("name", ""),
                "status": r.get("status", ""),
                "message": r.get("message", ""),
                "details": details_str,
            })

    return output.getvalue()


def generate_html_report(url, results):
    """Format check results as a standalone HTML dashboard.

    Generates a self-contained HTML file with inline CSS — no external
    dependencies. Shows a score summary at the top, then color-coded
    sections grouped by category.

    Args:
        url: The URL that was audited.
        results: List of check result dicts.

    Returns:
        A complete HTML string.
    """
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    warnings = sum(1 for r in results if r["status"] == "warning")
    failed = sum(1 for r in results if r["status"] == "fail")
    score_pct = round((passed / total) * 100) if total else 0

    # Determine overall score color.
    if failed == 0:
        score_color = "#22c55e"
    elif failed < total / 2:
        score_color = "#eab308"
    else:
        score_color = "#ef4444"

    status_styles = {
        "pass": {"bg": "#dcfce7", "border": "#22c55e", "text": "#166534"},
        "warning": {"bg": "#fef9c3", "border": "#eab308", "text": "#854d0e"},
        "fail": {"bg": "#fee2e2", "border": "#ef4444", "text": "#991b1b"},
    }

    grouped = _categorize_results(results)
    category_order = ["Meta Tags", "Content", "Links", "Other"]
    # Put uncategorized first.
    for cat in list(grouped.keys()):
        if cat not in category_order:
            category_order.append(cat)

    categories_html = ""
    for category in category_order:
        if category not in grouped:
            continue
        items_html = ""
        for r in grouped[category]:
            style = status_styles.get(r["status"], status_styles["pass"])
            icon = STATUS_ICONS.get(r["status"], "?")
            details_html = ""
            if r.get("details"):
                details_list = []
                for k, v in r["details"].items():
                    if isinstance(v, list):
                        details_list.append(f"<b>{k}:</b> {len(v)} items")
                    else:
                        details_list.append(f"<b>{k}:</b> {v}")
                details_html = f'<div class="details">{"; ".join(details_list)}</div>'
            items_html += f"""
                <div class="check-item" style="background:{style['bg']};border-left:4px solid {style['border']}">
                    <div class="check-header">
                        <span class="check-icon" style="color:{style['text']}">{icon}</span>
                        <span class="check-name">{r['name']}</span>
                        <span class="check-status" style="color:{style['text']}">{r['status'].upper()}</span>
                    </div>
                    <div class="check-message">{r['message']}</div>
                    {details_html}
                </div>"""
        categories_html += f"""
            <div class="category">
                <h2>{category}</h2>
                {items_html}
            </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEO Audit Report — {url}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; background: #f9fafb; padding: 2rem; }}
.container {{ max-width: 800px; margin: 0 auto; }}
h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; color: #111827; }}
.subtitle {{ color: #6b7280; margin-bottom: 1.5rem; }}
.score-card {{ background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.score-row {{ display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }}
.score-circle {{ width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; font-weight: 700; color: #fff; background: {score_color}; flex-shrink: 0; }}
.score-text {{ flex: 1; min-width: 200px; }}
.score-text h2 {{ font-size: 1.25rem; margin-bottom: 0.25rem; }}
.score-meta {{ color: #6b7280; font-size: 0.875rem; }}
.score-badges {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
.badge {{ padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }}
.badge-pass {{ background: #dcfce7; color: #166534; }}
.badge-warn {{ background: #fef9c3; color: #854d0e; }}
.badge-fail {{ background: #fee2e2; color: #991b1b; }}
.category {{ margin-bottom: 2rem; }}
.category h2 {{ font-size: 1.125rem; color: #374151; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 2px solid #e5e7eb; }}
.check-item {{ background: #f9fafb; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }}
.check-header {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }}
.check-icon {{ font-size: 1.25rem; font-weight: 700; }}
.check-name {{ font-weight: 600; flex: 1; }}
.check-status {{ font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em; }}
.check-message {{ color: #4b5563; font-size: 0.875rem; }}
.details {{ color: #6b7280; font-size: 0.8rem; margin-top: 0.5rem; }}
</style>
</head>
<body>
<div class="container">
    <h1>SEO Audit Report</h1>
    <p class="subtitle">URL: <code>{url}</code> &bull; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="score-card">
        <div class="score-row">
            <div class="score-circle">{score_pct}%</div>
            <div class="score-text">
                <h2>Overall Score</h2>
                <p class="score-meta">{passed} of {total} checks passed</p>
                <div class="score-badges">
                    <span class="badge badge-pass">{passed} passed</span>
                    <span class="badge badge-warn">{warnings} warnings</span>
                    <span class="badge badge-fail">{failed} failed</span>
                </div>
            </div>
        </div>
    </div>

    {categories_html}
</div>
</body>
</html>"""
    return html


def print_report(results, url, fmt="text", output=None):
    """Print or write the SEO audit report.

    Args:
        results: List of check result dicts.
        url: The URL that was audited.
        fmt: Output format — "text", "json", "csv", "html", or "markdown".
        output: Optional file path. If None, prints to stdout.
    """
    if fmt == "json":
        content = generate_json_report(url, results)
    elif fmt == "csv":
        content = generate_csv_report({url: results})
    elif fmt == "html":
        content = generate_html_report(url, results)
    elif fmt == "markdown":
        content = generate_markdown_report(url, results)
    else:
        content = generate_report(url, results)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Report written to {output}")
    else:
        # Use UTF-8 for stdout to support emoji and special characters.
        # This handles Windows console encoding issues.
        try:
            print(content)
        except UnicodeEncodeError:
            # Fallback: encode to stdout's encoding, replacing unknown chars.
            import sys
            buf = getattr(sys.stdout, "buffer", None)
            if buf:
                buf.write(content.encode(sys.stdout.encoding or "utf-8", errors="replace"))
            else:
                print(content.encode("ascii", errors="replace").decode("ascii"))
