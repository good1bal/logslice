"""Collect and report statistics about a sliced log segment."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional

from logslice.filters import normalize_severity
from logslice.parser import ParsedLine


@dataclass
class SliceStats:
    """Aggregated statistics produced by :func:`collect_stats`."""

    total_lines: int = 0
    matched_lines: int = 0
    severity_counts: Counter = field(default_factory=Counter)
    earliest: Optional[datetime] = None
    latest: Optional[datetime] = None

    # ------------------------------------------------------------------ #
    # Derived properties
    # ------------------------------------------------------------------ #

    @property
    def skipped_lines(self) -> int:
        return self.total_lines - self.matched_lines

    @property
    def time_span_seconds(self) -> Optional[float]:
        if self.earliest is None or self.latest is None:
            return None
        return (self.latest - self.earliest).total_seconds()

    def as_dict(self) -> dict:
        return {
            "total_lines": self.total_lines,
            "matched_lines": self.matched_lines,
            "skipped_lines": self.skipped_lines,
            "severity_counts": dict(self.severity_counts),
            "earliest": self.earliest.isoformat() if self.earliest else None,
            "latest": self.latest.isoformat() if self.latest else None,
            "time_span_seconds": self.time_span_seconds,
        }


def collect_stats(
    all_lines: Iterable[ParsedLine],
    matched_lines: Iterable[ParsedLine],
) -> SliceStats:
    """Build a :class:`SliceStats` from two iterables.

    Both iterables are consumed exactly once; callers must pass
    pre-materialised lists if they need the data afterwards.
    """
    stats = SliceStats()

    for line in all_lines:
        stats.total_lines += 1

    for line in matched_lines:
        stats.matched_lines += 1
        if line.severity:
            key = normalize_severity(line.severity)
            stats.severity_counts[key] += 1
        if line.timestamp is not None:
            if stats.earliest is None or line.timestamp < stats.earliest:
                stats.earliest = line.timestamp
            if stats.latest is None or line.timestamp > stats.latest:
                stats.latest = line.timestamp

    return stats
