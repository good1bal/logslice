"""Merge multiple sorted log streams into a single time-ordered sequence."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional

from logslice.parser import ParsedLine


@dataclass
class MergeOptions:
    """Options controlling how log streams are merged."""

    sources: List[Iterable[ParsedLine]] = field(default_factory=list)
    # When True, lines without a timestamp sort before timestamped lines.
    nulls_first: bool = False
    # Tag each output line with which source index it came from.
    tag_source: bool = False


def _sort_key(line: ParsedLine, nulls_first: bool) -> tuple:
    """Return a comparable key for heap ordering."""
    if line.timestamp is None:
        # Use a sentinel so None timestamps sort consistently.
        sentinel = (0,) if nulls_first else (2,)
        return sentinel + (line.line_number,)
    return (1, line.timestamp, line.line_number)


def merge_logs(
    options: MergeOptions,
) -> Iterator[ParsedLine]:
    """Yield ParsedLine objects from all sources in ascending timestamp order.

    Sources are assumed to be individually sorted.  A k-way heap merge is used
    so only one line per source is held in memory at a time.
    """
    # Each heap entry: (sort_key, source_index, line)
    heap: list = []

    iterators = [iter(src) for src in options.sources]

    for src_idx, it in enumerate(iterators):
        line = next(it, None)
        if line is not None:
            key = _sort_key(line, options.nulls_first)
            heapq.heappush(heap, (key, src_idx, line))

    while heap:
        key, src_idx, line = heapq.heappop(heap)

        if options.tag_source:
            # Annotate the raw text with the source index as a prefix tag.
            tagged_text = f"[src:{src_idx}] {line.raw}"
            line = ParsedLine(
                raw=tagged_text,
                timestamp=line.timestamp,
                severity=line.severity,
                message=line.message,
                line_number=line.line_number,
            )

        yield line

        nxt = next(iterators[src_idx], None)
        if nxt is not None:
            nxt_key = _sort_key(nxt, options.nulls_first)
            heapq.heappush(heap, (nxt_key, src_idx, nxt))
