"""Tests for logslice.splitter — SplitOptions, SplitResult, and split_log."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logslice.parser import ParsedLine
from logslice.splitter import SplitOptions, SplitResult, split_log


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, second, tzinfo=timezone.utc)


def _line(text: str, ts: datetime | None = None, severity: str = "INFO", lineno: int = 1) -> ParsedLine:
    return ParsedLine(
        raw=text,
        timestamp=ts,
        severity=severity,
        line_number=lineno,
    )


def _make_lines():
    """Return a small sequence of ParsedLine objects spanning several hours."""
    return [
        _line("first entry",  ts=_dt(0, 0),  severity="INFO",  lineno=1),
        _line("second entry", ts=_dt(0, 30), severity="DEBUG", lineno=2),
        _line("third entry",  ts=_dt(1, 0),  severity="WARN",  lineno=3),
        _line("fourth entry", ts=_dt(1, 45), severity="ERROR", lineno=4),
        _line("fifth entry",  ts=_dt(2, 15), severity="INFO",  lineno=5),
    ]


# ---------------------------------------------------------------------------
# SplitOptions validation
# ---------------------------------------------------------------------------

class TestSplitOptions:
    def test_defaults_are_sane(self):
        opts = SplitOptions(output_dir="/tmp")
        assert opts.window_minutes > 0
        assert opts.prefix == "part"
        assert opts.suffix == ".log"
        assert opts.include_line_numbers is False

    def test_window_minutes_below_one_raises(self):
        with pytest.raises(ValueError, match="window_minutes"):
            SplitOptions(output_dir="/tmp", window_minutes=0)

    def test_window_minutes_negative_raises(self):
        with pytest.raises(ValueError, match="window_minutes"):
            SplitOptions(output_dir="/tmp", window_minutes=-5)

    def test_custom_prefix_and_suffix(self):
        opts = SplitOptions(output_dir="/tmp", prefix="chunk", suffix=".txt")
        assert opts.prefix == "chunk"
        assert opts.suffix == ".txt"


# ---------------------------------------------------------------------------
# split_log — basic splitting behaviour
# ---------------------------------------------------------------------------

class TestSplitLog:
    def test_returns_split_result_list(self, tmp_path):
        lines = _make_lines()
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60)
        results = split_log(lines, opts)
        assert isinstance(results, list)
        assert all(isinstance(r, SplitResult) for r in results)

    def test_correct_number_of_parts_hourly(self, tmp_path):
        # Lines span 0:00–2:15 → three 60-minute buckets
        lines = _make_lines()
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60)
        results = split_log(lines, opts)
        assert len(results) == 3

    def test_single_part_when_window_covers_all(self, tmp_path):
        lines = _make_lines()
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=180)
        results = split_log(lines, opts)
        assert len(results) == 1

    def test_output_files_are_created(self, tmp_path):
        lines = _make_lines()
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60)
        results = split_log(lines, opts)
        for r in results:
            assert Path(r.path).exists()

    def test_each_part_contains_correct_lines(self, tmp_path):
        lines = _make_lines()
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60)
        results = split_log(lines, opts)
        # First bucket (0:00–0:59) should have 2 lines
        first = next(r for r in results if r.part_index == 0)
        assert first.line_count == 2

    def test_total_line_count_matches_input(self, tmp_path):
        lines = _make_lines()
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60)
        results = split_log(lines, opts)
        assert sum(r.line_count for r in results) == len(lines)

    def test_file_names_use_prefix_and_suffix(self, tmp_path):
        lines = _make_lines()
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60,
                            prefix="seg", suffix=".txt")
        results = split_log(lines, opts)
        for r in results:
            name = Path(r.path).name
            assert name.startswith("seg")
            assert name.endswith(".txt")

    def test_empty_input_yields_no_parts(self, tmp_path):
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60)
        results = split_log([], opts)
        assert results == []

    def test_lines_without_timestamps_go_to_fallback_part(self, tmp_path):
        lines = [
            _line("no ts", ts=None, lineno=1),
            _line("no ts 2", ts=None, lineno=2),
        ]
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60)
        results = split_log(lines, opts)
        assert len(results) == 1
        assert results[0].line_count == 2

    def test_include_line_numbers_prepends_number(self, tmp_path):
        lines = [_line("hello", ts=_dt(1), lineno=42)]
        opts = SplitOptions(output_dir=str(tmp_path), window_minutes=60,
                            include_line_numbers=True)
        results = split_log(lines, opts)
        content = Path(results[0].path).read_text()
        assert "42" in content
