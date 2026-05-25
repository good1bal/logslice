"""logslice.redactor — Redact sensitive patterns from log lines before output.

Supports named rules (e.g. 'email', 'ip', 'token') as well as arbitrary
regex patterns supplied by the caller.  Each match is replaced with a
configurable placeholder string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional, Pattern, Tuple

from logslice.parser import ParsedLine

# ---------------------------------------------------------------------------
# Built-in pattern library
# ---------------------------------------------------------------------------

_BUILTIN_PATTERNS: dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "ipv6": r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b",
    "uuid": r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
    "jwt": r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
    "credit_card": r"\b(?:\d[ \-]?){13,16}\b",
    "phone": r"\b(?:\+?\d[\s.\-]?){7,15}\b",
    "url_password": r"(?<=://)([^:]+):([^@]+)(?=@)",
}


def builtin_names() -> List[str]:
    """Return the names of all available built-in redaction rules."""
    return list(_BUILTIN_PATTERNS.keys())


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class RedactorOptions:
    """Options controlling which patterns are redacted and how.

    Attributes:
        builtins:    Names of built-in rules to enable (see ``builtin_names()``).
        patterns:    Additional raw regex strings to redact.
        placeholder: Replacement text for every redacted span.
        case_sensitive: Whether custom *patterns* are case-sensitive.
                        Built-in patterns are always case-insensitive.
    """

    builtins: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    placeholder: str = "[REDACTED]"
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        unknown = set(self.builtins) - set(_BUILTIN_PATTERNS)
        if unknown:
            raise ValueError(f"Unknown built-in redaction rules: {sorted(unknown)}")


# ---------------------------------------------------------------------------
# Core redactor
# ---------------------------------------------------------------------------


class Redactor:
    """Applies a collection of redaction rules to text strings."""

    def __init__(self, options: RedactorOptions) -> None:
        self._placeholder = options.placeholder
        self._rules: List[Tuple[Pattern[str], str]] = []

        # Compile built-in patterns (always case-insensitive)
        for name in options.builtins:
            raw = _BUILTIN_PATTERNS[name]
            self._rules.append((re.compile(raw, re.IGNORECASE), options.placeholder))

        # Compile caller-supplied patterns
        flags = 0 if options.case_sensitive else re.IGNORECASE
        for raw in options.patterns:
            self._rules.append((re.compile(raw, flags), options.placeholder))

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def redact_text(self, text: str) -> str:
        """Return *text* with all matching spans replaced by the placeholder."""
        for pattern, replacement in self._rules:
            text = pattern.sub(replacement, text)
        return text

    def redact_line(self, line: ParsedLine) -> ParsedLine:
        """Return a new :class:`~logslice.parser.ParsedLine` with redacted raw text."""
        redacted_raw = self.redact_text(line.raw)
        return ParsedLine(
            raw=redacted_raw,
            timestamp=line.timestamp,
            severity=line.severity,
            message=self.redact_text(line.message) if line.message is not None else None,
            line_number=line.line_number,
        )


# ---------------------------------------------------------------------------
# Convenience generator
# ---------------------------------------------------------------------------


def redact_lines(
    lines: Iterable[ParsedLine],
    options: Optional[RedactorOptions] = None,
) -> Iterator[ParsedLine]:
    """Yield redacted versions of *lines* according to *options*.

    If *options* is ``None`` or defines no rules the lines pass through
    unchanged, making it safe to call unconditionally in a pipeline.
    """
    if options is None or (not options.builtins and not options.patterns):
        yield from lines
        return

    redactor = Redactor(options)
    for line in lines:
        yield redactor.redact_line(line)
