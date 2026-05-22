"""Tests for logslice.filters."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from logslice.filters import (
    AcceptAllFilter,
    ExactSeverityFilter,
    MinSeverityFilter,
    in_time_range,
    make_severity_filter,
    normalize_severity,
    severity_rank,
)
from logslice.parser import ParsedLine


def _line(
    severity: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    raw: str = "test log line",
) -> ParsedLine:
    return ParsedLine(raw=raw, timestamp=timestamp, severity=severity)


# ---------------------------------------------------------------------------
# normalize_severity
# ---------------------------------------------------------------------------

def test_normalize_warn():
    assert normalize_severity("WARN") == "WARNING"


def test_normalize_fatal():
    assert normalize_severity("FATAL") == "CRITICAL"


def test_normalize_passthrough():
    assert normalize_severity("ERROR") == "ERROR"


# ---------------------------------------------------------------------------
# severity_rank
# ---------------------------------------------------------------------------

def test_rank_ordering():
    assert severity_rank("DEBUG") < severity_rank("INFO")
    assert severity_rank("INFO") < severity_rank("WARNING")
    assert severity_rank("WARNING") < severity_rank("ERROR")
    assert severity_rank("ERROR") < severity_rank("CRITICAL")


def test_rank_unknown_returns_zero():
    assert severity_rank("VERBOSE") == 0


# ---------------------------------------------------------------------------
# MinSeverityFilter
# ---------------------------------------------------------------------------

def test_min_severity_accepts_equal():
    f = MinSeverityFilter("WARNING")
    assert f.accepts(_line(severity="WARNING"))


def test_min_severity_accepts_higher():
    f = MinSeverityFilter("WARNING")
    assert f.accepts(_line(severity="ERROR"))


def test_min_severity_rejects_lower():
    f = MinSeverityFilter("WARNING")
    assert not f.accepts(_line(severity="DEBUG"))


def test_min_severity_passes_none_severity():
    f = MinSeverityFilter("ERROR")
    assert f.accepts(_line(severity=None))


# ---------------------------------------------------------------------------
# ExactSeverityFilter
# ---------------------------------------------------------------------------

def test_exact_accepts_matching():
    f = ExactSeverityFilter({"ERROR", "CRITICAL"})
    assert f.accepts(_line(severity="ERROR"))
    assert f.accepts(_line(severity="CRITICAL"))


def test_exact_rejects_non_matching():
    f = ExactSeverityFilter({"ERROR"})
    assert not f.accepts(_line(severity="INFO"))


def test_exact_normalizes_input():
    f = ExactSeverityFilter({"WARN"})
    assert f.accepts(_line(severity="WARNING"))


# ---------------------------------------------------------------------------
# make_severity_filter factory
# ---------------------------------------------------------------------------

def test_factory_returns_accept_all_when_no_args():
    assert isinstance(make_severity_filter(), AcceptAllFilter)


def test_factory_returns_min_filter():
    assert isinstance(make_severity_filter(min_level="INFO"), MinSeverityFilter)


def test_factory_returns_exact_filter():
    assert isinstance(make_severity_filter(include_levels={"ERROR"}), ExactSeverityFilter)


# ---------------------------------------------------------------------------
# in_time_range
# ---------------------------------------------------------------------------

_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_in_range_no_bounds():
    assert in_time_range(_line(timestamp=_TS), None, None)


def test_in_range_within_bounds():
    start = datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc)
    assert in_time_range(_line(timestamp=_TS), start, end)


def test_in_range_before_start():
    start = datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc)
    assert not in_time_range(_line(timestamp=_TS), start, None)


def test_in_range_after_end():
    end = datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)
    assert not in_time_range(_line(timestamp=_TS), None, end)


def test_in_range_no_timestamp_passes():
    start = datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc)
    assert in_time_range(_line(timestamp=None), start, None)
