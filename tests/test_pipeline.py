"""Tests for logslice.pipeline — PipelineOptions, PipelineResult, run_pipeline."""

import io
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from logslice.parser import ParsedLine
from logslice.filters import SeverityFilter
from logslice.pipeline import (
    PipelineOptions,
    PipelineResult,
    _iter_parsed,
    _apply_filters,
    run_pipeline,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _line(
    raw: str = "INFO hello",
    timestamp: datetime | None = None,
    severity: str | None = "INFO",
    line_number: int = 1,
) -> ParsedLine:
    return ParsedLine(
        raw=raw,
        timestamp=timestamp,
        severity=severity,
        line_number=line_number,
    )


def _opts(**kwargs) -> PipelineOptions:
    defaults = dict(
        start=None,
        end=None,
        severity_filter=None,
        collect_stats=False,
    )
    defaults.update(kwargs)
    return PipelineOptions(**defaults)


# ---------------------------------------------------------------------------
# _iter_parsed
# ---------------------------------------------------------------------------

def test_iter_parsed_yields_parsed_lines():
    lines = ["2024-01-01T00:00:00Z INFO hello\n", "2024-01-01T00:00:01Z ERROR boom\n"]
    results = list(_iter_parsed(iter(lines)))
    assert len(results) == 2
    assert all(isinstance(r, ParsedLine) for r in results)


def test_iter_parsed_assigns_line_numbers():
    lines = ["line one\n", "line two\n", "line three\n"]
    results = list(_iter_parsed(iter(lines)))
    assert [r.line_number for r in results] == [1, 2, 3]


def test_iter_parsed_strips_trailing_newline():
    lines = ["INFO hello\n"]
    results = list(_iter_parsed(iter(lines)))
    assert results[0].raw == "INFO hello"


# ---------------------------------------------------------------------------
# _apply_filters
# ---------------------------------------------------------------------------

def test_apply_filters_no_filters_passes_all():
    parsed = [_line(timestamp=_ts(second=i), line_number=i + 1) for i in range(5)]
    opts = _opts()
    kept = list(_apply_filters(iter(parsed), opts))
    assert len(kept) == 5


def test_apply_filters_start_excludes_early():
    lines = [
        _line(timestamp=_ts(second=0), line_number=1),
        _line(timestamp=_ts(second=5), line_number=2),
        _line(timestamp=_ts(second=10), line_number=3),
    ]
    opts = _opts(start=_ts(second=5))
    kept = list(_apply_filters(iter(lines), opts))
    assert len(kept) == 2
    assert kept[0].line_number == 2


def test_apply_filters_end_excludes_late():
    lines = [
        _line(timestamp=_ts(second=0), line_number=1),
        _line(timestamp=_ts(second=5), line_number=2),
        _line(timestamp=_ts(second=10), line_number=3),
    ]
    opts = _opts(end=_ts(second=5))
    kept = list(_apply_filters(iter(lines), opts))
    assert len(kept) == 2
    assert kept[-1].line_number == 2


def test_apply_filters_severity_filter_applied():
    lines = [
        _line(raw="INFO hello", severity="INFO", line_number=1),
        _line(raw="ERROR boom", severity="ERROR", line_number=2),
        _line(raw="DEBUG trace", severity="DEBUG", line_number=3),
    ]
    # Accept only ERROR and above
    sf = SeverityFilter(min_severity="ERROR")
    opts = _opts(severity_filter=sf)
    kept = list(_apply_filters(iter(lines), opts))
    assert len(kept) == 1
    assert kept[0].severity == "ERROR"


def test_apply_filters_lines_without_timestamp_kept_when_no_range():
    lines = [_line(timestamp=None, line_number=1)]
    opts = _opts()
    kept = list(_apply_filters(iter(lines), opts))
    assert len(kept) == 1


def test_apply_filters_lines_without_timestamp_skipped_when_range_set():
    lines = [_line(timestamp=None, line_number=1)]
    opts = _opts(start=_ts(second=0))
    kept = list(_apply_filters(iter(lines), opts))
    assert len(kept) == 0


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------

def test_run_pipeline_returns_pipeline_result():
    stream = io.StringIO("2024-01-01T00:00:00Z INFO hello\n")
    opts = _opts()
    result = run_pipeline(stream, opts)
    assert isinstance(result, PipelineResult)


def test_run_pipeline_lines_contain_matching_entries():
    content = (
        "2024-01-01T00:00:00Z INFO first\n"
        "2024-01-01T00:00:05Z ERROR second\n"
        "2024-01-01T00:00:10Z DEBUG third\n"
    )
    stream = io.StringIO(content)
    opts = _opts(start=_ts(second=5))
    result = run_pipeline(stream, opts)
    assert len(result.lines) == 2


def test_run_pipeline_stats_collected_when_requested():
    content = "2024-01-01T00:00:00Z INFO hello\n"
    stream = io.StringIO(content)
    opts = _opts(collect_stats=True)
    result = run_pipeline(stream, opts)
    assert result.stats is not None


def test_run_pipeline_stats_none_when_not_requested():
    content = "2024-01-01T00:00:00Z INFO hello\n"
    stream = io.StringIO(content)
    opts = _opts(collect_stats=False)
    result = run_pipeline(stream, opts)
    assert result.stats is None


def test_run_pipeline_empty_input_yields_no_lines():
    stream = io.StringIO("")
    opts = _opts()
    result = run_pipeline(stream, opts)
    assert result.lines == []
