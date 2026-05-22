"""Tests for logslice.summarizer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from logslice.parser import ParsedLine
from logslice.stats import SliceStats
from logslice.summarizer import (
    LogSummary,
    SummaryOptions,
    build_summary,
    format_summary,
)


def _ts(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


def _line(raw: str, severity: str | None = None, ts: datetime | None = None) -> ParsedLine:
    return ParsedLine(raw=raw, timestamp=ts, severity=severity, line_number=1)


def _stats(
    total: int = 10,
    skipped: int = 2,
    first: datetime | None = None,
    last: datetime | None = None,
) -> SliceStats:
    return SliceStats(
        total_lines=total,
        skipped_lines=skipped,
        first_timestamp=first,
        last_timestamp=last,
    )


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------

def test_build_summary_counts_matched():
    lines = [_line("a", "INFO"), _line("b", "DEBUG"), _line("c", "INFO")]
    summary = build_summary(_stats(), lines)
    assert summary.matched_lines == 3


def test_build_summary_inherits_stats_totals():
    summary = build_summary(_stats(total=50, skipped=5), [])
    assert summary.total_lines == 50
    assert summary.skipped_lines == 5


def test_build_summary_severity_counts():
    lines = [_line("a", "INFO"), _line("b", "INFO"), _line("c", "ERROR")]
    summary = build_summary(_stats(), lines)
    assert summary.severity_counts["INFO"] == 2
    assert summary.severity_counts["ERROR"] == 1


def test_build_summary_unknown_severity():
    lines = [_line("a", None)]
    summary = build_summary(_stats(), lines)
    assert "UNKNOWN" in summary.severity_counts


def test_build_summary_sample_errors_collected():
    lines = [
        _line("err1", "ERROR"),
        _line("err2", "ERROR"),
        _line("err3", "ERROR"),
        _line("err4", "ERROR"),  # beyond top_n_errors=3
    ]
    opts = SummaryOptions(top_n_errors=3)
    summary = build_summary(_stats(), lines, opts)
    assert len(summary.sample_errors) == 3


def test_build_summary_time_span_from_stats():
    summary = build_summary(
        _stats(first=_ts(10), last=_ts(11)),
        [],
    )
    assert summary.time_span_seconds == 3600.0


def test_build_summary_time_span_none_when_missing():
    summary = build_summary(_stats(), [])
    assert summary.time_span_seconds is None


# ---------------------------------------------------------------------------
# format_summary
# ---------------------------------------------------------------------------

def test_format_summary_contains_header():
    result = format_summary(LogSummary())
    assert "Log Slice Summary" in result


def test_format_summary_shows_matched_and_total():
    s = LogSummary(total_lines=100, matched_lines=42)
    result = format_summary(s)
    assert "100" in result
    assert "42" in result


def test_format_summary_shows_time_span():
    s = LogSummary(time_span_seconds=120.0)
    result = format_summary(s, SummaryOptions(show_time_span=True))
    assert "120.0" in result


def test_format_summary_hides_time_span_when_disabled():
    s = LogSummary(time_span_seconds=120.0)
    result = format_summary(s, SummaryOptions(show_time_span=False))
    assert "120.0" not in result


def test_format_summary_shows_severity_breakdown():
    s = LogSummary(severity_counts={"INFO": 5, "ERROR": 2})
    result = format_summary(s, SummaryOptions(show_severity_counts=True))
    assert "INFO" in result
    assert "ERROR" in result


def test_format_summary_shows_sample_errors():
    s = LogSummary(sample_errors=["something went wrong"])
    result = format_summary(s)
    assert "something went wrong" in result
