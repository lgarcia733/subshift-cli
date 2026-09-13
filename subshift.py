#!/usr/bin/env python3
"""Shift and rescale timestamps in SRT subtitle files."""

import argparse
import re
import sys
from pathlib import Path

TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
ARROW_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})"
)


class Cue:
    __slots__ = ("start", "end", "text")

    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


def parse_time(text):
    match = TIME_RE.match(text)
    if not match:
        raise ValueError(f"not a valid SRT timestamp: {text!r}")
    hours, minutes, seconds, millis = (int(g) for g in match.groups())
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def format_time(ms):
    if ms < 0:
        ms = 0
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    seconds, millis = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def parse_srt(content):
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", content.strip())
    cues = []
    for block in blocks:
        lines = block.strip("\n").split("\n")
        if len(lines) < 2:
            continue
        # Real files sometimes drop the cue number or have stray blank
        # lines inside a block, so find the arrow line instead of
        # assuming it's always the second line.
        arrow_index = None
        for i, line in enumerate(lines):
            if ARROW_RE.search(line):
                arrow_index = i
                break
        if arrow_index is None:
            continue
        arrow_match = ARROW_RE.search(lines[arrow_index])
        start = parse_time(arrow_match.group(1))
        end = parse_time(arrow_match.group(2))
        text = "\n".join(lines[arrow_index + 1:])
        cues.append(Cue(start, end, text))
    return cues


def render_srt(cues):
    parts = []
    for i, cue in enumerate(cues, start=1):
        parts.append(
            f"{i}\n{format_time(cue.start)} --> {format_time(cue.end)}\n"
            f"{cue.text}\n"
        )
    return "\n".join(parts) + "\n"


def transform(cues, scale, shift_ms):
    for cue in cues:
        cue.start = round(cue.start * scale) + shift_ms
        cue.end = round(cue.end * scale) + shift_ms
    return cues


def parse_factor(text):
    """Accept either a plain float or a "a/b" fraction like "25/23.976"."""
    if "/" in text:
        num, den = text.split("/", 1)
        return float(num) / float(den)
    return float(text)


def default_output_path(input_path):
    p = Path(input_path)
    return p.with_suffix(f".shifted{p.suffix or '.srt'}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="subshift",
        description="Shift or rescale the timestamps in an SRT subtitle file.",
    )
    parser.add_argument("input", help="path to the .srt file to read")
    parser.add_argument(
        "-o", "--output",
        help="where to write the result; use - for stdout "
             "(default: <input>.shifted.srt)",
    )
    parser.add_argument(
        "--shift", type=int, default=0, metavar="MS",
        help="milliseconds to add to every timestamp; negative moves "
             "subtitles earlier",
    )
    parser.add_argument(
        "--scale", type=parse_factor, default=1.0, metavar="FACTOR",
        help="multiply every timestamp by FACTOR before shifting; use "
             "this to fix subtitles timed for a different frame rate, "
             "e.g. --scale 25/23.976",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        raw = Path(args.input).read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"subshift: {exc}", file=sys.stderr)
        return 1

    cues = parse_srt(raw)
    if not cues:
        print(f"subshift: no subtitle cues found in {args.input}", file=sys.stderr)
        return 1

    transform(cues, args.scale, args.shift)
    output_text = render_srt(cues)

    if args.output == "-":
        sys.stdout.write(output_text)
        return 0

    output_path = args.output or default_output_path(args.input)
    Path(output_path).write_text(output_text, encoding="utf-8")
    print(f"wrote {len(cues)} cues to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
