"""Tests for logslice.output."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logslice.formatter import FormatOptions
from logslice.output import OutputOptions, write_lines, write_lines_to_stream
from logslice.parser import ParsedLine


def _ts(hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, 0, tzinfo=timezone.utc)


def _line(raw: str, severity: str = "INFO", ts: datetime | None = None) -> ParsedLine:
    return ParsedLine(
        raw=raw,
        timestamp=ts or _ts(),
        severity=severity,
        line_number=1,
    )


# ---------------------------------------------------------------------------
# write_lines_to_stream
# ---------------------------------------------------------------------------

def test_write_lines_to_stream_returns_count():
    stream = io.StringIO()
    lines = [_line("line one"), _line("line two")]
    count = write_lines_to_stream(lines, stream)
    assert count == 2


def test_write_lines_to_stream_content():
    stream = io.StringIO()
    lines = [_line("hello world")]
    write_lines_to_stream(lines, stream)
    output = stream.getvalue()
    assert "hello world" in output


def test_write_lines_to_stream_newline_appended():
    stream = io.StringIO()
    lines = [_line("no newline")]
    write_lines_to_stream(lines, stream)
    assert stream.getvalue().endswith("\n")


def test_write_lines_to_stream_empty():
    stream = io.StringIO()
    count = write_lines_to_stream([], stream)
    assert count == 0
    assert stream.getvalue() == ""


def test_write_lines_to_stream_json_format():
    stream = io.StringIO()
    fmt = FormatOptions(json_output=True)
    lines = [_line("msg", severity="ERROR")]
    write_lines_to_stream(lines, stream, fmt=fmt)
    output = stream.getvalue()
    assert "\"severity\"" in output or "severity" in output


# ---------------------------------------------------------------------------
# write_lines (file destination)
# ---------------------------------------------------------------------------

def test_write_lines_to_file(tmp_path: Path):
    dest = tmp_path / "out.log"
    opts = OutputOptions(destination=dest)
    lines = [_line("written to file")]
    count = write_lines(lines, opts)
    assert count == 1
    assert dest.exists()
    assert "written to file" in dest.read_text(encoding="utf-8")


def test_write_lines_append_mode(tmp_path: Path):
    dest = tmp_path / "append.log"
    dest.write_text("existing\n", encoding="utf-8")
    opts = OutputOptions(destination=dest, append=True)
    lines = [_line("appended")]
    write_lines(lines, opts)
    content = dest.read_text(encoding="utf-8")
    assert content.startswith("existing")
    assert "appended" in content


def test_write_lines_overwrite_mode(tmp_path: Path):
    dest = tmp_path / "overwrite.log"
    dest.write_text("old content\n", encoding="utf-8")
    opts = OutputOptions(destination=dest, append=False)
    lines = [_line("new content")]
    write_lines(lines, opts)
    content = dest.read_text(encoding="utf-8")
    assert "old content" not in content
    assert "new content" in content
