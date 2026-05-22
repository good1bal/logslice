"""Tests for logslice.tail — TailOptions and run_tail behaviour."""

import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from logslice.tail import TailOptions, run_tail
from logslice.parser import ParsedLine
from logslice.filters import SeverityFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(hour: int = 12, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, second, tzinfo=timezone.utc)


def _parsed(text: str, severity: str = "INFO", line_no: int = 1) -> ParsedLine:
    return ParsedLine(
        raw=text,
        timestamp=_ts(),
        severity=severity,
        line_number=line_no,
    )


# ---------------------------------------------------------------------------
# TailOptions construction
# ---------------------------------------------------------------------------

class TestTailOptions:
    def test_defaults(self, tmp_path: Path):
        log = tmp_path / "app.log"
        log.write_text("")
        opts = TailOptions(path=log)
        assert opts.path == log
        assert opts.severity_filter is None
        assert opts.poll_interval > 0
        assert opts.formatter is not None

    def test_custom_poll_interval(self, tmp_path: Path):
        log = tmp_path / "app.log"
        log.write_text("")
        opts = TailOptions(path=log, poll_interval=0.05)
        assert opts.poll_interval == 0.05

    def test_severity_filter_attached(self, tmp_path: Path):
        log = tmp_path / "app.log"
        log.write_text("")
        sf = MagicMock(spec=SeverityFilter)
        opts = TailOptions(path=log, severity_filter=sf)
        assert opts.severity_filter is sf


# ---------------------------------------------------------------------------
# run_tail
# ---------------------------------------------------------------------------

class TestRunTail:
    """run_tail should stream formatted lines from watch_file, applying
    optional severity filtering and writing to the provided output stream."""

    def _make_lines(self, *severities: str):
        return [_parsed(f"line {i}", sev, i) for i, sev in enumerate(severities, 1)]

    def test_run_tail_writes_lines(self, tmp_path: Path, capsys):
        """Lines emitted by watch_file should appear on the output stream."""
        log = tmp_path / "app.log"
        log.write_text("")
        lines = self._make_lines("INFO", "ERROR")

        with patch("logslice.tail.watch_file", return_value=iter(lines)):
            import io
            stream = io.StringIO()
            opts = TailOptions(path=log, poll_interval=0.01)
            run_tail(opts, out=stream)

        output = stream.getvalue()
        assert "line 1" in output
        assert "line 2" in output

    def test_run_tail_filters_by_severity(self, tmp_path: Path):
        """Lines below the severity threshold must be suppressed."""
        log = tmp_path / "app.log"
        log.write_text("")
        lines = self._make_lines("DEBUG", "INFO", "ERROR")

        sf = MagicMock(spec=SeverityFilter)
        # Only accept ERROR
        sf.accepts = MagicMock(side_effect=lambda ln: ln.severity == "ERROR")

        with patch("logslice.tail.watch_file", return_value=iter(lines)):
            import io
            stream = io.StringIO()
            opts = TailOptions(path=log, severity_filter=sf, poll_interval=0.01)
            run_tail(opts, out=stream)

        output = stream.getvalue()
        assert "line 3" in output   # ERROR line
        assert "line 1" not in output  # DEBUG suppressed
        assert "line 2" not in output  # INFO suppressed

    def test_run_tail_returns_line_count(self, tmp_path: Path):
        """run_tail should return the total number of lines written."""
        log = tmp_path / "app.log"
        log.write_text("")
        lines = self._make_lines("INFO", "WARN", "ERROR")

        with patch("logslice.tail.watch_file", return_value=iter(lines)):
            import io
            opts = TailOptions(path=log, poll_interval=0.01)
            count = run_tail(opts, out=io.StringIO())

        assert count == 3

    def test_run_tail_empty_file(self, tmp_path: Path):
        """run_tail on a file that produces no lines should return 0."""
        log = tmp_path / "empty.log"
        log.write_text("")

        with patch("logslice.tail.watch_file", return_value=iter([])):
            import io
            opts = TailOptions(path=log, poll_interval=0.01)
            count = run_tail(opts, out=io.StringIO())

        assert count == 0
