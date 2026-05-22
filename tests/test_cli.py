"""Tests for the CLI argument parser and main entry point."""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from logslice.cli import _parse_dt, build_parser, main


# ---------------------------------------------------------------------------
# _parse_dt
# ---------------------------------------------------------------------------

class TestParseDt:
    def test_date_only(self):
        dt = _parse_dt("2024-03-15")
        assert dt.year == 2024
        assert dt.month == 3
        assert dt.day == 15
        assert dt.hour == 0
        assert dt.minute == 0

    def test_datetime_with_seconds(self):
        dt = _parse_dt("2024-03-15T12:30:45")
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_datetime_without_seconds(self):
        dt = _parse_dt("2024-03-15T12:30")
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 0

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Cannot parse datetime"):
            _parse_dt("not-a-date")

    def test_returns_datetime_instance(self):
        dt = _parse_dt("2024-01-01")
        assert isinstance(dt, datetime)


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

class TestBuildParser:
    def setup_method(self):
        self.parser = build_parser()

    def test_requires_file_argument(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args([])

    def test_file_argument_parsed(self):
        args = self.parser.parse_args(["app.log"])
        assert args.file == "app.log"

    def test_start_default_is_none(self):
        args = self.parser.parse_args(["app.log"])
        assert args.start is None

    def test_end_default_is_none(self):
        args = self.parser.parse_args(["app.log"])
        assert args.end is None

    def test_level_default_is_none(self):
        args = self.parser.parse_args(["app.log"])
        assert args.level is None

    def test_format_default_is_plain(self):
        args = self.parser.parse_args(["app.log"])
        assert args.format == "plain"

    def test_format_json_accepted(self):
        args = self.parser.parse_args(["app.log", "--format", "json"])
        assert args.format == "json"

    def test_color_flag_default_false(self):
        args = self.parser.parse_args(["app.log"])
        assert args.color is False

    def test_color_flag_set(self):
        args = self.parser.parse_args(["app.log", "--color"])
        assert args.color is True

    def test_line_numbers_flag_default_false(self):
        args = self.parser.parse_args(["app.log"])
        assert args.line_numbers is False

    def test_line_numbers_flag_set(self):
        args = self.parser.parse_args(["app.log", "--line-numbers"])
        assert args.line_numbers is True

    def test_start_parsed_as_datetime(self):
        args = self.parser.parse_args(["app.log", "--start", "2024-01-01T10:00"])
        assert isinstance(args.start, datetime)
        assert args.start.hour == 10

    def test_end_parsed_as_datetime(self):
        args = self.parser.parse_args(["app.log", "--end", "2024-01-01T18:00"])
        assert isinstance(args.end, datetime)
        assert args.end.hour == 18

    def test_stats_flag_default_false(self):
        args = self.parser.parse_args(["app.log"])
        assert args.stats is False

    def test_stats_flag_set(self):
        args = self.parser.parse_args(["app.log", "--stats"])
        assert args.stats is True

    def test_output_default_is_none(self):
        args = self.parser.parse_args(["app.log"])
        assert args.output is None

    def test_output_path_accepted(self):
        args = self.parser.parse_args(["app.log", "--output", "out.log"])
        assert args.output == "out.log"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_calls_run_pipeline(self, tmp_path):
        log_file = tmp_path / "sample.log"
        log_file.write_text("2024-01-01T10:00:00 INFO hello\n")

        with patch("logslice.cli.run_pipeline") as mock_run:
            mock_result = MagicMock()
            mock_result.lines = []
            mock_result.stats = MagicMock()
            mock_result.stats.as_dict.return_value = {}
            mock_run.return_value = mock_result

            with patch("sys.argv", ["logslice", str(log_file)]):
                main()

        mock_run.assert_called_once()

    def test_main_exits_nonzero_on_missing_file(self, capsys):
        with patch("sys.argv", ["logslice", "/nonexistent/file.log"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code != 0
