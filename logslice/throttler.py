"""Rate-limiting / throttling for log line streams.

Allows callers to cap the number of lines emitted per second, which is
useful when piping live output to slow consumers or terminals.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import ParsedLine


@dataclass
class ThrottlerOptions:
    """Configuration for the line-rate throttler."""

    lines_per_second: float = 0.0  # 0 means unlimited
    burst: int = 1  # max lines that may be emitted instantly

    def __post_init__(self) -> None:
        if self.lines_per_second < 0:
            raise ValueError("lines_per_second must be >= 0")
        if self.burst < 1:
            raise ValueError("burst must be >= 1")


@dataclass
class _TokenBucket:
    """Simple token-bucket implementation for rate limiting."""

    rate: float          # tokens added per second
    capacity: int        # maximum tokens
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last = time.monotonic()

    def consume(self) -> None:
        """Block until a token is available, then consume one."""
        while True:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            deficit = (1.0 - self._tokens) / self.rate
            time.sleep(deficit)


def throttle_lines(
    source: Iterable[ParsedLine],
    options: ThrottlerOptions | None = None,
) -> Iterator[ParsedLine]:
    """Yield lines from *source*, sleeping as needed to honour the rate limit.

    When ``options.lines_per_second`` is 0 (the default) lines are yielded
    immediately without any delay.
    """
    opts = options or ThrottlerOptions()

    if opts.lines_per_second <= 0:
        yield from source
        return

    bucket = _TokenBucket(rate=opts.lines_per_second, capacity=opts.burst)
    for line in source:
        bucket.consume()
        yield line
