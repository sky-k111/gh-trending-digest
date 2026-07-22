"""Tests for store module."""
import json
import os
import sys
import tempfile
import pytest

# Ensure src/ is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from store import (
    load_seen, save_seen, is_seen, mark_seen,
    load_history, add_history_entry, get_history_for_period,
)


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Redirect DATA_DIR to a temp directory."""
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        os.makedirs(data_dir, exist_ok=True)
        import store
        monkeypatch.setattr(store, "DATA_DIR", data_dir)
        yield data_dir


class TestSeen:
    def test_load_seen_empty(self, temp_data_dir):
        assert load_seen() == {}

    def test_save_and_load_seen(self, temp_data_dir):
        data = {"123": {"score": 4, "pushed_at": "2026-07-21", "source": "daily"}}
        save_seen(data)
        assert load_seen() == data

    def test_is_seen_true(self, temp_data_dir):
        save_seen({"456": {"score": 5, "pushed_at": "2026-07-21", "source": "daily"}})
        assert is_seen(456) is True

    def test_is_seen_false(self, temp_data_dir):
        assert is_seen(999) is False

    def test_mark_seen_adds_entry(self, temp_data_dir):
        mark_seen(789, score=4, source="daily")
        data = load_seen()
        assert "789" in data
        assert data["789"]["score"] == 4
        assert data["789"]["source"] == "daily"


class TestHistory:
    def test_load_history_empty(self, temp_data_dir):
        assert load_history() == []

    def test_add_and_load_history(self, temp_data_dir):
        entry = {"date": "2026-07-22", "type": "daily", "repos": []}
        add_history_entry(entry)
        assert load_history() == [entry]

    def test_get_history_for_period(self, temp_data_dir):
        old = {"date": "2026-07-10", "type": "daily", "repos": []}
        recent = {"date": "2026-07-22", "type": "daily", "repos": []}
        add_history_entry(old)
        add_history_entry(recent)
        result = get_history_for_period(days=7)
        assert len(result) == 1
        assert result[0]["date"] == "2026-07-22"

    def test_data_dir_auto_create(self, temp_data_dir):
        import store
        import shutil
        shutil.rmtree(temp_data_dir)
        # Should not raise
        result = load_seen()
        assert result == {}
