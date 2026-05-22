"""Tests for logslice.highlighter."""

from __future__ import annotations

import pytest

from logslice.highlighter import HighlightRule, Highlighter, make_highlighter


# ---------------------------------------------------------------------------
# HighlightRule
# ---------------------------------------------------------------------------

def test_highlight_rule_wraps_match():
    rule = HighlightRule(pattern="error", colour="red")
    result = rule.apply("an error occurred")
    assert "\033[31m" in result
    assert "error" in result
    assert "\033[0m" in result


def test_highlight_rule_case_insensitive_by_default():
    rule = HighlightRule(pattern="warn", colour="yellow")
    result = rule.apply("WARN: disk full")
    assert "\033[33m" in result


def test_highlight_rule_case_sensitive_no_match():
    rule = HighlightRule(pattern="warn", colour="yellow", case_sensitive=True)
    result = rule.apply("WARN: disk full")
    # No ANSI codes should be injected
    assert "\033[" not in result


def test_highlight_rule_unknown_colour_raises():
    with pytest.raises(ValueError, match="Unknown colour"):
        HighlightRule(pattern="foo", colour="ultraviolet")


def test_highlight_rule_multiple_occurrences():
    rule = HighlightRule(pattern="ok", colour="green")
    result = rule.apply("ok ok ok")
    assert result.count("\033[32m") == 3


# ---------------------------------------------------------------------------
# Highlighter
# ---------------------------------------------------------------------------

def test_highlighter_applies_all_rules():
    h = Highlighter()
    h.add_rule("error", colour="red")
    h.add_rule("warn", colour="yellow")
    result = h.highlight("error and warn in one line")
    assert "\033[31m" in result  # red for error
    assert "\033[33m" in result  # yellow for warn


def test_highlighter_disabled_returns_original():
    h = Highlighter(enabled=False)
    h.add_rule("error", colour="red")
    text = "an error occurred"
    assert h.highlight(text) == text


def test_highlighter_no_rules_returns_original():
    h = Highlighter()
    text = "nothing to highlight"
    assert h.highlight(text) == text


def test_highlighter_add_rule_appends():
    h = Highlighter()
    h.add_rule("foo")
    h.add_rule("bar")
    assert len(h.rules) == 2


# ---------------------------------------------------------------------------
# make_highlighter
# ---------------------------------------------------------------------------

def test_make_highlighter_with_keywords():
    h = make_highlighter(keywords=["timeout", "retry"], colour="cyan")
    result = h.highlight("connection timeout, retry scheduled")
    assert "\033[36m" in result
    assert result.count("\033[36m") == 2


def test_make_highlighter_empty_keywords():
    h = make_highlighter(keywords=[])
    text = "nothing special"
    assert h.highlight(text) == text


def test_make_highlighter_disabled():
    h = make_highlighter(keywords=["error"], enabled=False)
    text = "an error occurred"
    assert h.highlight(text) == text


def test_make_highlighter_escapes_special_chars():
    h = make_highlighter(keywords=["file.log"], colour="blue")
    result = h.highlight("reading file.log now")
    assert "\033[34m" in result
    # Should NOT match 'fileXlog' (dot is escaped)
    result2 = h.highlight("fileXlog")
    assert "\033[34m" not in result2
