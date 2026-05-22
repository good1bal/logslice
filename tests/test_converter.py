"""Tests for logslice.converter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from logslice.converter import ConvertOptions, convert_log


_SAMPLE_LOG = (
    "2024-01-15T10:00:00Z INFO  service started\n"
    "2024-01-15T10:00:01Z ERROR disk full\n"
    "2024-01-15T10:00:02Z WARN  retrying\n"
)


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    p = tmp_path / "app.log"
    p.write_text(_SAMPLE_LOG, encoding="utf-8")
    return p


def test_convert_to_jsonl(log_file: Path, tmp_path: Path):
    dest = tmp_path / "out.jsonl"
    opts = ConvertOptions(source=log_file, destination=dest, fmt="jsonl")
    count = convert_log(opts)
    assert count == 3
    rows = [json.loads(ln) for ln in dest.read_text().splitlines()]
    assert rows[1]["severity"] == "ERROR"


def test_convert_to_csv(log_file: Path, tmp_path: Path):
    dest = tmp_path / "out.csv"
    opts = ConvertOptions(source=log_file, destination=dest, fmt="csv")
    count = convert_log(opts)
    assert count == 3
    text = dest.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "timestamp,severity,message"


def test_convert_to_plain(log_file: Path, tmp_path: Path):
    dest = tmp_path / "out.txt"
    opts = ConvertOptions(source=log_file, destination=dest, fmt="plain")
    count = convert_log(opts)
    assert count == 3
    lines = dest.read_text(encoding="utf-8").splitlines()
    assert "service started" in lines[0]


def test_convert_with_line_numbers(log_file: Path, tmp_path: Path):
    dest = tmp_path / "out.jsonl"
    opts = ConvertOptions(
        source=log_file, destination=dest, fmt="jsonl", include_line_numbers=True
    )
    convert_log(opts)
    rows = [json.loads(ln) for ln in dest.read_text().splitlines()]
    assert rows[0]["line_number"] == 1
    assert rows[2]["line_number"] == 3


def test_convert_missing_source_raises(tmp_path: Path):
    opts = ConvertOptions(
        source=tmp_path / "nope.log",
        destination=tmp_path / "out.txt",
    )
    with pytest.raises(FileNotFoundError, match="Source log not found"):
        convert_log(opts)


def test_convert_returns_line_count(log_file: Path, tmp_path: Path):
    dest = tmp_path / "out.jsonl"
    opts = ConvertOptions(source=log_file, destination=dest)
    result = convert_log(opts)
    assert result == 3


def test_convert_empty_file(tmp_path: Path):
    src = tmp_path / "empty.log"
    src.write_text("", encoding="utf-8")
    dest = tmp_path / "out.jsonl"
    opts = ConvertOptions(source=src, destination=dest, fmt="jsonl")
    count = convert_log(opts)
    assert count == 0
    assert dest.read_text(encoding="utf-8") == ""
