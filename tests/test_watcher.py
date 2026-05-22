"""Tests for logslice.watcher."""

from __future__ import annotations

import os
import threading
import time
import tempfile
from pathlib import Path

import pytest

from logslice.watcher import WatchOptions, watch_file
from logslice.filters import make_severity_filter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _append(path: str, text: str) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_watch_yields_new_lines(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("")  # create empty file

    opts = WatchOptions(poll_interval=0.05, max_idle=0.3)

    def _writer():
        time.sleep(0.05)
        _append(str(log), "2024-01-01T00:00:01 INFO hello\n")
        time.sleep(0.05)
        _append(str(log), "2024-01-01T00:00:02 DEBUG world\n")

    t = threading.Thread(target=_writer, daemon=True)
    t.start()

    lines = list(watch_file(str(log), opts))
    t.join()

    assert len(lines) == 2
    assert lines[0].raw == "2024-01-01T00:00:01 INFO hello"
    assert lines[1].raw == "2024-01-01T00:00:02 DEBUG world"


def test_watch_assigns_incremental_line_numbers(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("")

    opts = WatchOptions(poll_interval=0.05, max_idle=0.3)

    def _writer():
        time.sleep(0.05)
        for i in range(3):
            _append(str(log), f"2024-01-01T00:00:0{i} INFO msg{i}\n")

    t = threading.Thread(target=_writer, daemon=True)
    t.start()
    lines = list(watch_file(str(log), opts))
    t.join()

    assert [l.line_number for l in lines] == [1, 2, 3]


def test_watch_severity_filter(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("")

    filt = make_severity_filter(min_severity="WARN")
    opts = WatchOptions(poll_interval=0.05, max_idle=0.3, severity_filter=filt)

    def _writer():
        time.sleep(0.05)
        _append(str(log), "2024-01-01T00:00:01 DEBUG ignored\n")
        _append(str(log), "2024-01-01T00:00:02 WARN kept\n")
        _append(str(log), "2024-01-01T00:00:03 ERROR also kept\n")

    t = threading.Thread(target=_writer, daemon=True)
    t.start()
    lines = list(watch_file(str(log), opts))
    t.join()

    assert len(lines) == 2
    assert all(l.severity in ("WARN", "ERROR") for l in lines)


def test_watch_callback_invoked(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("")

    received = []
    opts = WatchOptions(
        poll_interval=0.05,
        max_idle=0.3,
        line_callback=received.append,
    )

    def _writer():
        time.sleep(0.05)
        _append(str(log), "2024-01-01T00:00:01 INFO cb test\n")

    t = threading.Thread(target=_writer, daemon=True)
    t.start()
    list(watch_file(str(log), opts))
    t.join()

    assert len(received) == 1
    assert received[0].raw == "2024-01-01T00:00:01 INFO cb test"


def test_watch_stops_on_max_idle(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("")

    opts = WatchOptions(poll_interval=0.05, max_idle=0.15)
    start = time.monotonic()
    lines = list(watch_file(str(log), opts))
    elapsed = time.monotonic() - start

    assert lines == []
    assert elapsed < 1.0  # should not hang
