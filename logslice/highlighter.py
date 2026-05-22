"""Keyword highlighting for log output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# ANSI colour codes
_RESET = "\033[0m"
_COLOURS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
}


@dataclass
class HighlightRule:
    """A single keyword/pattern highlight rule."""

    pattern: str
    colour: str = "yellow"
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        if self.colour not in _COLOURS:
            raise ValueError(
                f"Unknown colour {self.colour!r}. Choose from: {sorted(_COLOURS)}"
            )
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._regex: re.Pattern[str] = re.compile(self.pattern, flags)

    def apply(self, text: str) -> str:
        """Return *text* with all matches wrapped in the chosen ANSI colour."""
        colour_code = _COLOURS[self.colour]

        def _replace(m: re.Match) -> str:  # type: ignore[type-arg]
            return f"{colour_code}{m.group(0)}{_RESET}"

        return self._regex.sub(_replace, text)


@dataclass
class Highlighter:
    """Applies an ordered list of :class:`HighlightRule` objects to text."""

    rules: List[HighlightRule] = field(default_factory=list)
    enabled: bool = True

    def add_rule(self, pattern: str, colour: str = "yellow", case_sensitive: bool = False) -> None:
        """Convenience method to append a new rule."""
        self.rules.append(HighlightRule(pattern=pattern, colour=colour, case_sensitive=case_sensitive))

    def highlight(self, text: str) -> str:
        """Apply all rules in order and return the highlighted string."""
        if not self.enabled or not self.rules:
            return text
        for rule in self.rules:
            text = rule.apply(text)
        return text


def make_highlighter(
    keywords: Optional[List[str]] = None,
    colour: str = "yellow",
    enabled: bool = True,
) -> Highlighter:
    """Build a :class:`Highlighter` from a list of plain keyword strings."""
    h = Highlighter(enabled=enabled)
    for kw in (keywords or []):
        h.add_rule(re.escape(kw), colour=colour)
    return h
