"""Summarizer: produce a human-readable summary of a log slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from logslice.stats import SliceStats


@dataclass
class SummaryOptions:
    """Options controlling what the summary includes."""

    show_severity_counts: bool = True
    show_time_span: bool = True
    show_skipped: bool = True
    top_n_errors: int = 3


@dataclass
class LogSummary:
    """Aggregated summary data for a processed log slice."""

    total_lines: int = 0
    matched_lines: int = 0
    skipped_lines: int = 0
    severity_counts: Dict[str, int] = field(default_factory=dict)
    time_span_seconds: Optional[float] = None
    sample_errors: List[str] = field(default_factory=list)


def build_summary(
    stats: SliceStats,
    lines,
    options: Optional[SummaryOptions] = None,
) -> LogSummary:
    """Build a :class:`LogSummary` from *stats* and the matched *lines*.

    Parameters
    ----------
    stats:
        A :class:`~logslice.stats.SliceStats` instance produced by
        :func:`~logslice.stats.collect_stats`.
    lines:
        Iterable of :class:`~logslice.parser.ParsedLine` objects that passed
        all filters.
    options:
        Optional display/collection options.
    """
    if options is None:
        options = SummaryOptions()

    severity_counts: Dict[str, int] = {}
    sample_errors: List[str] = []
    matched = 0

    for pl in lines:
        matched += 1
        sev = (pl.severity or "UNKNOWN").upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if sev in ("ERROR", "FATAL", "CRITICAL") and len(sample_errors) < options.top_n_errors:
            sample_errors.append(pl.raw.rstrip("\n"))

    return LogSummary(
        total_lines=stats.total_lines,
        matched_lines=matched,
        skipped_lines=stats.skipped_lines,
        severity_counts=severity_counts,
        time_span_seconds=stats.time_span_seconds,
        sample_errors=sample_errors,
    )


def format_summary(summary: LogSummary, options: Optional[SummaryOptions] = None) -> str:
    """Render a :class:`LogSummary` as a printable string."""
    if options is None:
        options = SummaryOptions()

    lines: List[str] = ["=== Log Slice Summary ==="]
    lines.append(f"  Total lines  : {summary.total_lines}")
    lines.append(f"  Matched lines: {summary.matched_lines}")

    if options.show_skipped:
        lines.append(f"  Skipped lines: {summary.skipped_lines}")

    if options.show_time_span and summary.time_span_seconds is not None:
        lines.append(f"  Time span    : {summary.time_span_seconds:.1f}s")

    if options.show_severity_counts and summary.severity_counts:
        lines.append("  Severity breakdown:")
        for sev, count in sorted(summary.severity_counts.items()):
            lines.append(f"    {sev:<10}: {count}")

    if summary.sample_errors:
        lines.append(f"  Sample errors (up to {options.top_n_errors}):")
        for err in summary.sample_errors:
            lines.append(f"    > {err}")

    return "\n".join(lines)
