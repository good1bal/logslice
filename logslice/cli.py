"""Command-line interface for logslice."""

import argparse
import sys
from datetime import datetime
from typing import Optional

from logslice.slicer import slice_log
from logslice.formatter import FormatOptions, format_lines

DATE_FORMATS = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]


def _parse_dt(value: str) -> datetime:
    """Try multiple date formats and return a datetime."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Cannot parse datetime '{value}'. "
        "Expected formats: YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD HH:MM:SS, or YYYY-MM-DD"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logslice",
        description="Slice log files by time range and severity.",
    )
    p.add_argument("file", help="Path to log file (use '-' for stdin)")
    p.add_argument("--start", type=_parse_dt, metavar="DATETIME", help="Start of time range (inclusive)")
    p.add_argument("--end", type=_parse_dt, metavar="DATETIME", help="End of time range (inclusive)")
    p.add_argument(
        "--severity",
        nargs="+",
        metavar="LEVEL",
        help="One or more severity levels to include (e.g. ERROR WARN)",
    )
    p.add_argument("--line-numbers", action="store_true", help="Prefix output with line numbers")
    p.add_argument("--color", action="store_true", help="Colorize output by severity")
    p.add_argument(
        "--format",
        dest="output_format",
        choices=["plain", "json", "csv"],
        default="plain",
        help="Output format (default: plain)",
    )
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.file == "-":
        source = sys.stdin
    else:
        try:
            source = open(args.file, "r", encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"logslice: error opening file: {exc}", file=sys.stderr)
            return 1

    try:
        matched_lines = slice_log(
            source,
            start=args.start,
            end=args.end,
            severities=args.severity,
        )
    finally:
        if args.file != "-":
            source.close()

    opts = FormatOptions(
        show_line_numbers=args.line_numbers,
        colorize=args.color,
        output_format=args.output_format,
    )
    formatted = format_lines(matched_lines, opts)
    for line in formatted:
        print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
