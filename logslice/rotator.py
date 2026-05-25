"""Log rotation detector — identifies rotated/rolled log files for a given base path."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class RotatorOptions:
    """Options controlling how rotated log files are discovered."""

    base_path: Path
    max_rotations: int = 10
    include_compressed: bool = True
    sort_newest_first: bool = True

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_path)
        if self.max_rotations < 0:
            raise ValueError("max_rotations must be >= 0")


@dataclass
class RotatedFile:
    """Represents a single rotated (or current) log file."""

    path: Path
    index: Optional[int]  # None for the current/base file
    compressed: bool
    size_bytes: int


# Patterns that match common rotation suffixes, e.g. .1, .2.gz, .2024-01-15
_NUMERIC_SUFFIX = re.compile(r"\.(\d+)(\.gz|\.bz2|\.xz)?$")
_DATE_SUFFIX = re.compile(r"\.(\d{4}-\d{2}-\d{2})(\.gz|\.bz2|\.xz)?$")
_COMPRESSED_EXT = {".gz", ".bz2", ".xz"}


def _rotation_index(stem: str, base_name: str) -> Optional[int]:
    """Return a sortable integer index for a rotated filename, or None."""
    suffix = stem[len(base_name):]
    m = _NUMERIC_SUFFIX.match(suffix)
    if m:
        return int(m.group(1))
    m = _DATE_SUFFIX.match(suffix)
    if m:
        # Convert date string to an integer YYYYMMDD for ordering
        return int(m.group(1).replace("-", ""))
    return None


def find_rotated_files(opts: RotatorOptions) -> List[RotatedFile]:
    """Discover rotated log files adjacent to *opts.base_path*.

    Returns the base file (index=None) plus up to *max_rotations* rotated
    copies, ordered by rotation index.
    """
    base = opts.base_path
    parent = base.parent
    base_name = base.name
    results: List[RotatedFile] = []

    if base.exists():
        results.append(
            RotatedFile(
                path=base,
                index=None,
                compressed=False,
                size_bytes=base.stat().st_size,
            )
        )

    for entry in parent.iterdir():
        name = entry.name
        if name == base_name or not name.startswith(base_name):
            continue
        compressed = any(name.endswith(ext) for ext in _COMPRESSED_EXT)
        if compressed and not opts.include_compressed:
            continue
        idx = _rotation_index(name, base_name)
        if idx is None:
            continue
        results.append(
            RotatedFile(
                path=entry,
                index=idx,
                compressed=compressed,
                size_bytes=entry.stat().st_size,
            )
        )

    # Sort: base file first (index=None), then by numeric index ascending
    rotated = sorted(
        (r for r in results if r.index is not None), key=lambda r: r.index  # type: ignore[arg-type]
    )
    base_files = [r for r in results if r.index is None]

    ordered = base_files + rotated[: opts.max_rotations]
    if opts.sort_newest_first:
        ordered = list(reversed(ordered))
    return ordered
