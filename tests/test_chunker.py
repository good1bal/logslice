"""Tests for logslice.chunker — ChunkOptions, chunk_by_lines, chunk_by_bytes, chunk_by_time."""

import datetime
from typing import List

import pytest

from logslice.chunker import (
    Chunk,
    ChunkOptions,
    chunk_by_bytes,
    chunk_by_lines,
    chunk_by_time,
)
from logslice.parser import ParsedLine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(hour: int, minute: int = 0, second: int = 0) -> datetime.datetime:
    return datetime.datetime(2024, 1, 1, hour, minute, second)


def _line(
    text: str,
    ts: datetime.datetime | None = None,
    lineno: int = 1,
    severity: str | None = None,
) -> ParsedLine:
    return ParsedLine(
        raw=text,
        timestamp=ts,
        severity=severity,
        line_number=lineno,
    )


def _lines(n: int, start_hour: int = 0) -> List[ParsedLine]:
    """Produce *n* lines each one minute apart beginning at *start_hour*."""
    return [
        _line(f"line {i}", ts=_ts(start_hour, minute=i), lineno=i + 1)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# ChunkOptions validation
# ---------------------------------------------------------------------------

class TestChunkOptions:
    def test_defaults_are_sane(self):
        opts = ChunkOptions()
        assert opts.max_lines is None
        assert opts.max_bytes is None
        assert opts.window_seconds is None

    def test_max_lines_zero_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            ChunkOptions(max_lines=0)

    def test_max_bytes_zero_raises(self):
        with pytest.raises(ValueError, match="max_bytes"):
            ChunkOptions(max_bytes=0)

    def test_window_seconds_zero_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            ChunkOptions(window_seconds=0)

    def test_negative_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            ChunkOptions(max_lines=-5)


# ---------------------------------------------------------------------------
# Chunk dataclass helpers
# ---------------------------------------------------------------------------

class TestChunk:
    def test_line_count(self):
        lines = _lines(4)
        chunk = Chunk(lines=lines)
        assert chunk.line_count() == 4

    def test_byte_count_matches_raw_utf8(self):
        lines = [_line("hello"), _line("world")]
        chunk = Chunk(lines=lines)
        expected = len("hello".encode()) + len("world".encode())
        assert chunk.byte_count() == expected

    def test_empty_chunk_has_zero_counts(self):
        chunk = Chunk(lines=[])
        assert chunk.line_count() == 0
        assert chunk.byte_count() == 0


# ---------------------------------------------------------------------------
# chunk_by_lines
# ---------------------------------------------------------------------------

class TestChunkByLines:
    def test_even_split(self):
        lines = _lines(6)
        chunks = list(chunk_by_lines(lines, max_lines=2))
        assert len(chunks) == 3
        assert all(c.line_count() == 2 for c in chunks)

    def test_remainder_forms_last_chunk(self):
        lines = _lines(7)
        chunks = list(chunk_by_lines(lines, max_lines=3))
        assert len(chunks) == 3
        assert chunks[-1].line_count() == 1

    def test_empty_input_yields_nothing(self):
        assert list(chunk_by_lines([], max_lines=5)) == []

    def test_single_chunk_when_fewer_lines_than_max(self):
        lines = _lines(3)
        chunks = list(chunk_by_lines(lines, max_lines=10))
        assert len(chunks) == 1
        assert chunks[0].line_count() == 3


# ---------------------------------------------------------------------------
# chunk_by_bytes
# ---------------------------------------------------------------------------

class TestChunkByBytes:
    def test_splits_when_byte_limit_exceeded(self):
        # Each raw string is exactly 5 bytes ("aaaaaa" would be 6 — use 5-char strings)
        lines = [_line("12345", lineno=i) for i in range(4)]
        # max_bytes=10 → fits exactly 2 lines per chunk
        chunks = list(chunk_by_bytes(lines, max_bytes=10))
        assert len(chunks) == 2

    def test_single_oversized_line_forms_own_chunk(self):
        big = _line("x" * 200, lineno=1)
        small = _line("y", lineno=2)
        chunks = list(chunk_by_bytes([big, small], max_bytes=50))
        assert len(chunks) == 2
        assert chunks[0].lines[0].raw == "x" * 200

    def test_empty_input_yields_nothing(self):
        assert list(chunk_by_bytes([], max_bytes=100)) == []


# ---------------------------------------------------------------------------
# chunk_by_time
# ---------------------------------------------------------------------------

class TestChunkByTime:
    def test_groups_within_window(self):
        # 6 lines, one per minute; window = 3 minutes → 2 chunks
        lines = _lines(6, start_hour=0)
        chunks = list(chunk_by_time(lines, window_seconds=180))
        assert len(chunks) == 2

    def test_lines_without_timestamps_go_into_current_chunk(self):
        ts_line = _line("with ts", ts=_ts(0, 0), lineno=1)
        no_ts = _line("no ts", ts=None, lineno=2)
        chunks = list(chunk_by_time([ts_line, no_ts], window_seconds=60))
        # Both should end up in a single chunk (no_ts appended to current)
        total_lines = sum(c.line_count() for c in chunks)
        assert total_lines == 2

    def test_empty_input_yields_nothing(self):
        assert list(chunk_by_time([], window_seconds=60)) == []

    def test_all_same_timestamp_single_chunk(self):
        ts = _ts(0, 0)
        lines = [_line(f"l{i}", ts=ts, lineno=i) for i in range(5)]
        chunks = list(chunk_by_time(lines, window_seconds=30))
        assert len(chunks) == 1
