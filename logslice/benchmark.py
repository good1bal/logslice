"""Benchmark: run a pipeline with profiling and report throughput."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from logslice.indexer import build_index_cached, iter_from_offset, find_start_offset
from logslice.parser import parse_line
from logslice.profiler import ProfileResult, format_profile, profile_stage


@dataclass
class BenchmarkOptions:
    path: Path
    cache_dir: Optional[Path] = None
    start_offset: int = 0
    max_lines: Optional[int] = None
    show_profile: bool = True


@dataclass
class BenchmarkResult:
    profile: ProfileResult = field(default_factory=ProfileResult)
    lines_read: int = 0
    lines_parsed: int = 0

    def summary(self) -> str:
        parts = [
            f"lines_read={self.lines_read}",
            f"lines_parsed={self.lines_parsed}",
        ]
        if self.profile.stages:
            parts.append(f"elapsed={self.profile.total_elapsed_seconds:.4f}s")
        return ", ".join(parts)


def run_benchmark(opts: BenchmarkOptions) -> BenchmarkResult:
    """Read and parse lines from *path*, collecting profiling metrics."""
    result = BenchmarkResult()
    profile = result.profile

    index = build_index_cached(opts.path, cache_dir=opts.cache_dir)
    offset = opts.start_offset

    raw_iter = iter_from_offset(opts.path, offset)

    def _limited():
        for i, raw in enumerate(raw_iter):
            if opts.max_lines is not None and i >= opts.max_lines:
                break
            yield raw

    def _to_parsed(raws):
        for i, raw in enumerate(raws):
            parsed = parse_line(raw, line_number=i + 1)
            yield parsed

    limited = list(profile_stage("read", _to_parsed(_limited()), profile))
    result.lines_read = len(limited)
    result.lines_parsed = sum(1 for ln in limited if ln.timestamp is not None)

    return result
