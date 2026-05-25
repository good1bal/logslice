"""Tests for logslice.profiler."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest

from logslice.parser import ParsedLine
from logslice.profiler import (
    ProfileResult,
    StageMetric,
    format_profile,
    profile_stage,
)


def _dt(hour: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, 0, 0, tzinfo=timezone.utc)


def _line(n: int = 1) -> ParsedLine:
    return ParsedLine(
        raw=f"INFO line {n}",
        timestamp=_dt(n % 24),
        severity="INFO",
        message=f"line {n}",
        line_number=n,
    )


def _source(count: int) -> Iterator[ParsedLine]:
    for i in range(1, count + 1):
        yield _line(i)


# ---------------------------------------------------------------------------
# StageMetric
# ---------------------------------------------------------------------------

def test_stage_metric_lines_per_second():
    m = StageMetric(name="test", elapsed_seconds=2.0, line_count=100)
    assert m.lines_per_second == 50.0


def test_stage_metric_zero_elapsed():
    m = StageMetric(name="test", elapsed_seconds=0.0, line_count=50)
    assert m.lines_per_second == 0.0


# ---------------------------------------------------------------------------
# ProfileResult
# ---------------------------------------------------------------------------

def test_profile_result_add_accumulates():
    r = ProfileResult()
    r.add(StageMetric("a", 1.0, 10))
    r.add(StageMetric("b", 0.5, 8))
    assert len(r.stages) == 2
    assert r.total_elapsed_seconds == pytest.approx(1.5)
    assert r.total_lines == 10


def test_profile_result_as_dict_keys():
    r = ProfileResult()
    r.add(StageMetric("parse", 0.1, 5))
    d = r.as_dict()
    assert "total_elapsed_seconds" in d
    assert "total_lines" in d
    assert "stages" in d
    assert d["stages"][0]["name"] == "parse"


def test_profile_result_as_dict_stage_has_lps():
    r = ProfileResult()
    r.add(StageMetric("filter", 2.0, 200))
    stage = r.as_dict()["stages"][0]
    assert stage["lines_per_second"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# profile_stage
# ---------------------------------------------------------------------------

def test_profile_stage_yields_all_lines():
    r = ProfileResult()
    lines = list(profile_stage("read", _source(5), r))
    assert len(lines) == 5


def test_profile_stage_records_metric():
    r = ProfileResult()
    list(profile_stage("read", _source(10), r))
    assert len(r.stages) == 1
    assert r.stages[0].name == "read"
    assert r.stages[0].line_count == 10
    assert r.stages[0].elapsed_seconds >= 0.0


def test_profile_stage_empty_source():
    r = ProfileResult()
    lines = list(profile_stage("empty", iter([]), r))
    assert lines == []
    assert r.stages[0].line_count == 0


# ---------------------------------------------------------------------------
# format_profile
# ---------------------------------------------------------------------------

def test_format_profile_contains_stage_name():
    r = ProfileResult()
    r.add(StageMetric("parse", 0.5, 100))
    out = format_profile(r)
    assert "parse" in out


def test_format_profile_first_line_summary():
    r = ProfileResult()
    r.add(StageMetric("x", 1.0, 42))
    first_line = format_profile(r).splitlines()[0]
    assert "42" in first_line
