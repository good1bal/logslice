"""Tests for logslice.quota."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.parser import ParsedLine
from logslice.quota import QuotaOptions, QuotaResult, apply_quota, collect_quota_result


_NOW = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _line(n: int, raw: str | None = None) -> ParsedLine:
    text = raw if raw is not None else f"log line number {n}"
    return ParsedLine(
        raw=text,
        timestamp=_NOW,
        severity="INFO",
        message=text,
        line_number=n,
    )


# ---------------------------------------------------------------------------
# QuotaOptions validation
# ---------------------------------------------------------------------------

class TestQuotaOptions:
    def test_defaults_are_zero(self):
        opts = QuotaOptions()
        assert opts.max_lines == 0
        assert opts.max_bytes == 0

    def test_negative_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            QuotaOptions(max_lines=-1)

    def test_negative_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes"):
            QuotaOptions(max_bytes=-1)

    def test_valid_positive_values(self):
        opts = QuotaOptions(max_lines=10, max_bytes=1024)
        assert opts.max_lines == 10
        assert opts.max_bytes == 1024


# ---------------------------------------------------------------------------
# apply_quota — unlimited
# ---------------------------------------------------------------------------

def test_no_quota_passes_all_lines():
    lines = [_line(i) for i in range(10)]
    result = list(apply_quota(lines, QuotaOptions()))
    assert result == lines


def test_none_options_passes_all_lines():
    lines = [_line(i) for i in range(5)]
    assert list(apply_quota(lines, None)) == lines


# ---------------------------------------------------------------------------
# apply_quota — max_lines
# ---------------------------------------------------------------------------

def test_max_lines_truncates_stream():
    lines = [_line(i) for i in range(10)]
    result = list(apply_quota(lines, QuotaOptions(max_lines=3)))
    assert len(result) == 3


def test_max_lines_exact_boundary():
    lines = [_line(i) for i in range(5)]
    result = list(apply_quota(lines, QuotaOptions(max_lines=5)))
    assert len(result) == 5


def test_max_lines_larger_than_source():
    lines = [_line(i) for i in range(3)]
    result = list(apply_quota(lines, QuotaOptions(max_lines=100)))
    assert len(result) == 3


# ---------------------------------------------------------------------------
# apply_quota — max_bytes
# ---------------------------------------------------------------------------

def test_max_bytes_stops_before_overflow():
    # Each raw string is exactly 5 bytes (ASCII)
    lines = [_line(i, raw="hello") for i in range(6)]
    # Allow 12 bytes → fits 2 lines (10 bytes), 3rd would push to 15
    result = list(apply_quota(lines, QuotaOptions(max_bytes=12)))
    assert len(result) == 2


def test_max_bytes_allows_exact_fit():
    lines = [_line(i, raw="hi") for i in range(3)]  # 2 bytes each = 6 total
    result = list(apply_quota(lines, QuotaOptions(max_bytes=6)))
    assert len(result) == 3


# ---------------------------------------------------------------------------
# collect_quota_result
# ---------------------------------------------------------------------------

def test_collect_quota_result_not_truncated():
    lines = [_line(i) for i in range(3)]
    kept, result = collect_quota_result(lines, QuotaOptions(max_lines=10))
    assert len(kept) == 3
    assert result.truncated is False
    assert result.lines_emitted == 3


def test_collect_quota_result_truncated():
    lines = [_line(i) for i in range(10)]
    kept, result = collect_quota_result(lines, QuotaOptions(max_lines=4))
    assert len(kept) == 4
    assert result.truncated is True
    assert result.lines_emitted == 4


def test_collect_quota_result_bytes_emitted():
    lines = [_line(i, raw="abc") for i in range(3)]  # 3 bytes each
    _, result = collect_quota_result(lines, QuotaOptions())
    assert result.bytes_emitted == 9
