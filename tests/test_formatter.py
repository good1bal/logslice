"""Tests for logslice.formatter."""

import json
from datetime import datetime

import pytest

from logslice.parser import ParsedLine
from logslice.formatter import FormatOptions, format_line, format_lines


def _make_line(raw="2024-01-15 10:00:00 INFO hello", severity="INFO", message="hello"):
    ts = datetime(2024, 1, 15, 10, 0, 0)
    return ParsedLine(raw=raw, timestamp=ts, severity=severity, message=message)


def test_format_plain_default():
    line = _make_line()
    opts = FormatOptions()
    result = format_line(line, opts)
    assert result == line.raw


def test_format_plain_with_line_number():
    line = _make_line()
    opts = FormatOptions(show_line_numbers=True)
    result = format_line(line, opts, index=42)
    assert "42" in result
    assert line.raw in result


def test_format_json_output():
    line = _make_line()
    opts = FormatOptions(output_format="json")
    result = format_line(line, opts)
    data = json.loads(result)
    assert data["severity"] == "INFO"
    assert data["message"] == "hello"
    assert "2024-01-15" in data["timestamp"]


def test_format_json_with_line_number():
    line = _make_line()
    opts = FormatOptions(output_format="json", show_line_numbers=True)
    result = format_line(line, opts, index=7)
    data = json.loads(result)
    assert data["line"] == 7


def test_format_csv_output():
    line = _make_line()
    opts = FormatOptions(output_format="csv")
    result = format_line(line, opts)
    parts = result.split(",")
    assert "2024-01-15" in parts[0]
    assert parts[1] == "INFO"
    assert "hello" in result


def test_format_csv_with_line_number():
    line = _make_line()
    opts = FormatOptions(output_format="csv", show_line_numbers=True)
    result = format_line(line, opts, index=3)
    assert result.startswith("3,")


def test_format_colorize_error():
    line = _make_line(raw="2024-01-15 10:00:00 ERROR boom", severity="ERROR", message="boom")
    opts = FormatOptions(colorize=True)
    result = format_line(line, opts)
    assert "\033[31m" in result
    assert "\033[0m" in result


def test_format_colorize_unknown_severity():
    line = _make_line(raw="some line", severity=None, message="some line")
    opts = FormatOptions(colorize=True)
    result = format_line(line, opts)
    assert result == "some line"


def test_format_lines_returns_list():
    lines = [_make_line(), _make_line()]
    opts = FormatOptions(show_line_numbers=True)
    results = format_lines(lines, opts, start_index=10)
    assert len(results) == 2
    assert "10" in results[0]
    assert "11" in results[1]


def test_format_lines_default_options():
    lines = [_make_line()]
    results = format_lines(lines)
    assert results[0] == lines[0].raw
