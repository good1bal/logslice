"""Tests for logslice.annotator — pattern-based line annotation."""

import re
from datetime import datetime, timezone

import pytest

from logslice.annotator import AnnotatorOptions, annotate_lines
from logslice.parser import ParsedLine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(year: int = 2024, month: int = 1, day: int = 1,
        hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _line(
    raw: str = "INFO  server started",
    severity: str = "INFO",
    timestamp: datetime | None = None,
    line_number: int = 1,
    annotations: dict | None = None,
) -> ParsedLine:
    return ParsedLine(
        raw=raw,
        severity=severity,
        timestamp=timestamp or _ts(),
        line_number=line_number,
        annotations=annotations or {},
    )


# ---------------------------------------------------------------------------
# AnnotatorOptions validation
# ---------------------------------------------------------------------------

class TestAnnotatorOptions:
    def test_defaults_are_sane(self):
        opts = AnnotatorOptions(patterns={})
        assert opts.patterns == {}
        assert opts.case_sensitive is False
        assert opts.overwrite is False

    def test_case_sensitive_flag_stored(self):
        opts = AnnotatorOptions(patterns={"k": "v"}, case_sensitive=True)
        assert opts.case_sensitive is True

    def test_overwrite_flag_stored(self):
        opts = AnnotatorOptions(patterns={}, overwrite=True)
        assert opts.overwrite is True

    def test_invalid_regex_raises(self):
        with pytest.raises(re.error):
            AnnotatorOptions(patterns={"bad": "[unclosed"})


# ---------------------------------------------------------------------------
# annotate_lines
# ---------------------------------------------------------------------------

class TestAnnotateLines:
    def test_no_patterns_passes_lines_unchanged(self):
        lines = [_line("INFO  hello"), _line("WARN  world", severity="WARN")]
        opts = AnnotatorOptions(patterns={})
        result = list(annotate_lines(lines, opts))
        assert len(result) == 2
        assert result[0].annotations == {}
        assert result[1].annotations == {}

    def test_matching_pattern_adds_annotation(self):
        line = _line("ERROR  connection refused")
        opts = AnnotatorOptions(patterns={"error_type": r"connection \w+"})
        result = list(annotate_lines([line], opts))
        assert result[0].annotations.get("error_type") == "connection refused"

    def test_non_matching_pattern_adds_no_annotation(self):
        line = _line("INFO  all good")
        opts = AnnotatorOptions(patterns={"error_type": r"connection \w+"})
        result = list(annotate_lines([line], opts))
        assert "error_type" not in result[0].annotations

    def test_case_insensitive_by_default(self):
        line = _line("INFO  TIMEOUT occurred")
        opts = AnnotatorOptions(patterns={"event": r"timeout"})
        result = list(annotate_lines([line], opts))
        assert result[0].annotations.get("event") == "TIMEOUT"

    def test_case_sensitive_no_match(self):
        line = _line("INFO  TIMEOUT occurred")
        opts = AnnotatorOptions(patterns={"event": r"timeout"}, case_sensitive=True)
        result = list(annotate_lines([line], opts))
        assert "event" not in result[0].annotations

    def test_case_sensitive_match(self):
        line = _line("INFO  timeout occurred")
        opts = AnnotatorOptions(patterns={"event": r"timeout"}, case_sensitive=True)
        result = list(annotate_lines([line], opts))
        assert result[0].annotations.get("event") == "timeout"

    def test_multiple_patterns_all_applied(self):
        line = _line("ERROR  disk full on /dev/sda")
        opts = AnnotatorOptions(patterns={
            "level": r"ERROR",
            "device": r"/dev/\S+",
        })
        result = list(annotate_lines([line], opts))
        ann = result[0].annotations
        assert ann.get("level") == "ERROR"
        assert ann.get("device") == "/dev/sda"

    def test_existing_annotation_not_overwritten_by_default(self):
        line = _line("INFO  hello", annotations={"tag": "original"})
        opts = AnnotatorOptions(patterns={"tag": r"hello"})
        result = list(annotate_lines([line], opts))
        assert result[0].annotations["tag"] == "original"

    def test_existing_annotation_overwritten_when_flag_set(self):
        line = _line("INFO  hello", annotations={"tag": "original"})
        opts = AnnotatorOptions(patterns={"tag": r"hello"}, overwrite=True)
        result = list(annotate_lines([line], opts))
        assert result[0].annotations["tag"] == "hello"

    def test_original_line_object_not_mutated(self):
        line = _line("INFO  hello")
        opts = AnnotatorOptions(patterns={"word": r"hello"})
        original_annotations = dict(line.annotations)
        list(annotate_lines([line], opts))
        assert line.annotations == original_annotations

    def test_returns_iterator(self):
        import types
        opts = AnnotatorOptions(patterns={})
        result = annotate_lines([], opts)
        assert isinstance(result, types.GeneratorType)

    def test_empty_input_yields_nothing(self):
        opts = AnnotatorOptions(patterns={"k": r"v"})
        assert list(annotate_lines([], opts)) == []
