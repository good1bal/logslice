"""Profiler: measures timing and throughput for pipeline stages."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional

from logslice.parser import ParsedLine


@dataclass
class StageMetric:
    name: str
    elapsed_seconds: float
    line_count: int

    @property
    def lines_per_second(self) -> float:
        if self.elapsed_seconds == 0.0:
            return 0.0
        return self.line_count / self.elapsed_seconds


@dataclass
class ProfileResult:
    stages: List[StageMetric] = field(default_factory=list)
    total_elapsed_seconds: float = 0.0
    total_lines: int = 0

    def add(self, metric: StageMetric) -> None:
        self.stages.append(metric)
        self.total_elapsed_seconds += metric.elapsed_seconds
        self.total_lines = max(self.total_lines, metric.line_count)

    def as_dict(self) -> dict:
        return {
            "total_elapsed_seconds": round(self.total_elapsed_seconds, 6),
            "total_lines": self.total_lines,
            "stages": [
                {
                    "name": m.name,
                    "elapsed_seconds": round(m.elapsed_seconds, 6),
                    "line_count": m.line_count,
                    "lines_per_second": round(m.lines_per_second, 2),
                }
                for m in self.stages
            ],
        }


def profile_stage(
    name: str,
    source: Iterator[ParsedLine],
    result: ProfileResult,
) -> Iterator[ParsedLine]:
    """Wrap an iterator to measure elapsed time and line count for a stage."""
    count = 0
    start = time.perf_counter()
    for line in source:
        count += 1
        yield line
    elapsed = time.perf_counter() - start
    result.add(StageMetric(name=name, elapsed_seconds=elapsed, line_count=count))


def format_profile(result: ProfileResult) -> str:
    """Return a human-readable summary of profiling results."""
    lines = [f"Profile: {result.total_lines} lines in {result.total_elapsed_seconds:.4f}s"]
    for m in result.stages:
        lines.append(
            f"  [{m.name}] {m.line_count} lines, "
            f"{m.elapsed_seconds:.4f}s, "
            f"{m.lines_per_second:.1f} lines/s"
        )
    return "\n".join(lines)
