"""logslice — Fast log file slicer.

Public re-exports for the most commonly used symbols.
"""

from logslice.cache import CacheEntry, load_cache, save_cache
from logslice.chunker import Chunk, ChunkOptions, chunk_lines
from logslice.converter import ConvertOptions, convert_log
from logslice.deduplicator import DeduplicatorOptions, deduplicate
from logslice.exporter import ExportOptions, export_csv, export_jsonl, export_plain
from logslice.filters import (
    SeverityFilter,
    make_severity_filter,
    normalize_severity,
    severity_rank,
)
from logslice.formatter import FormatOptions, format_line, format_lines
from logslice.highlighter import HighlightRule, Highlighter
from logslice.indexer import build_index, build_index_cached, find_start_offset
from logslice.merger import MergeOptions, merge_logs
from logslice.output import OutputOptions, write_lines, write_lines_to_stream
from logslice.parser import ParsedLine, parse_line, parse_timestamp
from logslice.pipeline import PipelineOptions, PipelineResult, run_pipeline
from logslice.sampler import SamplerOptions, sample_lines
from logslice.slicer import slice_log
from logslice.stats import SliceStats, collect_stats
from logslice.summarizer import LogSummary, SummaryOptions, build_summary, format_summary
from logslice.tail import TailOptions, run_tail
from logslice.watcher import WatchOptions, watch_file

__all__ = [
    # cache
    "CacheEntry",
    "load_cache",
    "save_cache",
    # chunker
    "Chunk",
    "ChunkOptions",
    "chunk_lines",
    # converter
    "ConvertOptions",
    "convert_log",
    # deduplicator
    "DeduplicatorOptions",
    "deduplicate",
    # exporter
    "ExportOptions",
    "export_csv",
    "export_jsonl",
    "export_plain",
    # filters
    "SeverityFilter",
    "make_severity_filter",
    "normalize_severity",
    "severity_rank",
    # formatter
    "FormatOptions",
    "format_line",
    "format_lines",
    # highlighter
    "HighlightRule",
    "Highlighter",
    # indexer
    "build_index",
    "build_index_cached",
    "find_start_offset",
    # merger
    "MergeOptions",
    "merge_logs",
    # output
    "OutputOptions",
    "write_lines",
    "write_lines_to_stream",
    # parser
    "ParsedLine",
    "parse_line",
    "parse_timestamp",
    # pipeline
    "PipelineOptions",
    "PipelineResult",
    "run_pipeline",
    # sampler
    "SamplerOptions",
    "sample_lines",
    # slicer
    "slice_log",
    # stats
    "SliceStats",
    "collect_stats",
    # summarizer
    "LogSummary",
    "SummaryOptions",
    "build_summary",
    "format_summary",
    # tail
    "TailOptions",
    "run_tail",
    # watcher
    "WatchOptions",
    "watch_file",
]
