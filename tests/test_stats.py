"""Tests for logslice.stats."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from logslice.parser import ParsedLine
from logslice.stats import SliceStats, collect_stats


def _ts(hour: int) -> datetime:
    return datetime(2024, 6, 1, hour, 0, 0, tzinfo=timezone.utc)


def _line(
    severity: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> ParsedLine:
    return ParsedLine(raw="x", timestamp=timestamp, severity=severity)


# ---------------------------------------------------------------------------
# SliceStats derived properties
# ---------------------------------------------------------------------------

def test_skipped_lines():
    s = SliceStats(total_lines=10, matched_lines=7)
    assert s.skipped_lines == 3


def test_time_span_seconds():
    s = SliceStats(earliest=_ts(8), latest=_ts(10))
    assert s.time_span_seconds == 7200.0


def test_time_span_none_when_missing():
    s = SliceStats(earliest=_ts(8), latest=None)
    assert s.time_span_seconds is None


def test_as_dict_keys():
    s = SliceStats(total_lines=5, matched_lines=3)
    d = s.as_dict()
    assert "total_lines" in d
    assert "matched_lines" in d
    assert "skipped_lines" in d
    assert "severity_counts" in d


# ---------------------------------------------------------------------------
# collect_stats
# ---------------------------------------------------------------------------

def test_collect_counts_total_and_matched():
    all_lines = [_line() for _ in range(10)]
    matched = all_lines[:4]
    stats = collect_stats(all_lines, matched)
    assert stats.total_lines == 10
    assert stats.matched_lines == 4


def test_collect_severity_counts():
    matched = [
        _line(severity="INFO"),
        _line(severity="INFO"),
        _line(severity="ERROR"),
        _line(severity="WARN"),   # normalized to WARNING
    ]
    stats = collect_stats(matched, matched)
    assert stats.severity_counts["INFO"] == 2
    assert stats.severity_counts["ERROR"] == 1
    assert stats.severity_counts["WARNING"] == 1


def test_collect_earliest_and_latest():
    matched = [
        _line(timestamp=_ts(9)),
        _line(timestamp=_ts(7)),
        _line(timestamp=_ts(11)),
    ]
    stats = collect_stats(matched, matched)
    assert stats.earliest == _ts(7)
    assert stats.latest == _ts(11)


def test_collect_no_timestamps():
    matched = [_line(), _line()]
    stats = collect_stats(matched, matched)
    assert stats.earliest is None
    assert stats.latest is None


def test_collect_empty():
    stats = collect_stats([], [])
    assert stats.total_lines == 0
    assert stats.matched_lines == 0
    assert stats.skipped_lines == 0
