"""Hard line-count and byte-count quotas for log slicing pipelines.

Quotas let callers stop iteration early once a maximum number of lines or
bytes has been consumed, complementing time-range and severity filters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from logslice.parser import ParsedLine


@dataclass
class QuotaOptions:
    """Limits applied to a stream of :class:`ParsedLine` objects."""

    max_lines: int = 0   # 0 = unlimited
    max_bytes: int = 0   # 0 = unlimited; measured on raw text

    def __post_init__(self) -> None:
        if self.max_lines < 0:
            raise ValueError("max_lines must be >= 0")
        if self.max_bytes < 0:
            raise ValueError("max_bytes must be >= 0")


@dataclass
class QuotaResult:
    """Summary returned after applying a quota to a stream."""

    lines_emitted: int = 0
    bytes_emitted: int = 0
    truncated: bool = False


def apply_quota(
    source: Iterable[ParsedLine],
    options: QuotaOptions | None = None,
) -> Iterator[ParsedLine]:
    """Yield lines from *source* until any active quota is exceeded.

    Iteration stops *before* emitting the line that would breach the limit,
    so the output always satisfies ``len(result) <= max_lines`` and
    ``sum(len(l.raw) for l in result) <= max_bytes``.
    """
    opts = options or QuotaOptions()
    lines_seen = 0
    bytes_seen = 0

    for line in source:
        line_bytes = len(line.raw.encode())

        if opts.max_lines and lines_seen >= opts.max_lines:
            return
        if opts.max_bytes and bytes_seen + line_bytes > opts.max_bytes:
            return

        yield line
        lines_seen += 1
        bytes_seen += line_bytes


def collect_quota_result(
    source: Iterable[ParsedLine],
    options: QuotaOptions | None = None,
) -> tuple[list[ParsedLine], QuotaResult]:
    """Materialise *source* under quota and return lines + a result summary."""
    opts = options or QuotaOptions()
    all_lines = list(source)
    kept: list[ParsedLine] = []
    result = QuotaResult()

    for line in apply_quota(iter(all_lines), opts):
        kept.append(line)
        result.lines_emitted += 1
        result.bytes_emitted += len(line.raw.encode())

    result.truncated = len(kept) < len(all_lines)
    return kept, result
