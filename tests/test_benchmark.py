"""Tests for logslice.benchmark."""

from __future__ import annotations

from pathlib import Path

import pytest

from logslice.benchmark import BenchmarkOptions, BenchmarkResult, run_benchmark
from logslice.profiler import ProfileResult, StageMetric


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.log"
    lines = [
        "2024-01-01T00:00:01Z INFO  started\n",
        "2024-01-01T00:00:02Z DEBUG loop\n",
        "2024-01-01T00:00:03Z ERROR boom\n",
        "not a timestamp line\n",
        "2024-01-01T00:00:05Z WARN  slow\n",
    ]
    p.write_text("".join(lines))
    return p


# ---------------------------------------------------------------------------
# BenchmarkOptions
# ---------------------------------------------------------------------------

def test_benchmark_options_defaults(log_file: Path):
    opts = BenchmarkOptions(path=log_file)
    assert opts.start_offset == 0
    assert opts.max_lines is None
    assert opts.show_profile is True


# ---------------------------------------------------------------------------
# BenchmarkResult
# ---------------------------------------------------------------------------

def test_benchmark_result_summary_contains_counts():
    r = BenchmarkResult(lines_read=10, lines_parsed=8)
    s = r.summary()
    assert "10" in s
    assert "8" in s


def test_benchmark_result_summary_with_profile():
    r = BenchmarkResult(lines_read=5, lines_parsed=4)
    r.profile.add(StageMetric("read", 0.01, 5))
    s = r.summary()
    assert "elapsed" in s


# ---------------------------------------------------------------------------
# run_benchmark
# ---------------------------------------------------------------------------

def test_run_benchmark_reads_all_lines(log_file: Path):
    opts = BenchmarkOptions(path=log_file)
    result = run_benchmark(opts)
    assert result.lines_read == 5


def test_run_benchmark_counts_parsed_timestamps(log_file: Path):
    opts = BenchmarkOptions(path=log_file)
    result = run_benchmark(opts)
    # 4 lines have timestamps; 1 does not
    assert result.lines_parsed == 4


def test_run_benchmark_max_lines_respected(log_file: Path):
    opts = BenchmarkOptions(path=log_file, max_lines=2)
    result = run_benchmark(opts)
    assert result.lines_read == 2


def test_run_benchmark_profile_has_read_stage(log_file: Path):
    opts = BenchmarkOptions(path=log_file)
    result = run_benchmark(opts)
    names = [s.name for s in result.profile.stages]
    assert "read" in names


def test_run_benchmark_profile_elapsed_nonnegative(log_file: Path):
    opts = BenchmarkOptions(path=log_file)
    result = run_benchmark(opts)
    for stage in result.profile.stages:
        assert stage.elapsed_seconds >= 0.0
