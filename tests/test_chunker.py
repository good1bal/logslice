"""Tests for logslice.chunker — chunk iteration by line count or byte size."""

import pytest
from datetime import datetime, timezone
from logslice.chunker import ChunkOptions, Chunk, chunk_lines
from logslice.parser import ParsedLine


def _ts(hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, 0, tzinfo=timezone.utc)


def _line(
    text: str = "INFO hello",
    lineno: int = 1,
    ts: datetime | None = None,
    severity: str = "INFO",
) -> ParsedLine:
    return ParsedLine(
        raw=text,
        line_number=lineno,
        timestamp=ts,
        severity=severity,
    )


def _lines(n: int, prefix: str = "INFO msg") -> list[ParsedLine]:
    return [_line(text=f"{prefix} {i}", lineno=i, ts=_ts(minute=i % 60)) for i in range(1, n + 1)]


class TestChunkOptions:
    def test_defaults_are_sane(self):
        opts = ChunkOptions()
        assert opts.max_lines is None
        assert opts.max_bytes is None
        assert opts.overlap == 0

    def test_max_lines_must_be_positive(self):
        with pytest.raises(ValueError, match="max_lines"):
            ChunkOptions(max_lines=0)

    def test_max_bytes_must_be_positive(self):
        with pytest.raises(ValueError, match="max_bytes"):
            ChunkOptions(max_bytes=-1)

    def test_overlap_cannot_be_negative(self):
        with pytest.raises(ValueError, match="overlap"):
            ChunkOptions(overlap=-1)

    def test_overlap_must_be_less_than_max_lines(self):
        with pytest.raises(ValueError, match="overlap"):
            ChunkOptions(max_lines=3, overlap=3)

    def test_at_least_one_limit_required(self):
        with pytest.raises(ValueError, match="max_lines or max_bytes"):
            ChunkOptions()
            # Validation only fires when both are None and we try to chunk
            # so this test verifies chunk_lines raises instead


class TestChunkByLines:
    def test_single_chunk_when_few_lines(self):
        lines = _lines(5)
        opts = ChunkOptions(max_lines=10)
        chunks = list(chunk_lines(lines, opts))
        assert len(chunks) == 1
        assert chunks[0].line_count == 5

    def test_splits_evenly(self):
        lines = _lines(9)
        opts = ChunkOptions(max_lines=3)
        chunks = list(chunk_lines(lines, opts))
        assert len(chunks) == 3
        for chunk in chunks:
            assert chunk.line_count == 3

    def test_last_chunk_may_be_smaller(self):
        lines = _lines(10)
        opts = ChunkOptions(max_lines=3)
        chunks = list(chunk_lines(lines, opts))
        assert len(chunks) == 4
        assert chunks[-1].line_count == 1

    def test_chunk_index_is_sequential(self):
        lines = _lines(6)
        opts = ChunkOptions(max_lines=2)
        chunks = list(chunk_lines(lines, opts))
        assert [c.index for c in chunks] == [0, 1, 2]

    def test_overlap_repeats_tail_lines(self):
        lines = _lines(6)
        opts = ChunkOptions(max_lines=3, overlap=1)
        chunks = list(chunk_lines(lines, opts))
        # chunk 0: lines 1-3, chunk 1: lines 3-5, chunk 2: line 5-6
        assert chunks[0].lines[-1].line_number == chunks[1].lines[0].line_number

    def test_empty_input_yields_no_chunks(self):
        opts = ChunkOptions(max_lines=5)
        chunks = list(chunk_lines([], opts))
        assert chunks == []

    def test_chunk_preserves_line_content(self):
        lines = _lines(4)
        opts = ChunkOptions(max_lines=2)
        chunks = list(chunk_lines(lines, opts))
        assert chunks[0].lines[0].line_number == 1
        assert chunks[1].lines[0].line_number == 3


class TestChunkByBytes:
    def test_splits_by_byte_size(self):
        # Each line raw text is "INFO msg N" — roughly 10 bytes each
        lines = _lines(10)
        total = sum(len(ln.raw.encode()) for ln in lines)
        half = total // 2 + 1
        opts = ChunkOptions(max_bytes=half)
        chunks = list(chunk_lines(lines, opts))
        assert len(chunks) >= 2

    def test_single_oversized_line_forms_own_chunk(self):
        big = _line(text="ERROR " + "x" * 500, lineno=1)
        small = _line(text="INFO ok", lineno=2)
        opts = ChunkOptions(max_bytes=100)
        chunks = list(chunk_lines([big, small], opts))
        assert chunks[0].lines[0] is big

    def test_byte_count_matches_raw_encoding(self):
        lines = _lines(3)
        opts = ChunkOptions(max_lines=3)
        chunks = list(chunk_lines(lines, opts))
        expected = sum(len(ln.raw.encode()) for ln in lines)
        assert chunks[0].byte_count == expected


class TestChunkMetadata:
    def test_is_last_flag(self):
        lines = _lines(4)
        opts = ChunkOptions(max_lines=2)
        chunks = list(chunk_lines(lines, opts))
        assert not chunks[0].is_last
        assert chunks[-1].is_last

    def test_first_and_last_timestamp(self):
        lines = [
            _line(text="INFO a", lineno=1, ts=_ts(hour=1)),
            _line(text="INFO b", lineno=2, ts=_ts(hour=2)),
            _line(text="INFO c", lineno=3, ts=_ts(hour=3)),
        ]
        opts = ChunkOptions(max_lines=3)
        chunks = list(chunk_lines(lines, opts))
        assert chunks[0].first_timestamp == _ts(hour=1)
        assert chunks[0].last_timestamp == _ts(hour=3)

    def test_timestamps_none_when_missing(self):
        lines = [_line(ts=None, lineno=i) for i in range(1, 4)]
        opts = ChunkOptions(max_lines=3)
        chunks = list(chunk_lines(lines, opts))
        assert chunks[0].first_timestamp is None
        assert chunks[0].last_timestamp is None
