"""Integration tests: profile_stage chained across multiple stages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from logslice.parser import ParsedLine
from logslice.profiler import ProfileResult, format_profile, profile_stage


def _dt(sec: int = 0) -> datetime:
    return datetime(2024, 6, 1, 0, 0, sec, tzinfo=timezone.utc)


def _line(n: int) -> ParsedLine:
    return ParsedLine(
        raw=f"INFO msg {n}",
        timestamp=_dt(n),
        severity="INFO",
        message=f"msg {n}",
        line_number=n,
    )


def _source(n: int) -> Iterator[ParsedLine]:
    return (_line(i) for i in range(1, n + 1))


def _filter_info(src: Iterator[ParsedLine]) -> Iterator[ParsedLine]:
    return (ln for ln in src if ln.severity == "INFO")


def test_chained_stages_record_separate_metrics():
    r = ProfileResult()
    stage1 = profile_stage("parse", _source(20), r)
    stage2 = profile_stage("filter", _filter_info(stage1), r)
    lines = list(stage2)
    assert len(lines) == 20
    assert len(r.stages) == 2
    assert r.stages[0].name == "parse"
    assert r.stages[1].name == "filter"


def test_chained_stages_total_elapsed_is_sum():
    import pytest
    r = ProfileResult()
    stage1 = profile_stage("a", _source(10), r)
    stage2 = profile_stage("b", stage1, r)
    list(stage2)
    expected = sum(s.elapsed_seconds for s in r.stages)
    assert r.total_elapsed_seconds == pytest.approx(expected)


def test_format_profile_multiline_output():
    r = ProfileResult()
    stage1 = profile_stage("read", _source(5), r)
    stage2 = profile_stage("filter", stage1, r)
    list(stage2)
    out = format_profile(r)
    output_lines = out.splitlines()
    # header + one line per stage
    assert len(output_lines) == 3
    assert "read" in out
    assert "filter" in out


def test_profile_result_as_dict_round_trip():
    r = ProfileResult()
    list(profile_stage("x", _source(3), r))
    d = r.as_dict()
    assert isinstance(d["total_elapsed_seconds"], float)
    assert isinstance(d["stages"], list)
    assert d["stages"][0]["line_count"] == 3
