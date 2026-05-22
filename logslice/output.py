"""Output writers for logslice — write filtered lines to files or stdout."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Iterable, Optional

from logslice.formatter import FormatOptions, format_lines
from logslice.parser import ParsedLine


@dataclass
class OutputOptions:
    """Configuration for where and how output is written."""

    destination: Optional[Path] = None  # None means stdout
    format_options: FormatOptions = field(default_factory=FormatOptions)
    encoding: str = "utf-8"
    append: bool = False


def _open_destination(opts: OutputOptions) -> IO[str]:
    """Return an open file handle for the configured destination."""
    if opts.destination is None:
        return sys.stdout
    mode = "a" if opts.append else "w"
    return open(opts.destination, mode, encoding=opts.encoding)


def write_lines(
    lines: Iterable[ParsedLine],
    opts: OutputOptions,
) -> int:
    """Write *lines* according to *opts*.

    Returns the number of lines written.
    """
    to_stdout = opts.destination is None
    handle = _open_destination(opts)
    count = 0
    try:
        for formatted in format_lines(lines, opts.format_options):
            handle.write(formatted)
            if not formatted.endswith("\n"):
                handle.write("\n")
            count += 1
    finally:
        if not to_stdout:
            handle.close()
    return count


def write_lines_to_stream(
    lines: Iterable[ParsedLine],
    stream: IO[str],
    fmt: Optional[FormatOptions] = None,
) -> int:
    """Write *lines* to an already-open *stream*. Useful for testing."""
    fmt = fmt or FormatOptions()
    count = 0
    for formatted in format_lines(lines, fmt):
        stream.write(formatted)
        if not formatted.endswith("\n"):
            stream.write("\n")
        count += 1
    return count
