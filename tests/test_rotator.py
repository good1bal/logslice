"""Tests for logslice.rotator."""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from logslice.rotator import RotatedFile, RotatorOptions, find_rotated_files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str = "log line\n") -> Path:
    path.write_text(content)
    return path


def _write_gz(path: Path, content: str = "log line\n") -> Path:
    with gzip.open(path, "wt") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# RotatorOptions validation
# ---------------------------------------------------------------------------

class TestRotatorOptions:
    def test_defaults_are_sane(self, tmp_path: Path) -> None:
        opts = RotatorOptions(base_path=tmp_path / "app.log")
        assert opts.max_rotations == 10
        assert opts.include_compressed is True
        assert opts.sort_newest_first is True

    def test_base_path_coerced_to_path(self, tmp_path: Path) -> None:
        opts = RotatorOptions(base_path=str(tmp_path / "app.log"))  # type: ignore[arg-type]
        assert isinstance(opts.base_path, Path)

    def test_negative_max_rotations_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="max_rotations"):
            RotatorOptions(base_path=tmp_path / "app.log", max_rotations=-1)


# ---------------------------------------------------------------------------
# find_rotated_files
# ---------------------------------------------------------------------------

def test_no_files_returns_empty(tmp_path: Path) -> None:
    opts = RotatorOptions(base_path=tmp_path / "app.log")
    assert find_rotated_files(opts) == []


def test_base_file_only(tmp_path: Path) -> None:
    log = _write(tmp_path / "app.log")
    opts = RotatorOptions(base_path=log)
    result = find_rotated_files(opts)
    assert len(result) == 1
    assert result[0].index is None
    assert result[0].compressed is False


def test_numeric_rotations_discovered(tmp_path: Path) -> None:
    _write(tmp_path / "app.log")
    _write(tmp_path / "app.log.1")
    _write(tmp_path / "app.log.2")
    opts = RotatorOptions(base_path=tmp_path / "app.log", sort_newest_first=False)
    result = find_rotated_files(opts)
    assert len(result) == 3
    indices = [r.index for r in result]
    assert indices == [None, 1, 2]


def test_compressed_files_included(tmp_path: Path) -> None:
    _write(tmp_path / "app.log")
    _write_gz(tmp_path / "app.log.1.gz")
    opts = RotatorOptions(base_path=tmp_path / "app.log", sort_newest_first=False)
    result = find_rotated_files(opts)
    compressed = [r for r in result if r.compressed]
    assert len(compressed) == 1
    assert compressed[0].index == 1


def test_compressed_files_excluded(tmp_path: Path) -> None:
    _write(tmp_path / "app.log")
    _write_gz(tmp_path / "app.log.1.gz")
    opts = RotatorOptions(
        base_path=tmp_path / "app.log",
        include_compressed=False,
        sort_newest_first=False,
    )
    result = find_rotated_files(opts)
    assert all(not r.compressed for r in result)


def test_max_rotations_limits_results(tmp_path: Path) -> None:
    _write(tmp_path / "app.log")
    for i in range(1, 6):
        _write(tmp_path / f"app.log.{i}")
    opts = RotatorOptions(base_path=tmp_path / "app.log", max_rotations=2, sort_newest_first=False)
    result = find_rotated_files(opts)
    rotated = [r for r in result if r.index is not None]
    assert len(rotated) == 2


def test_sort_newest_first_reverses_order(tmp_path: Path) -> None:
    _write(tmp_path / "app.log")
    _write(tmp_path / "app.log.1")
    _write(tmp_path / "app.log.2")
    opts = RotatorOptions(base_path=tmp_path / "app.log", sort_newest_first=True)
    result = find_rotated_files(opts)
    # With newest-first the base file (index=None) should appear last
    assert result[-1].index is None


def test_size_bytes_populated(tmp_path: Path) -> None:
    log = _write(tmp_path / "app.log", "hello\n")
    opts = RotatorOptions(base_path=log)
    result = find_rotated_files(opts)
    assert result[0].size_bytes == log.stat().st_size
