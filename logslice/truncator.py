"""Line truncation utilities for logslice output."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import ParsedLine

_ELLIPSIS = "..."
_MIN_WIDTH = len(_ELLIPSIS) + 1


@dataclass
class TruncatorOptions:
    """Options controlling how lines are truncated."""

    max_width: int = 0  # 0 means no truncation
    ellipsis: str = _ELLIPSIS
    truncate_message_only: bool = True  # when True, only shorten the message part

    def __post_init__(self) -> None:
        if self.max_width != 0 and self.max_width < _MIN_WIDTH:
            raise ValueError(
                f"max_width must be 0 (disabled) or at least {_MIN_WIDTH}, "
                f"got {self.max_width}"
            )


def _truncate_str(text: str, max_width: int, ellipsis: str) -> str:
    """Return *text* truncated to *max_width* characters, appending *ellipsis*."""
    if len(text) <= max_width:
        return text
    return text[: max_width - len(ellipsis)] + ellipsis


def truncate_line(line: ParsedLine, opts: TruncatorOptions) -> ParsedLine:
    """Return a (possibly new) ParsedLine whose raw text respects *opts.max_width*.

    When *opts.truncate_message_only* is True the prefix (timestamp + severity)
    is preserved and only the trailing message portion is shortened.  When False
    the entire raw string is truncated.
    """
    if opts.max_width == 0 or len(line.raw) <= opts.max_width:
        return line

    if opts.truncate_message_only and line.message:
        # Compute the prefix that precedes the message in the raw string.
        prefix_end = line.raw.find(line.message)
        if prefix_end != -1:
            prefix = line.raw[:prefix_end]
            budget = opts.max_width - len(prefix)
            if budget >= _MIN_WIDTH:
                truncated_msg = _truncate_str(line.message, budget, opts.ellipsis)
                new_raw = prefix + truncated_msg
                return ParsedLine(
                    raw=new_raw,
                    timestamp=line.timestamp,
                    severity=line.severity,
                    message=truncated_msg,
                    line_number=line.line_number,
                )

    # Fallback: truncate the whole raw string.
    new_raw = _truncate_str(line.raw, opts.max_width, opts.ellipsis)
    return ParsedLine(
        raw=new_raw,
        timestamp=line.timestamp,
        severity=line.severity,
        message=line.message,
        line_number=line.line_number,
    )


def truncate_lines(
    lines: Iterable[ParsedLine], opts: TruncatorOptions
) -> Iterator[ParsedLine]:
    """Yield each line from *lines* after applying :func:`truncate_line`."""
    for line in lines:
        yield truncate_line(line, opts)
