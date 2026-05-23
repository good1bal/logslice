"""chunker.py — Split a log file into time-based or size-based chunks.

Each chunk is a contiguous slice of parsed lines that falls within a
calculated boundary.  Useful for parallel processing or breaking large
log files into manageable pieces before export.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Iterator, List, Optional

from logslice.parser import ParsedLine


@dataclass
class ChunkOptions:
    """Configuration for the chunking strategy.

    Exactly one of *max_lines*, *max_seconds*, or *max_bytes* should be
    set.  If more than one is provided, they are applied conjunctively
    (a new chunk starts when *any* limit is exceeded).

    Attributes:
        max_lines:   Start a new chunk after this many lines.
        max_seconds: Start a new chunk when the timestamp span within the
                     current chunk exceeds this many seconds.
        max_bytes:   Start a new chunk when the total raw-text length of
                     lines in the current chunk exceeds this many bytes.
    """

    max_lines: Optional[int] = None
    max_seconds: Optional[float] = None
    max_bytes: Optional[int] = None

    def __post_init__(self) -> None:
        if self.max_lines is not None and self.max_lines < 1:
            raise ValueError("max_lines must be >= 1")
        if self.max_seconds is not None and self.max_seconds <= 0:
            raise ValueError("max_seconds must be > 0")
        if self.max_bytes is not None and self.max_bytes < 1:
            raise ValueError("max_bytes must be >= 1")
        if all(v is None for v in (self.max_lines, self.max_seconds, self.max_bytes)):
            raise ValueError(
                "At least one of max_lines, max_seconds, or max_bytes must be set"
            )


@dataclass
class Chunk:
    """A single chunk produced by :func:`chunk_lines`.

    Attributes:
        index:      Zero-based chunk sequence number.
        lines:      The :class:`~logslice.parser.ParsedLine` objects in
                    this chunk.
        start_time: Timestamp of the first line that carries one, or
                    ``None`` if no timestamps were found.
        end_time:   Timestamp of the last line that carries one, or
                    ``None``.
    """

    index: int
    lines: List[ParsedLine] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def line_count(self) -> int:
        """Number of lines in this chunk."""
        return len(self.lines)

    @property
    def byte_count(self) -> int:
        """Total UTF-8 byte length of all raw lines in this chunk."""
        return sum(len(ln.raw.encode()) for ln in self.lines)

    @property
    def span_seconds(self) -> Optional[float]:
        """Wall-clock seconds between the first and last timestamped line.

        Returns ``None`` when fewer than two timestamped lines exist.
        """
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()


def _flush(buf: List[ParsedLine], idx: int) -> Chunk:
    """Create a :class:`Chunk` from *buf* and clear it in-place."""
    timestamps = [ln.timestamp for ln in buf if ln.timestamp is not None]
    chunk = Chunk(
        index=idx,
        lines=list(buf),
        start_time=timestamps[0] if timestamps else None,
        end_time=timestamps[-1] if timestamps else None,
    )
    buf.clear()
    return chunk


def chunk_lines(
    lines: Iterable[ParsedLine],
    options: ChunkOptions,
) -> Iterator[Chunk]:
    """Yield :class:`Chunk` objects by splitting *lines* according to *options*.

    The generator is lazy — it consumes *lines* one at a time and emits a
    chunk as soon as any configured limit is reached.  A final (possibly
    smaller) chunk is emitted for any remaining lines after the iterable
    is exhausted.

    Args:
        lines:   An iterable of :class:`~logslice.parser.ParsedLine`.
        options: Chunking thresholds.

    Yields:
        :class:`Chunk` instances in order.
    """
    buf: List[ParsedLine] = []
    chunk_idx = 0
    chunk_start_time: Optional[datetime] = None
    running_bytes = 0

    for line in lines:
        # Determine whether adding this line would breach a limit.
        if buf:  # only check limits when the buffer is non-empty
            over_lines = (
                options.max_lines is not None
                and len(buf) >= options.max_lines
            )
            over_bytes = (
                options.max_bytes is not None
                and running_bytes + len(line.raw.encode()) > options.max_bytes
            )
            over_seconds = False
            if options.max_seconds is not None and chunk_start_time is not None and line.timestamp is not None:
                elapsed = (line.timestamp - chunk_start_time).total_seconds()
                over_seconds = elapsed > options.max_seconds

            if over_lines or over_bytes or over_seconds:
                yield _flush(buf, chunk_idx)
                chunk_idx += 1
                chunk_start_time = None
                running_bytes = 0

        buf.append(line)
        running_bytes += len(line.raw.encode())
        if chunk_start_time is None and line.timestamp is not None:
            chunk_start_time = line.timestamp

    if buf:
        yield _flush(buf, chunk_idx)
