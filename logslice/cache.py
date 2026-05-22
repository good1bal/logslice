"""Simple file-based index cache for speeding up repeated slices on the same log file."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


_CACHE_DIR = Path(os.environ.get("LOGSLICE_CACHE_DIR", Path.home() / ".cache" / "logslice"))


@dataclass
class CacheEntry:
    file_path: str
    file_mtime: float
    file_size: int
    # byte offset -> ISO timestamp string mapping (stored as list of [offset, ts] pairs)
    index: list[list]


def _cache_key(file_path: str) -> str:
    """Derive a stable cache filename from the log file path."""
    digest = hashlib.sha1(file_path.encode()).hexdigest()[:16]
    return f"{digest}.json"


def _is_stale(entry: CacheEntry, file_path: str) -> bool:
    """Return True if the cached metadata no longer matches the file on disk."""
    try:
        stat = os.stat(file_path)
        return stat.st_mtime != entry.file_mtime or stat.st_size != entry.file_size
    except OSError:
        return True


def load_cache(file_path: str) -> Optional[CacheEntry]:
    """Load a cache entry for *file_path*, returning None if missing or stale."""
    cache_file = _CACHE_DIR / _cache_key(file_path)
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text())
        entry = CacheEntry(**data)
    except Exception:
        return None
    if _is_stale(entry, file_path):
        return None
    return entry


def save_cache(file_path: str, index: list[list]) -> CacheEntry:
    """Persist an index for *file_path* and return the new CacheEntry."""
    stat = os.stat(file_path)
    entry = CacheEntry(
        file_path=file_path,
        file_mtime=stat.st_mtime,
        file_size=stat.st_size,
        index=index,
    )
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _CACHE_DIR / _cache_key(file_path)
    cache_file.write_text(json.dumps(asdict(entry)))
    return entry


def invalidate_cache(file_path: str) -> bool:
    """Remove the cache entry for *file_path*. Returns True if something was deleted."""
    cache_file = _CACHE_DIR / _cache_key(file_path)
    if cache_file.exists():
        cache_file.unlink()
        return True
    return False
