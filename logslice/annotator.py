"""annotator.py — Attach extra metadata fields to parsed log lines.

Annotations are arbitrary key/value pairs that can be added to each
``ParsedLine`` before formatting or export.  Typical use-cases:

* tagging lines with a source file name or host
* injecting a run-id so merged outputs stay traceable
* marking lines that matched a user-supplied regex
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

from logslice.parser import ParsedLine


@dataclass
class AnnotatorOptions:
    """Configuration for the :func:`annotate_lines` pipeline step.

    Attributes
    ----------
    tags:
        Static key/value pairs attached to every line (e.g.
        ``{"host": "web-01", "run_id": "abc123"}``).
    mark_pattern:
        Optional regex string.  Lines whose raw text matches the pattern
        receive an extra ``"marked": True`` annotation.
    mark_key:
        Name of the annotation key used for pattern matches.
        Defaults to ``"marked"``.
    case_sensitive:
        Whether *mark_pattern* matching is case-sensitive.
        Defaults to ``False``.
    """

    tags: dict[str, str] = field(default_factory=dict)
    mark_pattern: Optional[str] = None
    mark_key: str = "marked"
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        if not self.mark_key:
            raise ValueError("mark_key must be a non-empty string")


def _compile_pattern(opts: AnnotatorOptions) -> Optional[re.Pattern[str]]:
    """Return a compiled regex for *opts.mark_pattern*, or ``None``."""
    if not opts.mark_pattern:
        return None
    flags = 0 if opts.case_sensitive else re.IGNORECASE
    return re.compile(opts.mark_pattern, flags)


def _build_annotations(
    line: ParsedLine,
    opts: AnnotatorOptions,
    pattern: Optional[re.Pattern[str]],
) -> dict[str, object]:
    """Compute the annotation dict for a single *line*."""
    annotations: dict[str, object] = dict(opts.tags)
    if pattern is not None:
        annotations[opts.mark_key] = bool(pattern.search(line.raw))
    return annotations


def annotate_lines(
    lines: Iterable[ParsedLine],
    opts: Optional[AnnotatorOptions] = None,
) -> Iterator[ParsedLine]:
    """Yield *lines* with ``extra`` metadata merged from *opts*.

    Each :class:`~logslice.parser.ParsedLine` is yielded as-is but with
    its ``extra`` dict updated by the computed annotations.  The original
    ``extra`` values are preserved; annotation keys take precedence only
    when there is a collision.

    Parameters
    ----------
    lines:
        Source iterable of parsed log lines.
    opts:
        Annotation options.  Passing ``None`` (or omitting the argument)
        is a no-op — every line is yielded unchanged.

    Yields
    ------
    ParsedLine
        The same line objects with ``extra`` updated in-place.
    """
    if opts is None:
        yield from lines
        return

    pattern = _compile_pattern(opts)

    for line in lines:
        annotations = _build_annotations(line, opts, pattern)
        if annotations:
            # Merge: existing keys win; annotations fill in the rest.
            merged = {**annotations, **line.extra}
            # Allow annotations to *override* when the key is new.
            merged.update(
                {k: v for k, v in annotations.items() if k not in line.extra}
            )
            line.extra.update(merged)
        yield line
