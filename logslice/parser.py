"""Log line parser: extracts timestamp and severity from a log line."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Matches: 2024-01-15 12:34:56,789 or 2024-01-15T12:34:56.789
TIMESTAMP_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,]?\d*)"
)

SEVERITY_LEVELS = ["TRACE", "DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"]
SEVERITY_RE = re.compile(
    r"\b(?P<level>" + "|".join(SEVERITY_LEVELS) + r")\b"
)

SEVERITY_ORDER = {
    "TRACE": 0,
    "DEBUG": 1,
    "INFO": 2,
    "WARNING": 3,
    "WARN": 3,
    "ERROR": 4,
    "CRITICAL": 5,
    "FATAL": 5,
}

TS_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S,%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S,%f",
    "%Y-%m-%d %H:%M:%S",
]


@dataclass
class ParsedLine:
    raw: str
    timestamp: Optional[datetime]
    severity: Optional[str]
    severity_order: int


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Try parsing a timestamp string against known formats."""
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def parse_line(line: str) -> ParsedLine:
    """Parse a single log line into a ParsedLine dataclass."""
    timestamp: Optional[datetime] = None
    severity: Optional[str] = None
    severity_order: int = -1

    ts_match = TIMESTAMP_RE.search(line)
    if ts_match:
        timestamp = parse_timestamp(ts_match.group("ts"))

    sev_match = SEVERITY_RE.search(line)
    if sev_match:
        severity = sev_match.group("level")
        severity_order = SEVERITY_ORDER.get(severity, -1)

    return ParsedLine(
        raw=line,
        timestamp=timestamp,
        severity=severity,
        severity_order=severity_order,
    )
