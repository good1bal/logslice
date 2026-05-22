"""Output formatters for sliced log lines."""

from dataclasses import dataclass
from typing import List, Optional
from logslice.parser import ParsedLine


@dataclass
class FormatOptions:
    """Options controlling output format."""
    show_line_numbers: bool = False
    colorize: bool = False
    output_format: str = "plain"  # plain | json | csv


SEVERITY_COLORS = {
    "ERROR": "\033[31m",    # red
    "WARN":  "\033[33m",    # yellow
    "WARNING": "\033[33m",  # yellow
    "INFO":  "\033[32m",    # green
    "DEBUG": "\033[36m",    # cyan
}
RESET_COLOR = "\033[0m"


def _colorize_line(line: ParsedLine) -> str:
    """Wrap a log line in ANSI color based on severity."""
    color = SEVERITY_COLORS.get((line.severity or "").upper(), "")
    if not color:
        return line.raw
    return f"{color}{line.raw}{RESET_COLOR}"


def format_line(line: ParsedLine, options: FormatOptions, index: Optional[int] = None) -> str:
    """Format a single ParsedLine according to FormatOptions."""
    if options.output_format == "json":
        import json
        record = {
            "timestamp": line.timestamp.isoformat() if line.timestamp else None,
            "severity": line.severity,
            "message": line.message,
        }
        if options.show_line_numbers and index is not None:
            record["line"] = index
        return json.dumps(record)

    if options.output_format == "csv":
        ts = line.timestamp.isoformat() if line.timestamp else ""
        severity = line.severity or ""
        message = (line.message or "").replace('"', '""')
        row = f'{ts},{severity},"{message}"'
        if options.show_line_numbers and index is not None:
            row = f"{index},{row}"
        return row

    # plain
    text = _colorize_line(line) if options.colorize else line.raw
    if options.show_line_numbers and index is not None:
        text = f"{index:>6}: {text}"
    return text


def format_lines(
    lines: List[ParsedLine],
    options: Optional[FormatOptions] = None,
    start_index: int = 1,
) -> List[str]:
    """Format a list of ParsedLines, returning ready-to-print strings."""
    if options is None:
        options = FormatOptions()
    result = []
    for i, line in enumerate(lines, start=start_index):
        idx = i if options.show_line_numbers else None
        result.append(format_line(line, options, index=idx))
    return result
