"""Tests for logslice.throttler."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from logslice.parser import ParsedLine
from logslice.throttler import ThrottlerOptions, _TokenBucket, throttle_lines


_NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _line(n: int = 1) -> ParsedLine:
    return ParsedLine(
        raw=f"line {n}",
        timestamp=_NOW,
        severity="INFO",
        message=f"message {n}",
        line_number=n,
    )


# ---------------------------------------------------------------------------
# ThrottlerOptions validation
# ---------------------------------------------------------------------------

class TestThrottlerOptions:
    def test_defaults_are_sane(self):
        opts = ThrottlerOptions()
        assert opts.lines_per_second == 0.0
        assert opts.burst == 1

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="lines_per_second"):
            ThrottlerOptions(lines_per_second=-1.0)

    def test_zero_burst_raises(self):
        with pytest.raises(ValueError, match="burst"):
            ThrottlerOptions(burst=0)

    def test_valid_custom_values(self):
        opts = ThrottlerOptions(lines_per_second=100.0, burst=5)
        assert opts.lines_per_second == 100.0
        assert opts.burst == 5


# ---------------------------------------------------------------------------
# throttle_lines — unlimited path
# ---------------------------------------------------------------------------

def test_unlimited_yields_all_lines():
    lines = [_line(i) for i in range(5)]
    result = list(throttle_lines(lines, ThrottlerOptions(lines_per_second=0)))
    assert result == lines


def test_unlimited_no_sleep_called():
    lines = [_line(i) for i in range(3)]
    with patch("time.sleep") as mock_sleep:
        list(throttle_lines(lines, ThrottlerOptions(lines_per_second=0)))
    mock_sleep.assert_not_called()


def test_none_options_defaults_to_unlimited():
    lines = [_line(i) for i in range(3)]
    result = list(throttle_lines(lines, None))
    assert len(result) == 3


# ---------------------------------------------------------------------------
# throttle_lines — rate-limited path
# ---------------------------------------------------------------------------

def test_rate_limited_yields_all_lines():
    """Every line must still be emitted even under rate limiting."""
    lines = [_line(i) for i in range(4)]
    # Use a very high rate so the test doesn't actually sleep.
    opts = ThrottlerOptions(lines_per_second=1_000_000, burst=4)
    result = list(throttle_lines(lines, opts))
    assert result == lines


def test_rate_limited_order_preserved():
    lines = [_line(i) for i in range(6)]
    opts = ThrottlerOptions(lines_per_second=1_000_000, burst=6)
    result = list(throttle_lines(lines, opts))
    assert [l.line_number for l in result] == list(range(6))


# ---------------------------------------------------------------------------
# _TokenBucket internals
# ---------------------------------------------------------------------------

def test_token_bucket_does_not_sleep_when_tokens_available():
    bucket = _TokenBucket(rate=10.0, capacity=5)
    # Pre-fill bucket
    bucket._tokens = 5.0
    start = time.monotonic()
    bucket.consume()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1  # should be essentially instant


def test_token_bucket_caps_at_capacity():
    bucket = _TokenBucket(rate=1.0, capacity=3)
    # Simulate a long gap — tokens should not exceed capacity
    bucket._last = time.monotonic() - 1000
    bucket.consume()  # triggers refill + consume
    assert bucket._tokens <= bucket.capacity
