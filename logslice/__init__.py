"""logslice — Fast log file slicer that filters by time range and severity.

Public API surface for the logslice package.  Import the most commonly used
symbols from here so callers don't need to know the internal module layout.

Example
-------
>>> from logslice import run_pipeline, PipelineOptions
>>> opts = PipelineOptions(log_path="app.log", min_severity="ERROR")
>>> result = run_pipeline(opts)
>>> for line in result.lines:
...     print(line.raw)
"""

from importlib.metadata import PackageNotFoundError, version

# ---------------------------------------------------------------------------
# Package version
# ---------------------------------------------------------------------------
try:
    __version__: str = version("logslice")
except PackageNotFoundError:  # running from source without installation
    __version__ = "0.0.0.dev0"

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------
from logslice.parser import ParsedLine, parse_line, parse_timestamp
from logslice.filters import (
    SeverityFilter,
    make_severity_filter,
    normalize_severity,
    severity_rank,
)
from logslice.formatter import FormatOptions, format_line, format_lines
from logslice.stats import SliceStats, collect_stats
from logslice.pipeline import PipelineOptions, PipelineResult, run_pipeline
from logslice.output import OutputOptions, write_lines, write_lines_to_stream
from logslice.indexer import (
    build_index,
    build_index_cached,
    find_start_offset,
    iter_from_offset,
)
from logslice.slicer import slice_log
from logslice.tail import TailOptions, run_tail
from logslice.watcher import WatchOptions, watch_file

__all__ = [
    # version
    "__version__",
    # parser
    "ParsedLine",
    "parse_line",
    "parse_timestamp",
    # filters
    "SeverityFilter",
    "make_severity_filter",
    "normalize_severity",
    "severity_rank",
    # formatter
    "FormatOptions",
    "format_line",
    "format_lines",
    # stats
    "SliceStats",
    "collect_stats",
    # pipeline
    "PipelineOptions",
    "PipelineResult",
    "run_pipeline",
    # output
    "OutputOptions",
    "write_lines",
    "write_lines_to_stream",
    # indexer
    "build_index",
    "build_index_cached",
    "find_start_offset",
    "iter_from_offset",
    # slicer
    "slice_log",
    # tail / watch
    "TailOptions",
    "run_tail",
    "WatchOptions",
    "watch_file",
]
