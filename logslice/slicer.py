"""Core slicer: streams a log file and yields lines matching time/severity filters."""

from datetime import datetime
from typing import Generator, Optional

from logslice.parser import ParsedLine, parse_line, SEVERITY_ORDER


def slice_log(
    filepath: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    min_severity: Optional[str] = None,
    encoding: str = "utf-8",
) -> Generator[ParsedLine, None, None]:
    """
    Stream *filepath* line-by-line, yielding only lines that satisfy
    the given time range and minimum severity constraints.

    Args:
        filepath:     Path to the log file.
        start:        Inclusive lower bound for the log timestamp.
        end:          Inclusive upper bound for the log timestamp.
        min_severity: Minimum severity level (e.g. "WARNING").
        encoding:     File encoding (default utf-8).

    Yields:
        ParsedLine objects that pass all active filters.
    """
    min_order: int = SEVERITY_ORDER.get(min_severity.upper(), 0) if min_severity else -1

    with open(filepath, "r", encoding=encoding, errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            if not line:
                continue

            parsed = parse_line(line)

            # --- timestamp filter ---
            if parsed.timestamp is not None:
                if start and parsed.timestamp < start:
                    continue
                if end and parsed.timestamp > end:
                    continue
            elif start or end:
                # Line has no parseable timestamp; skip when a time filter is active
                continue

            # --- severity filter ---
            if min_severity:
                if parsed.severity_order < min_order:
                    continue

            yield parsed
