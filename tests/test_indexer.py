"""Tests for logslice.indexer — build_index, find_start_offset, iter_from_offset."""

import io
import os
import tempfile
from datetime import datetime, timezone

import pytest

from logslice.indexer import (
    build_index,
    build_index_cached,
    find_start_offset,
    iter_from_offset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(hour: int, minute: int = 0, second: int = 0) -> datetime:
    """Return a UTC datetime for today at the given time."""
    return datetime(2024, 6, 1, hour, minute, second, tzinfo=timezone.utc)


LOG_LINES = [
    "2024-06-01T10:00:00Z INFO  application started\n",
    "2024-06-01T10:01:00Z DEBUG checking config\n",
    "2024-06-01T10:02:00Z WARN  disk usage high\n",
    "2024-06-01T10:03:00Z ERROR failed to write\n",
    "2024-06-01T10:04:00Z INFO  retrying operation\n",
]


@pytest.fixture()
def log_file(tmp_path):
    """Write LOG_LINES to a temporary file and return its path."""
    path = tmp_path / "sample.log"
    path.write_text("".join(LOG_LINES), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# build_index
# ---------------------------------------------------------------------------

def test_build_index_returns_list(log_file):
    index = build_index(log_file)
    assert isinstance(index, list)


def test_build_index_length_matches_lines(log_file):
    index = build_index(log_file)
    assert len(index) == len(LOG_LINES)


def test_build_index_first_offset_is_zero(log_file):
    index = build_index(log_file)
    # First parseable line should start at byte offset 0
    assert index[0][1] == 0


def test_build_index_offsets_are_increasing(log_file):
    index = build_index(log_file)
    offsets = [entry[1] for entry in index]
    assert offsets == sorted(offsets)


def test_build_index_timestamps_are_parsed(log_file):
    index = build_index(log_file)
    for ts, _offset in index:
        assert isinstance(ts, datetime)


def test_build_index_timestamps_in_order(log_file):
    index = build_index(log_file)
    timestamps = [ts for ts, _ in index]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# find_start_offset
# ---------------------------------------------------------------------------

def test_find_start_offset_before_all_returns_zero(log_file):
    index = build_index(log_file)
    offset = find_start_offset(index, _dt(9, 0, 0))
    assert offset == 0


def test_find_start_offset_exact_match(log_file):
    index = build_index(log_file)
    # Exact timestamp of the third line
    offset = find_start_offset(index, _dt(10, 2, 0))
    expected = index[2][1]
    assert offset == expected


def test_find_start_offset_between_entries(log_file):
    index = build_index(log_file)
    # Between 10:01 and 10:02 — should land on the 10:01 entry or 10:02
    offset = find_start_offset(index, _dt(10, 1, 30))
    # Must be <= offset of 10:02 entry
    assert offset <= index[2][1]


def test_find_start_offset_after_all_returns_last(log_file):
    index = build_index(log_file)
    offset = find_start_offset(index, _dt(23, 59, 59))
    last_offset = index[-1][1]
    assert offset >= last_offset


def test_find_start_offset_empty_index():
    assert find_start_offset([], _dt(10, 0, 0)) == 0


# ---------------------------------------------------------------------------
# iter_from_offset
# ---------------------------------------------------------------------------

def test_iter_from_offset_zero_yields_all_lines(log_file):
    lines = list(iter_from_offset(log_file, 0))
    assert len(lines) == len(LOG_LINES)


def test_iter_from_offset_mid_file(log_file):
    index = build_index(log_file)
    # Start from the third line
    offset = index[2][1]
    lines = list(iter_from_offset(log_file, offset))
    assert len(lines) == len(LOG_LINES) - 2


def test_iter_from_offset_yields_correct_content(log_file):
    index = build_index(log_file)
    offset = index[1][1]
    lines = list(iter_from_offset(log_file, offset))
    assert lines[0].strip() == LOG_LINES[1].strip()


# ---------------------------------------------------------------------------
# build_index_cached
# ---------------------------------------------------------------------------

def test_build_index_cached_returns_same_as_build_index(log_file, tmp_path):
    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir, exist_ok=True)

    index_direct = build_index(log_file)
    index_cached = build_index_cached(log_file, cache_dir=cache_dir)

    assert len(index_direct) == len(index_cached)
    for (ts_d, off_d), (ts_c, off_c) in zip(index_direct, index_cached):
        assert ts_d == ts_c
        assert off_d == off_c


def test_build_index_cached_second_call_uses_cache(log_file, tmp_path):
    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir, exist_ok=True)

    first = build_index_cached(log_file, cache_dir=cache_dir)
    second = build_index_cached(log_file, cache_dir=cache_dir)

    assert first == second
