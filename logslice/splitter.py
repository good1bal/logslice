"""logslice.splitter — Split a log stream into multiple output files by time window or line count."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Iterator, List, Optional

from .parser import ParsedLine


@dataclass
class SplitOptions:
    """Configuration for splitting a log stream into chunks.

    Exactly one of *lines_per_file* or *window_seconds* must be set.

    Args:
        output_dir:      Directory where split files are written.
        prefix:          Filename prefix for each part (e.g. ``"app_"`` → ``app_001.log``).
        suffix:          Filename extension including the leading dot (default ``".log"``).
        lines_per_file:  Maximum number of lines per output file.  Mutually exclusive with
                         *window_seconds*.
        window_seconds:  Time window length in seconds.  Lines whose timestamp falls within
                         the same window land in the same file.  Mutually exclusive with
                         *lines_per_file*.
        zero_pad:        Width used when zero-padding the numeric part index (default 3).
    """

    output_dir: Path
    prefix: str = "part_"
    suffix: str = ".log"
    lines_per_file: Optional[int] = None
    window_seconds: Optional[float] = None
    zero_pad: int = 3

    def __post_init__(self) -> None:
        if self.lines_per_file is None and self.window_seconds is None:
            raise ValueError("Either lines_per_file or window_seconds must be set.")
        if self.lines_per_file is not None and self.window_seconds is not None:
            raise ValueError("lines_per_file and window_seconds are mutually exclusive.")
        if self.lines_per_file is not None and self.lines_per_file < 1:
            raise ValueError("lines_per_file must be >= 1.")
        if self.window_seconds is not None and self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0.")
        self.output_dir = Path(self.output_dir)


@dataclass
class SplitResult:
    """Summary returned by :func:`split_log`."""

    files_created: List[Path] = field(default_factory=list)
    total_lines: int = 0


def _part_path(opts: SplitOptions, index: int) -> Path:
    """Build the output path for part *index*."""
    name = f"{opts.prefix}{str(index).zfill(opts.zero_pad)}{opts.suffix}"
    return opts.output_dir / name


def _window_key(ts: Optional[datetime], window_seconds: float) -> Optional[int]:
    """Return an integer bucket index for *ts* given the window size.

    Lines without a timestamp are placed in the current open bucket.
    """
    if ts is None:
        return None
    epoch = datetime(1970, 1, 1, tzinfo=ts.tzinfo)
    delta = (ts - epoch).total_seconds()
    return int(delta // window_seconds)


def split_log(
    lines: Iterable[ParsedLine],
    opts: SplitOptions,
    *,
    open_fn: Callable[[Path], "_FileHandle"] = None,  # type: ignore[assignment]
) -> SplitResult:
    """Split *lines* into multiple files according to *opts*.

    The output directory is created if it does not exist.  Each part file is
    written as plain text (one raw log line per line).

    Args:
        lines:    Iterable of :class:`~logslice.parser.ParsedLine` objects.
        opts:     Splitting configuration.
        open_fn:  Optional factory used in tests to intercept file creation.
                  Receives a :class:`~pathlib.Path` and must return a
                  writable file-like object.

    Returns:
        A :class:`SplitResult` describing what was written.
    """
    opts.output_dir.mkdir(parents=True, exist_ok=True)

    if open_fn is None:
        open_fn = lambda p: open(p, "w", encoding="utf-8")  # noqa: E731

    result = SplitResult()
    current_file = None
    current_path: Optional[Path] = None
    part_index = 0
    line_count_in_part = 0
    current_bucket: Optional[int] = None

    def _next_part() -> None:
        nonlocal current_file, current_path, part_index, line_count_in_part
        if current_file is not None:
            current_file.close()
        current_path = _part_path(opts, part_index)
        current_file = open_fn(current_path)
        result.files_created.append(current_path)
        part_index += 1
        line_count_in_part = 0

    for parsed in lines:
        result.total_lines += 1

        if opts.lines_per_file is not None:
            # Rotate when the current part is full.
            if current_file is None or line_count_in_part >= opts.lines_per_file:
                _next_part()
        else:
            # Rotate when the timestamp crosses into a new window bucket.
            bucket = _window_key(parsed.timestamp, opts.window_seconds)  # type: ignore[arg-type]
            if bucket is None:
                bucket = current_bucket  # keep same file for timestamp-less lines
            if current_file is None or (bucket is not None and bucket != current_bucket):
                current_bucket = bucket
                _next_part()

        current_file.write(parsed.raw + "\n")  # type: ignore[union-attr]
        line_count_in_part += 1

    if current_file is not None:
        current_file.close()

    return result
