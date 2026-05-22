"""Convert between log formats using the exporter pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from logslice.exporter import ExportFormat, ExportOptions, export_to_file
from logslice.parser import ParsedLine, parse_line


@dataclass
class ConvertOptions:
    source: Path
    destination: Path
    fmt: ExportFormat = "jsonl"
    include_line_numbers: bool = False
    encoding: str = "utf-8"


def _iter_source(path: Path, encoding: str) -> Iterator[ParsedLine]:
    with path.open(encoding=encoding, errors="replace") as fh:
        for number, raw in enumerate(fh, start=1):
            raw = raw.rstrip("\n")
            parsed = parse_line(raw)
            parsed = ParsedLine(
                raw=parsed.raw,
                timestamp=parsed.timestamp,
                severity=parsed.severity,
                line_number=number,
            )
            yield parsed


def convert_log(opts: ConvertOptions) -> int:
    """Convert *source* log to *destination* in the requested format.

    Returns the number of lines written.
    """
    if not opts.source.exists():
        raise FileNotFoundError(f"Source log not found: {opts.source}")

    export_opts = ExportOptions(
        format=opts.fmt,
        include_line_numbers=opts.include_line_numbers,
    )
    lines = _iter_source(opts.source, opts.encoding)
    return export_to_file(lines, export_opts, opts.destination)
