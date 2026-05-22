"""Unit tests for logslice.parser."""

from datetime import datetime

import pytest

from logslice.parser import parse_line, parse_timestamp


# ---------------------------------------------------------------------------
# parse_timestamp
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ts_str, expected", [
    ("2024-01-15 12:34:56",       datetime(2024, 1, 15, 12, 34, 56)),
    ("2024-01-15T12:34:56",       datetime(2024, 1, 15, 12, 34, 56)),
    ("2024-01-15 12:34:56,789",   datetime(2024, 1, 15, 12, 34, 56, 789000)),
    ("2024-01-15T12:34:56.123456",datetime(2024, 1, 15, 12, 34, 56, 123456)),
])
def test_parse_timestamp_valid(ts_str, expected):
    assert parse_timestamp(ts_str) == expected


def test_parse_timestamp_invalid():
    assert parse_timestamp("not-a-timestamp") is None


# ---------------------------------------------------------------------------
# parse_line – timestamp extraction
# ---------------------------------------------------------------------------

def test_parse_line_extracts_timestamp():
    line = "2024-03-10 08:00:01,000 INFO  Starting application"
    parsed = parse_line(line)
    assert parsed.timestamp == datetime(2024, 3, 10, 8, 0, 1, 0)


def test_parse_line_no_timestamp():
    parsed = parse_line("No timestamp here at all")
    assert parsed.timestamp is None


# ---------------------------------------------------------------------------
# parse_line – severity extraction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("line, expected_sev, expected_order", [
    ("2024-01-01 00:00:00 DEBUG  connecting",    "DEBUG",    1),
    ("2024-01-01 00:00:00 INFO   ready",         "INFO",     2),
    ("2024-01-01 00:00:00 WARNING disk low",     "WARNING",  3),
    ("2024-01-01 00:00:00 ERROR  crash",         "ERROR",    4),
    ("2024-01-01 00:00:00 CRITICAL meltdown",    "CRITICAL", 5),
])
def test_parse_line_severity(line, expected_sev, expected_order):
    parsed = parse_line(line)
    assert parsed.severity == expected_sev
    assert parsed.severity_order == expected_order


def test_parse_line_no_severity():
    parsed = parse_line("2024-01-01 00:00:00 some plain text")
    assert parsed.severity is None
    assert parsed.severity_order == -1


def test_parse_line_raw_preserved():
    line = "2024-01-01 00:00:00 INFO hello world"
    assert parse_line(line).raw == line
