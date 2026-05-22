"""Tests for logslice.deduplicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.parser import ParsedLine
from logslice.deduplicator import DeduplicatorOptions, deduplicate


def _line(raw: str, n: int = 1) -> ParsedLine:
    return ParsedLine(
        raw=raw,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        severity="INFO",
        message=raw,
        line_number=n,
    )


# ---------------------------------------------------------------------------
# Basic pass-through
# ---------------------------------------------------------------------------

def test_no_duplicates_passes_through():
    lines = [_line("a"), _line("b"), _line("c")]
    result = list(deduplicate(lines))
    assert [l.raw for l in result] == ["a", "b", "c"]


def test_disabled_passes_all_lines():
    lines = [_line("x"), _line("x"), _line("x")]
    opts = DeduplicatorOptions(enabled=False)
    result = list(deduplicate(lines, opts))
    assert len(result) == 3


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------

def test_consecutive_duplicates_suppressed():
    lines = [_line("dup")] * 4
    opts = DeduplicatorOptions(annotate=False)
    result = list(deduplicate(lines, opts))
    # Only the first occurrence should survive.
    assert len(result) == 1
    assert result[0].raw == "dup"


def test_non_consecutive_duplicates_not_suppressed():
    lines = [_line("a"), _line("b"), _line("a")]
    opts = DeduplicatorOptions(annotate=False)
    result = list(deduplicate(lines, opts))
    assert [l.raw for l in result] == ["a", "b", "a"]


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------

def test_annotation_emitted_after_duplicates():
    lines = [_line("msg")] * 3
    opts = DeduplicatorOptions(annotate=True)
    result = list(deduplicate(lines, opts))
    assert len(result) == 2
    assert result[0].raw == "msg"
    assert "suppressed" in result[1].raw


def test_annotation_contains_correct_count():
    lines = [_line("msg")] * 5
    opts = DeduplicatorOptions(annotate=True)
    result = list(deduplicate(lines, opts))
    assert "4 duplicate" in result[1].raw


def test_no_annotation_when_annotate_false():
    lines = [_line("msg")] * 3
    opts = DeduplicatorOptions(annotate=False)
    result = list(deduplicate(lines, opts))
    assert len(result) == 1


# ---------------------------------------------------------------------------
# max_suppress limit
# ---------------------------------------------------------------------------

def test_max_suppress_limits_suppression():
    # With max_suppress=2, only 2 duplicates are suppressed; the 3rd passes through.
    lines = [_line("rep")] * 4  # original + 3 duplicates
    opts = DeduplicatorOptions(annotate=False, max_suppress=2)
    result = list(deduplicate(lines, opts))
    # Expect: original, then after 2 suppressed the 4th is emitted.
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_input_returns_empty():
    assert list(deduplicate([], DeduplicatorOptions())) == []


def test_single_line_passes_through():
    lines = [_line("only")]
    result = list(deduplicate(lines))
    assert len(result) == 1
    assert result[0].raw == "only"
