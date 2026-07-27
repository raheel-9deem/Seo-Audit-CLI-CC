# SEO Audit CLI

A command-line tool for auditing web pages for common SEO issues. Written in Python with speed and accuracy in mind.

## Features

### Core SEO Checks
- **Title Tag** — checks presence and optimal length (30–60 chars)
- **Meta Description** — validates length (120–160 chars) and presence
- **Heading Structure** — verifies H1 presence, uniqueness, and hierarchy
- **Image Alt Text** — flags images missing `alt` attributes
- **Word Count** — warns if page has fewer than 300 words
- **Internal/External Links** — counts and categorizes links
- **Broken Links** — parallel checking with HEAD requests (optional)
- **Canonical Tag** — checks for proper canonicalization
- **Robots Meta** — detects `noindex`/`nofollow` directives
- **Schema.org** — detects JSON-LD and microdata structured data
- **Open Graph** — validates og:title, og:description, og:image, og:url
- **Twitter Cards** — validates twitter:card, twitter:title, twitter:description
- **Hreflang** — detects multi-language link tags, flags missing x-default
- **Viewport** — checks mobile-friendly viewport configuration
- **Robots.txt** — validates presence and directives, extracts sitemap URLs
- **Sitemap** — validates XML sitemap structure and URL count

### WordPress Security
- **Auto-detection** — identifies WordPress sites via signatures (wp-content, wp-json, generator tag)
- **Version detection** — extracts WordPress version from meta tags
- **Security exposures** — flags publicly accessible wp-config.php.bak, readme.html, xmlrpc.php, and wp-json/

### Advanced Features
- **Site-wide crawling** — BFS-based crawler with depth and page limits
- **History tracking** — save scans locally and compare against previous results
- **Multiple output formats** — terminal (colored), markdown, JSON, CSV, HTML dashboard
- **Configurable thresholds** — customize min/max lengths via YAML config file

## Installation

Requires Python 3.8+.

```bash
# Clone or download the project, then:
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Audit a URL (scheme is optional)
python -m seo_audit.cli example.com

# Audit with HTTPS URL
python -m seo_audit.cli https://example.com

# Save the report to a file
python -m seo_audit.cli https://example.com --output report.md

# Output as JSON
python -m seo_audit.cli https://example.com --format json --output report.json

# Output as HTML dashboard
python -m seo_audit.cli https://example.com --format html --output report.html

# Skip broken link checking for a faster scan
python -m seo_audit.cli https://example.com --no-links

# Customize request timeout
python -m seo_audit.cli https://example.com --timeout 5

# Show version
python -m seo_audit.cli --version
```

### WordPress Security Checks

```bash
# Force WordPress checks (even if auto-detection fails)
python -m seo_audit.cli https://wordpress-site.com --wordpress

# Auto-detection runs automatically when WordPress signatures are found
python -m seo_audit.cli https://wordpress-site.com
```

### Crawling Multiple Pages

```bash
# Crawl a site and audit all discovered pages
python -m seo_audit.cli https://example.com --crawl

# Limit crawl scope
python -m seo_audit.cli https://example.com --crawl --max-pages 50 --max-depth 3
```

### History Tracking & Comparison

```bash
# Save scan results to local history
python -m seo_audit.cli https://example.com --save-history

# Compare against the previous scan of the same URL
python -m seo_audit.cli https://example.com --compare

# Both save and compare
python -m seo_audit.cli https://example.com --save-history --compare

# Use a custom database path
python -m seo_audit.cli https://example.com --save-history --db-path /path/to/history.db
```

### Output Formats

| Format | Description | Best For |
|--------|-------------|----------|
| `terminal` | Colored ANSI output | Interactive use |
| `markdown` | Markdown document | Documentation, GitHub |
| `json` | Structured JSON | Programmatic processing |
| `csv` | CSV rows | Spreadsheet analysis |
| `html` | Styled dashboard | Client reports, sharing |

```bash
# Generate multiple formats
python -m seo_audit.cli https://example.com --format json --output report.json
python -m seo_audit.cli https://example.com --format html --output dashboard.html
python -m seo_audit.cli https://example.com --format csv --output results.csv
```

## Options

| Flag | Description |
|------|-------------|
| `url` | Target URL (scheme optional; `https://` is prepended if missing) |
| `--output FILE` | Write the report to a file instead of stdout |
| `--format FORMAT` | Output format: `terminal`, `markdown`, `json`, `csv`, `html` (default: `terminal`) |
| `--no-links` | Skip broken link checking (faster scan) |
| `--wordpress` | Force WordPress detection and security checks |
| `--crawl` | Crawl the site and audit all discovered pages |
| `--max-pages N` | Maximum pages to crawl (default: 20) |
| `--max-depth N` | Maximum crawl depth (default: 2) |
| `--save-history` | Save scan results to the local history database |
| `--compare` | Show a diff against the last scan of the same URL |
| `--db-path PATH` | Path to the history database (default: `.seo_audit_history.db`) |
| `--timeout SECONDS` | Request timeout (default: 10) |
| `--version` | Show version and exit |

## Configuration

Create a `.seoauditrc.yaml` file in your project directory (or `~/.seoauditrc.yaml` / `~/.config/seo-audit/config.yaml`) to customize thresholds:

```yaml
# .seoauditrc.yaml
thresholds:
  title_min_length: 30      # Minimum title length (default: 30)
  title_max_length: 60      # Maximum title length (default: 60)
  meta_description_min_length: 120  # Min meta description length (default: 120)
  meta_description_max_length: 160  # Max meta description length (default: 160)
  word_count_minimum: 300   # Minimum word count (default: 300)

crawl:
  max_pages: 20             # Default max pages for --crawl (default: 20)
  max_depth: 2              # Default max depth for --crawl (default: 2)

general:
  timeout: 10               # Default request timeout (default: 10)
```

The config file is optional — all values have sensible defaults matching the original hardcoded behavior.

## Sample Output

### Terminal (Markdown format shown)

```markdown
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

### HTML Dashboard

The `--format html` flag generates a standalone HTML file with:
- Large percentage score circle at the top
- Color-coded pass/warning/fail badges
- Grouped categories (Meta Tags, Content, Links, etc.)
- Inline CSS — no external dependencies

## Project Structure

```
seo_audit/
├── __init__.py      # Package metadata and version
├── cli.py           # CLI entry point (argparse)
├── scraper.py       # HTML fetching and parsing
├── checks.py        # Individual SEO check functions
├── crawler.py       # BFS site crawler
├── report.py        # Report formatting (text, JSON, markdown, CSV, HTML)
├── history.py       # SQLite scan history and comparison
├── wordpress.py     # WordPress detection and security checks
└── config.py        # YAML configuration loader

tests/
├── test_checks.py   # Tests for check functions
├── test_crawler.py  # Tests for crawler (mocked)
└── test_history.py  # Tests for history module

requirements.txt
README.md
```

## Running Tests

```bash
pytest tests/ -v
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Audit completed successfully |
| 1 | Error (invalid URL, network failure, etc.) |
| 130 | Aborted by user (Ctrl+C) |

## Credits

Made with 🤍, By Raheel Nadeem.

## License

MIT
