"""Tests for logslice.merger."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from logslice.merger import MergeOptions, merge_logs
from logslice.parser import ParsedLine


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


def _line(
    raw: str,
    ts: datetime | None = None,
    line_number: int = 1,
    severity: str | None = None,
) -> ParsedLine:
    return ParsedLine(
        raw=raw,
        timestamp=ts,
        severity=severity,
        message=raw,
        line_number=line_number,
    )


def test_merge_two_sorted_streams_produces_global_order():
    stream_a = [_line("a1", _dt(1)), _line("a2", _dt(3))]
    stream_b = [_line("b1", _dt(2)), _line("b2", _dt(4))]
    opts = MergeOptions(sources=[stream_a, stream_b])
    result = list(merge_logs(opts))
    assert [r.raw for r in result] == ["a1", "b1", "a2", "b2"]


def test_merge_empty_sources_yields_nothing():
    opts = MergeOptions(sources=[])
    assert list(merge_logs(opts)) == []


def test_merge_single_source_passes_through():
    stream = [_line("x", _dt(1)), _line("y", _dt(2))]
    opts = MergeOptions(sources=[stream])
    result = list(merge_logs(opts))
    assert [r.raw for r in result] == ["x", "y"]


def test_merge_nulls_first_places_no_timestamp_lines_at_front():
    stream_a = [_line("no-ts", ts=None, line_number=1)]
    stream_b = [_line("ts-line", _dt(1), line_number=2)]
    opts = MergeOptions(sources=[stream_b, stream_a], nulls_first=True)
    result = list(merge_logs(opts))
    assert result[0].raw == "no-ts"


def test_merge_nulls_last_by_default():
    stream_a = [_line("no-ts", ts=None, line_number=1)]
    stream_b = [_line("ts-line", _dt(1), line_number=2)]
    opts = MergeOptions(sources=[stream_a, stream_b], nulls_first=False)
    result = list(merge_logs(opts))
    assert result[-1].raw == "no-ts"


def test_merge_tag_source_prefixes_raw():
    stream_a = [_line("hello", _dt(1))]
    stream_b = [_line("world", _dt(2))]
    opts = MergeOptions(sources=[stream_a, stream_b], tag_source=True)
    result = list(merge_logs(opts))
    assert result[0].raw.startswith("[src:0]")
    assert result[1].raw.startswith("[src:1]")


def test_merge_tag_source_preserves_timestamp():
    ts = _dt(5)
    stream = [_line("msg", ts, line_number=7)]
    opts = MergeOptions(sources=[stream], tag_source=True)
    result = list(merge_logs(opts))
    assert result[0].timestamp == ts


def test_merge_three_streams_correct_order():
    s1 = [_line("c", _dt(3))]
    s2 = [_line("a", _dt(1))]
    s3 = [_line("b", _dt(2))]
    opts = MergeOptions(sources=[s1, s2, s3])
    result = list(merge_logs(opts))
    assert [r.raw for r in result] == ["a", "b", "c"]
