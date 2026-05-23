"""Tests for logslice.truncator."""
from __future__ import annotations

import pytest

from logslice.parser import ParsedLine
from logslice.truncator import TruncatorOptions, truncate_line, truncate_lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _line(
    raw: str,
    message: str | None = None,
    line_number: int = 1,
) -> ParsedLine:
    return ParsedLine(
        raw=raw,
        timestamp=None,
        severity=None,
        message=message if message is not None else raw,
        line_number=line_number,
    )


# ---------------------------------------------------------------------------
# TruncatorOptions validation
# ---------------------------------------------------------------------------

def test_max_width_zero_is_valid():
    opts = TruncatorOptions(max_width=0)
    assert opts.max_width == 0


def test_max_width_below_minimum_raises():
    with pytest.raises(ValueError, match="max_width"):
        TruncatorOptions(max_width=3)  # ellipsis itself is 3 chars → need ≥4


def test_max_width_at_minimum_is_valid():
    opts = TruncatorOptions(max_width=4)
    assert opts.max_width == 4


# ---------------------------------------------------------------------------
# truncate_line — no truncation needed
# ---------------------------------------------------------------------------

def test_short_line_unchanged():
    opts = TruncatorOptions(max_width=80)
    line = _line("short line")
    result = truncate_line(line, opts)
    assert result.raw == "short line"


def test_disabled_max_width_unchanged():
    opts = TruncatorOptions(max_width=0)
    long_raw = "x" * 200
    line = _line(long_raw)
    result = truncate_line(line, opts)
    assert result.raw == long_raw


# ---------------------------------------------------------------------------
# truncate_line — full raw truncation
# ---------------------------------------------------------------------------

def test_full_raw_truncation():
    opts = TruncatorOptions(max_width=10, truncate_message_only=False)
    line = _line("a" * 20)
    result = truncate_line(line, opts)
    assert len(result.raw) == 10
    assert result.raw.endswith("...")


def test_full_raw_preserves_metadata():
    opts = TruncatorOptions(max_width=10, truncate_message_only=False)
    line = _line("b" * 20)
    result = truncate_line(line, opts)
    assert result.line_number == line.line_number
    assert result.timestamp == line.timestamp
    assert result.severity == line.severity


# ---------------------------------------------------------------------------
# truncate_line — message-only truncation
# ---------------------------------------------------------------------------

def test_message_only_preserves_prefix():
    prefix = "2024-01-01 ERROR "
    message = "something went wrong " * 5
    raw = prefix + message
    opts = TruncatorOptions(max_width=40, truncate_message_only=True)
    line = ParsedLine(
        raw=raw,
        timestamp=None,
        severity="ERROR",
        message=message,
        line_number=1,
    )
    result = truncate_line(line, opts)
    assert result.raw.startswith(prefix)
    assert len(result.raw) == 40
    assert result.raw.endswith("...")


def test_message_only_updates_message_field():
    prefix = "INFO "
    message = "detail " * 10
    raw = prefix + message
    opts = TruncatorOptions(max_width=20, truncate_message_only=True)
    line = ParsedLine(
        raw=raw, timestamp=None, severity="INFO", message=message, line_number=2
    )
    result = truncate_line(line, opts)
    assert result.message == result.raw[len(prefix):]


# ---------------------------------------------------------------------------
# truncate_lines
# ---------------------------------------------------------------------------

def test_truncate_lines_yields_all():
    opts = TruncatorOptions(max_width=10)
    lines = [_line("x" * 20, line_number=i) for i in range(5)]
    results = list(truncate_lines(lines, opts))
    assert len(results) == 5
    assert all(len(r.raw) == 10 for r in results)


def test_truncate_lines_empty_input():
    opts = TruncatorOptions(max_width=10)
    assert list(truncate_lines([], opts)) == []
