"""Build and query a byte-offset index for a log file, backed by the cache layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from logslice.cache import load_cache, save_cache
from logslice.parser import parse_timestamp


def build_index(file_path: str, sample_every: int = 1) -> list[tuple[int, datetime]]:
    """Scan *file_path* and return a list of (byte_offset, timestamp) pairs.

    *sample_every* controls how many lines to skip between index entries;
    1 means every line is indexed (maximum precision, higher memory use).
    """
    index: list[tuple[int, datetime]] = []
    with open(file_path, "rb") as fh:
        offset = 0
        line_no = 0
        for raw in fh:
            if line_no % sample_every == 0:
                text = raw.decode(errors="replace").rstrip("\n")
                ts = parse_timestamp(text)
                if ts is not None:
                    index.append((offset, ts))
            offset += len(raw)
            line_no += 1
    return index


def build_index_cached(
    file_path: str, sample_every: int = 1
) -> list[tuple[int, datetime]]:
    """Like :func:`build_index` but transparently caches results on disk."""
    entry = load_cache(file_path)
    if entry is not None:
        return [(pair[0], datetime.fromisoformat(pair[1])) for pair in entry.index]

    index = build_index(file_path, sample_every=sample_every)
    serialisable = [[offset, ts.isoformat()] for offset, ts in index]
    save_cache(file_path, serialisable)
    return index


def find_start_offset(
    index: list[tuple[int, datetime]], start: datetime
) -> Optional[int]:
    """Binary-search *index* for the byte offset of the first entry >= *start*.

    Returns 0 if *start* is before the first indexed timestamp, or None if
    the index is empty.
    """
    if not index:
        return None
    lo, hi = 0, len(index) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if index[mid][1] < start:
            lo = mid + 1
        else:
            hi = mid
    # Step back one entry to avoid missing a line whose timestamp was not sampled
    result_idx = max(0, lo - 1)
    return index[result_idx][0]


def iter_from_offset(file_path: str, offset: int) -> Iterator[str]:
    """Yield text lines from *file_path* starting at *offset*."""
    with open(file_path, "rb") as fh:
        fh.seek(offset)
        for raw in fh:
            yield raw.decode(errors="replace").rstrip("\n")
