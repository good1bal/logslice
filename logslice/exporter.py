"""Export filtered log lines to various file formats (CSV, JSONL, plain text)."""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from logslice.parser import ParsedLine

ExportFormat = Literal["plain", "jsonl", "csv"]


@dataclass
class ExportOptions:
    format: ExportFormat = "plain"
    include_line_numbers: bool = False
    extra_fields: list[str] = field(default_factory=list)


def _line_to_dict(line: ParsedLine, opts: ExportOptions) -> dict:
    record: dict = {
        "timestamp": line.timestamp.isoformat() if line.timestamp else None,
        "severity": line.severity,
        "message": line.raw,
    }
    if opts.include_line_numbers:
        record["line_number"] = line.line_number
    return record


def export_plain(lines: Iterable[ParsedLine], opts: ExportOptions) -> str:
    parts = []
    for line in lines:
        prefix = f"{line.line_number}: " if opts.include_line_numbers else ""
        parts.append(f"{prefix}{line.raw}")
    return "\n".join(parts)


def export_jsonl(lines: Iterable[ParsedLine], opts: ExportOptions) -> str:
    rows = [json.dumps(_line_to_dict(ln, opts)) for ln in lines]
    return "\n".join(rows)


def export_csv(lines: Iterable[ParsedLine], opts: ExportOptions) -> str:
    buf = io.StringIO()
    base_fields = ["timestamp", "severity", "message"]
    if opts.include_line_numbers:
        base_fields = ["line_number"] + base_fields
    writer = csv.DictWriter(buf, fieldnames=base_fields, extrasaction="ignore")
    writer.writeheader()
    for line in lines:
        writer.writerow(_line_to_dict(line, opts))
    return buf.getvalue().rstrip("\n")


def export_lines(lines: Iterable[ParsedLine], opts: ExportOptions) -> str:
    """Dispatch to the correct exporter based on opts.format."""
    collected = list(lines)
    if opts.format == "jsonl":
        return export_jsonl(collected, opts)
    if opts.format == "csv":
        return export_csv(collected, opts)
    return export_plain(collected, opts)


def export_to_file(
    lines: Iterable[ParsedLine], opts: ExportOptions, dest: Path
) -> int:
    """Write exported content to *dest*; return number of lines written."""
    collected = list(lines)
    content = export_lines(collected, opts)
    dest.write_text(content, encoding="utf-8")
    return len(collected)
