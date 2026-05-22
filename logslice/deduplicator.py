"""Deduplicator: remove or count consecutive duplicate log lines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import ParsedLine


@dataclass
class DeduplicatorOptions:
    """Options controlling deduplication behaviour."""

    enabled: bool = True
    # If True, emit a summary line showing how many duplicates were suppressed.
    annotate: bool = True
    # Maximum number of identical consecutive lines to suppress (0 = unlimited).
    max_suppress: int = 0


@dataclass
class _State:
    last_text: str | None = None
    count: int = 0
    last_line: ParsedLine | None = None


def _annotation(line: ParsedLine, count: int) -> ParsedLine:
    """Return a synthetic ParsedLine noting that *count* duplicates were skipped."""
    note = f"[logslice: {count} duplicate line(s) suppressed]"
    return ParsedLine(
        raw=note,
        timestamp=line.timestamp,
        severity=line.severity,
        message=note,
        line_number=line.line_number,
    )


def deduplicate(
    lines: Iterable[ParsedLine],
    options: DeduplicatorOptions | None = None,
) -> Iterator[ParsedLine]:
    """Yield lines with consecutive duplicates removed.

    When *options.annotate* is True a synthetic note line is emitted after a
    run of duplicates so the reader knows lines were suppressed.
    """
    if options is None:
        options = DeduplicatorOptions()

    if not options.enabled:
        yield from lines
        return

    state = _State()

    for line in lines:
        text = line.raw

        if text == state.last_text:
            suppress_limit = options.max_suppress
            if suppress_limit == 0 or state.count < suppress_limit:
                state.count += 1
                state.last_line = line
                continue
            # Limit reached — fall through and emit the line normally.

        # Flush pending duplicate annotation before emitting the new line.
        if state.count > 0 and options.annotate and state.last_line is not None:
            yield _annotation(state.last_line, state.count)

        state.last_text = text
        state.count = 0
        state.last_line = line
        yield line

    # Flush any trailing duplicates.
    if state.count > 0 and options.annotate and state.last_line is not None:
        yield _annotation(state.last_line, state.count)
