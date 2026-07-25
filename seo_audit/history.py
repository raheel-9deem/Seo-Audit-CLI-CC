"""Scan history module using SQLite for persisting and comparing SEO audit results.

This module provides a lightweight local database for storing scan results
and comparing current scans against previous ones to track improvements
or regressions.

Exports:
    init_db(db_path) — creates the database and table if they don't exist.
    save_scan(db_path, url, results) — saves a scan result.
    compare_with_previous(db_path, url, current_results) — returns a diff dict.
    get_previous_scans(db_path, url, limit=5) — lists recent scans for a URL.
"""

import json
import sqlite3
from datetime import datetime


def init_db(db_path=".seo_audit_history.db"):
    """Create the database and scans table if they don't exist.

    Args:
        db_path: Path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            scan_date TEXT NOT NULL,
            overall_score INTEGER NOT NULL,
            results_json TEXT NOT NULL
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_scans_url_date ON scans(url, scan_date DESC)"
    )
    conn.commit()
    conn.close()


def _compute_overall_score(results):
    """Compute an overall score (0-100) from check results.

    Args:
        results: List of check result dicts with a 'status' key.

    Returns:
        Integer score from 0 to 100.
    """
    if not results:
        return 0
    score_map = {"pass": 100, "warning": 50, "fail": 0}
    total = sum(score_map.get(r.get("status", ""), 0) for r in results)
    return round(total / len(results))


def save_scan(db_path, url, results):
    """Save a scan result to the database.

    Args:
        db_path: Path to the SQLite database file.
        url: The URL that was audited.
        results: List of check result dicts.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    score = _compute_overall_score(results)
    scan_date = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO scans (url, scan_date, overall_score, results_json) VALUES (?, ?, ?, ?)",
        (url, scan_date, score, json.dumps(results)),
    )
    conn.commit()
    conn.close()


def compare_with_previous(db_path, url, current_results):
    """Compare current scan results against the most recent previous scan.

    Args:
        db_path: Path to the SQLite database file.
        url: The URL that was audited.
        current_results: List of check result dicts from the current scan.

    Returns:
        Dict with keys:
            - improved: list of check names that went from worse to better
            - worsened: list of check names that went from better to worse
            - unchanged: list of check names with the same status
            - previous_score: overall score of the previous scan (or None)
            - current_score: overall score of the current scan
            - previous_date: ISO date string of the previous scan (or None)
            - no_previous: True if no previous scan was found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT scan_date, overall_score, results_json FROM scans "
        "WHERE url = ? ORDER BY scan_date DESC LIMIT 1",
        (url,),
    )
    row = cursor.fetchone()
    conn.close()

    current_score = _compute_overall_score(current_results)

    if row is None:
        return {
            "improved": [],
            "worsened": [],
            "unchanged": [],
            "previous_score": None,
            "current_score": current_score,
            "previous_date": None,
            "no_previous": True,
        }

    previous_date, previous_score, previous_json = row
    previous_results = json.loads(previous_json)

    # Build lookup by check name.
    prev_by_name = {r.get("name", ""): r.get("status", "") for r in previous_results}
    curr_by_name = {r.get("name", ""): r.get("status", "") for r in current_results}

    # Status ranking for comparison.
    rank = {"pass": 3, "warning": 2, "fail": 1}

    improved = []
    worsened = []
    unchanged = []

    all_names = set(prev_by_name.keys()) | set(curr_by_name.keys())
    for name in all_names:
        prev_status = prev_by_name.get(name, "unknown")
        curr_status = curr_by_name.get(name, "unknown")
        if prev_status == curr_status:
            unchanged.append(name)
        else:
            prev_rank = rank.get(prev_status, 0)
            curr_rank = rank.get(curr_status, 0)
            if curr_rank > prev_rank:
                improved.append(name)
            elif curr_rank < prev_rank:
                worsened.append(name)
            else:
                unchanged.append(name)

    return {
        "improved": improved,
        "worsened": worsened,
        "unchanged": unchanged,
        "previous_score": previous_score,
        "current_score": current_score,
        "previous_date": previous_date,
        "no_previous": False,
    }


def get_previous_scans(db_path, url, limit=5):
    """Get the most recent previous scans for a URL.

    Args:
        db_path: Path to the SQLite database file.
        url: The URL to look up.
        limit: Maximum number of scans to return (default 5).

    Returns:
        List of dicts with keys: scan_date, overall_score.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT scan_date, overall_score FROM scans "
        "WHERE url = ? ORDER BY scan_date DESC LIMIT ?",
        (url, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"scan_date": row[0], "overall_score": row[1]}
        for row in rows
    ]
