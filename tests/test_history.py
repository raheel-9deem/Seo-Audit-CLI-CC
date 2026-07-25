"""Tests for seo_audit.history module.

Run with: pytest tests/test_history.py -v
"""

import json
import os
import tempfile

import pytest

from seo_audit.history import (
    init_db,
    save_scan,
    compare_with_previous,
    get_previous_scans,
)


@pytest.fixture
def tmp_db():
    """Create a temporary database file for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def _make_results(status_list):
    """Helper to create a list of result dicts from a list of statuses.

    Args:
        status_list: List of (name, status) tuples.

    Returns:
        List of result dicts.
    """
    return [
        {"name": name, "status": status, "message": f"{name} message", "details": {}}
        for name, status in status_list
    ]


class TestInitDb:
    def test_creates_database(self, tmp_db):
        init_db(tmp_db)
        assert os.path.exists(tmp_db)

    def test_idempotent(self, tmp_db):
        init_db(tmp_db)
        init_db(tmp_db)  # Should not raise.
        assert os.path.exists(tmp_db)


class TestSaveScan:
    def test_saves_scan(self, tmp_db):
        init_db(tmp_db)
        results = _make_results([("Title Tag", "pass"), ("Meta Description", "fail")])
        save_scan(tmp_db, "https://example.com", results)
        # Verify by reading back.
        scans = get_previous_scans(tmp_db, "https://example.com")
        assert len(scans) == 1

    def test_multiple_scans(self, tmp_db):
        init_db(tmp_db)
        results = _make_results([("Title Tag", "pass")])
        save_scan(tmp_db, "https://example.com", results)
        save_scan(tmp_db, "https://example.com", results)
        scans = get_previous_scans(tmp_db, "https://example.com", limit=10)
        assert len(scans) == 2


class TestCompareWithPrevious:
    def test_no_previous_scan(self, tmp_db):
        init_db(tmp_db)
        results = _make_results([("Title Tag", "pass")])
        diff = compare_with_previous(tmp_db, "https://example.com", results)
        assert diff["no_previous"] is True
        assert diff["previous_score"] is None
        assert diff["previous_date"] is None

    def test_improved_checks(self, tmp_db):
        init_db(tmp_db)
        # First scan: one fail, one warning.
        old_results = _make_results([("Title Tag", "fail"), ("Meta Description", "warning")])
        save_scan(tmp_db, "https://example.com", old_results)

        # Second scan: both improved.
        new_results = _make_results([("Title Tag", "pass"), ("Meta Description", "pass")])
        diff = compare_with_previous(tmp_db, "https://example.com", new_results)

        assert "Title Tag" in diff["improved"]
        assert "Meta Description" in diff["improved"]
        assert len(diff["worsened"]) == 0
        assert diff["current_score"] > diff["previous_score"]

    def test_worsened_checks(self, tmp_db):
        init_db(tmp_db)
        old_results = _make_results([("Title Tag", "pass"), ("Meta Description", "pass")])
        save_scan(tmp_db, "https://example.com", old_results)

        new_results = _make_results([("Title Tag", "fail"), ("Meta Description", "warning")])
        diff = compare_with_previous(tmp_db, "https://example.com", new_results)

        assert "Title Tag" in diff["worsened"]
        assert "Meta Description" in diff["worsened"]
        assert len(diff["improved"]) == 0

    def test_unchanged_checks(self, tmp_db):
        init_db(tmp_db)
        results = _make_results([("Title Tag", "pass"), ("Meta Description", "pass")])
        save_scan(tmp_db, "https://example.com", results)

        diff = compare_with_previous(tmp_db, "https://example.com", results)

        assert "Title Tag" in diff["unchanged"]
        assert "Meta Description" in diff["unchanged"]
        assert len(diff["improved"]) == 0
        assert len(diff["worsened"]) == 0

    def test_mixed_changes(self, tmp_db):
        init_db(tmp_db)
        old_results = _make_results([
            ("Title Tag", "pass"),
            ("Meta Description", "pass"),
            ("Headings", "fail"),
        ])
        save_scan(tmp_db, "https://example.com", old_results)

        new_results = _make_results([
            ("Title Tag", "pass"),         # unchanged
            ("Meta Description", "fail"),  # worsened
            ("Headings", "pass"),          # improved
        ])
        diff = compare_with_previous(tmp_db, "https://example.com", new_results)

        assert "Title Tag" in diff["unchanged"]
        assert "Meta Description" in diff["worsened"]
        assert "Headings" in diff["improved"]

    def test_skips_nonexistent_url(self, tmp_db):
        init_db(tmp_db)
        results = _make_results([("Title Tag", "pass")])
        diff = compare_with_previous(tmp_db, "https://other.com", results)
        assert diff["no_previous"] is True


class TestGetPreviousScans:
    def test_returns_empty_for_new_url(self, tmp_db):
        init_db(tmp_db)
        scans = get_previous_scans(tmp_db, "https://newsite.com")
        assert scans == []

    def test_respects_limit(self, tmp_db):
        init_db(tmp_db)
        results = _make_results([("Title Tag", "pass")])
        for _ in range(5):
            save_scan(tmp_db, "https://example.com", results)
        scans = get_previous_scans(tmp_db, "https://example.com", limit=3)
        assert len(scans) == 3

    def test_returns_expected_keys(self, tmp_db):
        init_db(tmp_db)
        results = _make_results([("Title Tag", "pass")])
        save_scan(tmp_db, "https://example.com", results)
        scans = get_previous_scans(tmp_db, "https://example.com")
        assert "scan_date" in scans[0]
        assert "overall_score" in scans[0]
