"""Log line sampler: keep every N-th matched line or a random fraction."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import ParsedLine


@dataclass
class SamplerOptions:
    """Controls how lines are sampled from the matched set."""

    # Keep every *nth* line (1 = keep all, 2 = every other, etc.).
    every_nth: int = 1
    # If set, keep each line with this probability (0.0–1.0).
    # Takes precedence over *every_nth* when not None.
    random_fraction: float | None = None
    # Seed for the random number generator (for reproducible output).
    seed: int | None = None
    # Private RNG instance – populated in __post_init__.
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.every_nth < 1:
            raise ValueError("every_nth must be >= 1")
        if self.random_fraction is not None and not (0.0 <= self.random_fraction <= 1.0):
            raise ValueError("random_fraction must be between 0.0 and 1.0")
        self._rng = random.Random(self.seed)


def sample_lines(
    lines: Iterable[ParsedLine],
    options: SamplerOptions | None = None,
) -> Iterator[ParsedLine]:
    """Yield a subset of *lines* according to *options*.

    Parameters
    ----------
    lines:
        Source iterable of already-filtered :class:`~logslice.parser.ParsedLine`
        objects.
    options:
        Sampling configuration.  ``None`` (or ``SamplerOptions()`` defaults)
        passes every line through unchanged.
    """
    if options is None:
        yield from lines
        return

    if options.random_fraction is not None:
        frac = options.random_fraction
        rng = options._rng
        for line in lines:
            if rng.random() < frac:
                yield line
        return

    nth = options.every_nth
    if nth == 1:
        yield from lines
        return

    for index, line in enumerate(lines):
        if index % nth == 0:
            yield line
