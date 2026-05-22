"""High-level 'tail -f' command integration for logslice CLI."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional, TextIO

from logslice.watcher import WatchOptions, watch_file
from logslice.filters import make_severity_filter, SeverityFilter
from logslice.formatter import FormatOptions, format_line


@dataclass
class TailOptions:
    """Options for the tail command."""
    path: str
    min_severity: Optional[str] = None
    output_format: str = "plain"        # 'plain' or 'json'
    colorize: bool = False
    show_line_numbers: bool = False
    poll_interval: float = 0.5
    max_idle: Optional[float] = None    # useful for testing / scripting


def run_tail(
    opts: TailOptions,
    stream: Optional[TextIO] = None,
) -> int:
    """Stream new log lines from *opts.path* to *stream* (default: stdout).

    Returns the number of lines written.
    """
    if stream is None:
        stream = sys.stdout

    filt: Optional[SeverityFilter] = None
    if opts.min_severity:
        filt = make_severity_filter(min_severity=opts.min_severity)

    watch_opts = WatchOptions(
        poll_interval=opts.poll_interval,
        max_idle=opts.max_idle,
        severity_filter=filt,
    )

    fmt_opts = FormatOptions(
        output_format=opts.output_format,
        colorize=opts.colorize,
        show_line_numbers=opts.show_line_numbers,
    )

    count = 0
    for parsed in watch_file(opts.path, watch_opts):
        line_out = format_line(parsed, fmt_opts)
        stream.write(line_out + "\n")
        stream.flush()
        count += 1

    return count
