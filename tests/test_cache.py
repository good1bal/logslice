"""Tests for logslice.cache."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

import logslice.cache as cache_mod
from logslice.cache import (
    CacheEntry,
    _cache_key,
    _is_stale,
    load_cache,
    save_cache,
    invalidate_cache,
)


@pytest.fixture(autouse=True)
def tmp_cache_dir(tmp_path, monkeypatch):
    """Redirect all cache I/O to a temporary directory."""
    monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path / "cache")
    return tmp_path / "cache"


@pytest.fixture()
def sample_log(tmp_path):
    p = tmp_path / "app.log"
    p.write_text("2024-01-01T00:00:00 INFO hello\n")
    return str(p)


def test_cache_key_is_deterministic():
    assert _cache_key("/var/log/app.log") == _cache_key("/var/log/app.log")


def test_cache_key_differs_for_different_paths():
    assert _cache_key("/var/log/a.log") != _cache_key("/var/log/b.log")


def test_load_cache_returns_none_when_missing(sample_log):
    assert load_cache(sample_log) is None


def test_save_and_load_roundtrip(sample_log):
    index = [[0, "2024-01-01T00:00:00"]]
    save_cache(sample_log, index)
    entry = load_cache(sample_log)
    assert entry is not None
    assert entry.file_path == sample_log
    assert entry.index == index


def test_save_cache_creates_cache_dir_if_missing(sample_log, tmp_cache_dir):
    """save_cache should create the cache directory when it does not exist yet."""
    assert not tmp_cache_dir.exists()
    save_cache(sample_log, [])
    assert tmp_cache_dir.exists()


def test_load_cache_stale_after_modification(sample_log):
    save_cache(sample_log, [[0, "2024-01-01T00:00:00"]])
    # Modify file content to change mtime
    time.sleep(0.01)
    Path(sample_log).write_text("2024-01-01T00:00:01 INFO updated\n")
    assert load_cache(sample_log) is None


def test_is_stale_missing_file(tmp_path):
    entry = CacheEntry(
        file_path="/nonexistent/file.log",
        file_mtime=0.0,
        file_size=0,
        index=[],
    )
    assert _is_stale(entry, "/nonexistent/file.log") is True


def test_invalidate_removes_cache(sample_log):
    save_cache(sample_log, [])
    result = invalidate_cache(sample_log)
    assert result is True
    assert load_cache(sample_log) is None


def test_invalidate_returns_false_when_nothing_to_remove(sample_log):
    assert invalidate_cache(sample_log) is False


def test_load_cache_ignores_corrupt_json(sample_log, tmp_cache_dir):
    save_cache(sample_log, [])
    cache_file = tmp_cache_dir / (_cache_key(sample_log))
    cache_file.write_text("{not valid json")
    assert load_cache(sample_log) is None
