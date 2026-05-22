"""Tail-style file watcher that emits new lines as they appear."""

from __future__ import annotations

import time
import os
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional

from logslice.parser import ParsedLine, parse_line
from logslice.filters import SeverityFilter


@dataclass
class WatchOptions:
    """Configuration for the file watcher."""
    poll_interval: float = 0.5          # seconds between stat checks
    max_idle: Optional[float] = None    # stop after this many idle seconds
    severity_filter: Optional[SeverityFilter] = None
    line_callback: Optional[Callable[[ParsedLine], None]] = None


def _read_new_lines(fp, line_no_start: int) -> Iterator[ParsedLine]:
    """Read any new content from *fp* and yield ParsedLine objects."""
    line_no = line_no_start
    while True:
        raw = fp.readline()
        if not raw:
            break
        line_no += 1
        yield parse_line(raw.rstrip("\n"), line_no)


def watch_file(path: str, opts: Optional[WatchOptions] = None) -> Iterator[ParsedLine]:
    """Yield :class:`ParsedLine` objects for every new line appended to *path*.

    Blocks indefinitely (or until *opts.max_idle* seconds elapse with no new
    data) polling the file for growth.
    """
    if opts is None:
        opts = WatchOptions()

    filt = opts.severity_filter
    line_no = 0
    idle_elapsed = 0.0

    with open(path, "r", encoding="utf-8", errors="replace") as fp:
        # Seek to end so we only see *new* lines.
        fp.seek(0, os.SEEK_END)

        while True:
            new_lines = list(_read_new_lines(fp, line_no))
            if new_lines:
                idle_elapsed = 0.0
                line_no += len(new_lines)
                for pl in new_lines:
                    if filt is None or filt.accepts(pl):
                        if opts.line_callback:
                            opts.line_callback(pl)
                        yield pl
            else:
                time.sleep(opts.poll_interval)
                idle_elapsed += opts.poll_interval
                if opts.max_idle is not None and idle_elapsed >= opts.max_idle:
                    return
