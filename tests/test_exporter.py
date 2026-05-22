"""Tests for logslice.exporter."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logslice.exporter import (
    ExportOptions,
    export_csv,
    export_jsonl,
    export_lines,
    export_plain,
    export_to_file,
)
from logslice.parser import ParsedLine

_TS = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def _line(raw: str, sev: str = "INFO", ts=_TS, num: int = 1) -> ParsedLine:
    return ParsedLine(raw=raw, timestamp=ts, severity=sev, line_number=num)


# ---------------------------------------------------------------------------
# plain
# ---------------------------------------------------------------------------

def test_export_plain_single_line():
    result = export_plain([_line("hello world")], ExportOptions())
    assert result == "hello world"


def test_export_plain_with_line_numbers():
    opts = ExportOptions(include_line_numbers=True)
    result = export_plain([_line("msg", num=5)], opts)
    assert result == "5: msg"


def test_export_plain_multiple_lines():
    lines = [_line("a", num=1), _line("b", num=2)]
    result = export_plain(lines, ExportOptions())
    assert result == "a\nb"


# ---------------------------------------------------------------------------
# JSONL
# ---------------------------------------------------------------------------

def test_export_jsonl_structure():
    result = export_jsonl([_line("test msg", sev="ERROR")], ExportOptions())
    obj = json.loads(result)
    assert obj["severity"] == "ERROR"
    assert obj["message"] == "test msg"
    assert obj["timestamp"] == _TS.isoformat()


def test_export_jsonl_no_line_number_by_default():
    result = export_jsonl([_line("x")], ExportOptions())
    obj = json.loads(result)
    assert "line_number" not in obj


def test_export_jsonl_with_line_number():
    opts = ExportOptions(include_line_numbers=True)
    result = export_jsonl([_line("x", num=7)], opts)
    obj = json.loads(result)
    assert obj["line_number"] == 7


def test_export_jsonl_multiple_rows():
    lines = [_line("a", num=1), _line("b", num=2)]
    rows = export_jsonl(lines, ExportOptions()).splitlines()
    assert len(rows) == 2
    assert json.loads(rows[1])["message"] == "b"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def test_export_csv_has_header():
    result = export_csv([_line("row")], ExportOptions())
    assert result.splitlines()[0] == "timestamp,severity,message"


def test_export_csv_data_row():
    result = export_csv([_line("hello", sev="WARN")], ExportOptions())
    lines = result.splitlines()
    assert "WARN" in lines[1]
    assert "hello" in lines[1]


def test_export_csv_with_line_number_header():
    opts = ExportOptions(include_line_numbers=True)
    result = export_csv([_line("x")], opts)
    assert result.splitlines()[0].startswith("line_number")


# ---------------------------------------------------------------------------
# dispatch + file
# ---------------------------------------------------------------------------

def test_export_lines_dispatches_format():
    opts = ExportOptions(format="jsonl")
    result = export_lines([_line("z")], opts)
    assert json.loads(result)["message"] == "z"


def test_export_to_file_writes_content(tmp_path: Path):
    dest = tmp_path / "out.txt"
    count = export_to_file([_line("written")], ExportOptions(), dest)
    assert count == 1
    assert "written" in dest.read_text(encoding="utf-8")


def test_export_to_file_returns_line_count(tmp_path: Path):
    dest = tmp_path / "out.jsonl"
    lines = [_line("a", num=1), _line("b", num=2), _line("c", num=3)]
    count = export_to_file(lines, ExportOptions(format="jsonl"), dest)
    assert count == 3
