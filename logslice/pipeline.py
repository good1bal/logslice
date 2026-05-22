"""High-level pipeline that wires parser, filters, formatter, and stats."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import IO, Iterator, Optional, Set

from logslice.filters import SeverityFilter, in_time_range, make_severity_filter
from logslice.formatter import FormatOptions, format_line
from logslice.parser import ParsedLine, parse_line
from logslice.stats import SliceStats, collect_stats


@dataclass
class PipelineOptions:
    """All knobs exposed to the CLI / library consumers."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None
    min_level: Optional[str] = None
    include_levels: Optional[Set[str]] = None
    format_options: FormatOptions = field(default_factory=FormatOptions)
    collect_statistics: bool = False


@dataclass
class PipelineResult:
    """Returned by :func:`run_pipeline`."""

    lines_written: int
    stats: Optional[SliceStats] = None


def _iter_parsed(source: IO[str]) -> Iterator[ParsedLine]:
    """Yield :class:`ParsedLine` objects from an open text stream."""
    for raw_line in source:
        yield parse_line(raw_line.rstrip("\n"))


def _apply_filters(
    lines: Iterator[ParsedLine],
    severity_filter: SeverityFilter,
    start: Optional[datetime],
    end: Optional[datetime],
) -> Iterator[ParsedLine]:
    for line in lines:
        if not in_time_range(line, start, end):
            continue
        if not severity_filter.accepts(line):
            continue
        yield line


def run_pipeline(
    source: IO[str],
    dest: IO[str],
    options: Optional[PipelineOptions] = None,
) -> PipelineResult:
    """Read *source*, filter, format, and write matching lines to *dest*.

    Returns a :class:`PipelineResult` with the count of written lines and
    optional statistics when *options.collect_statistics* is True.
    """
    if options is None:
        options = PipelineOptions()

    severity_filter = make_severity_filter(
        min_level=options.min_level,
        include_levels=options.include_levels,
    )

    all_parsed: list[ParsedLine] = list(_iter_parsed(source))
    matched: list[ParsedLine] = list(
        _apply_filters(
            iter(all_parsed),
            severity_filter,
            options.start,
            options.end,
        )
    )

    lines_written = 0
    for number, parsed in enumerate(matched, start=1):
        formatted = format_line(parsed, options.format_options, line_number=number)
        dest.write(formatted + "\n")
        lines_written += 1

    stats: Optional[SliceStats] = None
    if options.collect_statistics:
        stats = collect_stats(all_parsed, matched)

    return PipelineResult(lines_written=lines_written, stats=stats)
