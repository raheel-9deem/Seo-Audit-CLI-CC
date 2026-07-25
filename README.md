# SEO Audit CLI

A command-line tool for auditing web pages for common SEO issues. Written in Python with speed and accuracy in mind.

## Features

- **Title Tag** — checks presence and optimal length (30–60 chars)
- **Meta Description** — validates length (120–160 chars) and presence
- **Heading Structure** — verifies H1 presence, uniqueness, and hierarchy
- **Image Alt Text** — flags images missing `alt` attributes
- **Word Count** — warns if page has fewer than 300 words
- **Internal/External Links** — counts and categorizes links
- **Broken Links** — parallel checking with HEAD requests (optional)
- **Canonical Tag** — checks for proper canonicalization
- **Robots Meta** — detects `noindex`/`nofollow` directives

## Installation

Requires Python 3.8+.

```bash
# Clone or download the project, then:
pip install -r requirements.txt
```

## Usage

```bash
# Basic usage — audit a URL (scheme is optional)
python -m seo_audit.cli example.com

# Audit with HTTPS URL
python -m seo_audit.cli https://example.com

# Save the markdown report to a file
python -m seo_audit.cli https://example.com --output report.md

# Skip broken link checking for a faster scan
python -m seo_audit.cli https://example.com --no-links

# Customize request timeout
python -m seo_audit.cli https://example.com --timeout 5

# Show version
python -m seo_audit.cli --version
```

## Options

| Flag | Description |
|------|-------------|
| `url` | Target URL (scheme optional; `https://` is prepended if missing) |
| `--output FILE` | Write the markdown report to a file instead of stdout |
| `--no-links` | Skip broken link checking (faster scan) |
| `--timeout SECONDS` | Request timeout (default: 10) |
| `--version` | Show version and exit |

## Sample Output

```
# SEO Audit Report

**URL:** `https://example.com/`
**Date:** 2026-07-24 22:18:32

## Summary

🟡 **3/8 checks passed**
⚠️ **1 warnings**
❌ **4 failed**

## Meta Tags

| Status | Check | Details |
|--------|-------|---------|
| ⚠ | Title Tag | Title is too short (14 chars). Minimum recommended: 30. |
| ✗ | Meta Description | No meta description tag found. |
| ✗ | Canonical | No canonical <link> tag found. |
| ✓ | Robots Meta | No robots meta tag found (defaults to index, follow). |

## Content

| Status | Check | Details |
|--------|-------|---------|
| ✓ | Headings | Heading structure looks good. H1: 'Example Domain...' |
| ⚠ | Images | No <img> tags found on the page. |
| ✗ | Word Count | Page has only 21 words. Recommended minimum: 300. |

## Links

| Status | Check | Details |
|--------|-------|---------|
| ✓ | Links | Found 1 links (0 internal, 1 external). |
```

## Project Structure

```
seo_audit/
├── __init__.py    # Package metadata and version
├── cli.py         # CLI entry point (argparse)
├── scraper.py     # HTML fetching and parsing
├── checks.py      # Individual SEO check functions
└── report.py      # Report formatting (text, JSON, markdown)

tests/
└── test_checks.py # Pytest test suite (45 tests)

requirements.txt
README.md
```

## Running Tests

```bash
pytest tests/test_checks.py -v
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Audit completed successfully |
| 1 | Error (invalid URL, network failure, etc.) |
| 130 | Aborted by user (Ctrl+C) |

## License

MIT
