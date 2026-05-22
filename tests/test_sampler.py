"""Tests for logslice.sampler."""

from __future__ import annotations

import pytest

from logslice.parser import ParsedLine
from logslice.sampler import SamplerOptions, sample_lines


def _line(n: int) -> ParsedLine:
    return ParsedLine(
        raw=f"line {n}",
        timestamp=None,
        severity=None,
        message=f"line {n}",
        line_number=n,
    )


LINES = [_line(i) for i in range(10)]


# ---------------------------------------------------------------------------
# SamplerOptions validation
# ---------------------------------------------------------------------------

def test_every_nth_below_one_raises():
    with pytest.raises(ValueError, match="every_nth"):
        SamplerOptions(every_nth=0)


def test_random_fraction_out_of_range_raises():
    with pytest.raises(ValueError, match="random_fraction"):
        SamplerOptions(random_fraction=1.5)


def test_random_fraction_negative_raises():
    with pytest.raises(ValueError, match="random_fraction"):
        SamplerOptions(random_fraction=-0.1)


# ---------------------------------------------------------------------------
# every_nth sampling
# ---------------------------------------------------------------------------

def test_every_nth_one_passes_all():
    opts = SamplerOptions(every_nth=1)
    result = list(sample_lines(LINES, opts))
    assert result == LINES


def test_every_nth_two_halves_output():
    opts = SamplerOptions(every_nth=2)
    result = list(sample_lines(LINES, opts))
    assert result == LINES[::2]


def test_every_nth_three():
    opts = SamplerOptions(every_nth=3)
    result = list(sample_lines(LINES, opts))
    assert [ln.line_number for ln in result] == [0, 3, 6, 9]


def test_every_nth_larger_than_input():
    opts = SamplerOptions(every_nth=20)
    result = list(sample_lines(LINES, opts))
    assert len(result) == 1
    assert result[0].line_number == 0


# ---------------------------------------------------------------------------
# random_fraction sampling
# ---------------------------------------------------------------------------

def test_random_fraction_zero_drops_all():
    opts = SamplerOptions(random_fraction=0.0, seed=42)
    result = list(sample_lines(LINES, opts))
    assert result == []


def test_random_fraction_one_keeps_all():
    opts = SamplerOptions(random_fraction=1.0, seed=42)
    result = list(sample_lines(LINES, opts))
    assert result == LINES


def test_random_fraction_reproducible_with_seed():
    opts_a = SamplerOptions(random_fraction=0.5, seed=7)
    opts_b = SamplerOptions(random_fraction=0.5, seed=7)
    assert list(sample_lines(LINES, opts_a)) == list(sample_lines(LINES, opts_b))


def test_random_fraction_different_seeds_differ():
    opts_a = SamplerOptions(random_fraction=0.5, seed=1)
    opts_b = SamplerOptions(random_fraction=0.5, seed=999)
    # With 10 lines it is astronomically unlikely both seeds give identical results.
    assert list(sample_lines(LINES, opts_a)) != list(sample_lines(LINES, opts_b))


# ---------------------------------------------------------------------------
# None options passthrough
# ---------------------------------------------------------------------------

def test_none_options_passes_all():
    result = list(sample_lines(LINES, None))
    assert result == LINES


def test_empty_input_returns_empty():
    opts = SamplerOptions(every_nth=2)
    assert list(sample_lines([], opts)) == []
