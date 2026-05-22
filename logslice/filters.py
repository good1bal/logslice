"""Severity and time-range filter predicates for log lines."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Set

from logslice.parser import ParsedLine

# Canonical severity ordering (lower index = less severe)
SEVERITY_ORDER = ["DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"]

_NORMALIZED: dict[str, str] = {
    "WARN": "WARNING",
    "FATAL": "CRITICAL",
}


def normalize_severity(level: str) -> str:
    """Normalize severity aliases to a canonical form."""
    upper = level.upper()
    return _NORMALIZED.get(upper, upper)


def severity_rank(level: str) -> int:
    """Return a numeric rank for comparison; unknown levels get rank 0."""
    normalized = normalize_severity(level)
    try:
        return SEVERITY_ORDER.index(normalized)
    except ValueError:
        return 0


def make_severity_filter(
    min_level: Optional[str] = None,
    include_levels: Optional[Set[str]] = None,
) -> "SeverityFilter":
    """Factory that returns an appropriate SeverityFilter instance."""
    if include_levels is not None:
        return ExactSeverityFilter(include_levels)
    if min_level is not None:
        return MinSeverityFilter(min_level)
    return AcceptAllFilter()


class SeverityFilter:
    """Base class for severity filters."""

    def accepts(self, line: ParsedLine) -> bool:  # pragma: no cover
        raise NotImplementedError


class AcceptAllFilter(SeverityFilter):
    """Accepts every line regardless of severity."""

    def accepts(self, line: ParsedLine) -> bool:
        return True


class MinSeverityFilter(SeverityFilter):
    """Accepts lines whose severity is >= *min_level*."""

    def __init__(self, min_level: str) -> None:
        self._min_rank = severity_rank(min_level)

    def accepts(self, line: ParsedLine) -> bool:
        if line.severity is None:
            return True  # lines without severity pass through
        return severity_rank(line.severity) >= self._min_rank


class ExactSeverityFilter(SeverityFilter):
    """Accepts lines whose severity is in the supplied set."""

    def __init__(self, levels: Set[str]) -> None:
        self._levels = {normalize_severity(l) for l in levels}

    def accepts(self, line: ParsedLine) -> bool:
        if line.severity is None:
            return True
        return normalize_severity(line.severity) in self._levels


def in_time_range(
    line: ParsedLine,
    start: Optional[datetime],
    end: Optional[datetime],
) -> bool:
    """Return True when *line* falls within [start, end] (inclusive)."""
    ts = line.timestamp
    if ts is None:
        return True  # lines without timestamps are never excluded by time
    if start is not None and ts < start:
        return False
    if end is not None and ts > end:
        return False
    return True
