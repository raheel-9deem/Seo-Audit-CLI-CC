"""Report formatting and output module.

This module takes the results from the SEO checks and formats them into
a human-readable text report or structured JSON/markdown output. It handles
both stdout printing and file output.

Exports:
    generate_report(url, results) -> str:
        Colored terminal report with summary score and grouped categories.
    generate_markdown_report(url, results) -> str:
        Markdown-formatted report for saving or sharing.
    generate_json_report(url, results) -> str:
        JSON-formatted report for programmatic consumption.
    print_report(results, url, fmt="text", output=None) -> None:
        Print or write the report in the requested format.
"""

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


def print_report(results, url, fmt="text", output=None):
    """Print or write the SEO audit report.

    Args:
        results: List of check result dicts.
        url: The URL that was audited.
        fmt: Output format — "text", "json", or "markdown".
        output: Optional file path. If None, prints to stdout.
    """
    if fmt == "json":
        content = generate_json_report(url, results)
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
