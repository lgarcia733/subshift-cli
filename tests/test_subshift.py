"""Unit tests for the timestamp and SRT parsing helpers."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from subshift import format_time, parse_srt, parse_time, render_srt, transform


class ParseTimeTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(parse_time("00:00:00,000"), 0)

    def test_full_components(self):
        # 1h 2m 3s 4ms
        self.assertEqual(parse_time("01:02:03,004"), 3_723_004)

    def test_rejects_missing_millis(self):
        with self.assertRaises(ValueError):
            parse_time("00:00:00")

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            parse_time("not a timestamp")

    def test_matches_prefix_only(self):
        # parse_time uses match(), not fullmatch(), so trailing
        # junk after a valid timestamp is ignored rather than rejected.
        self.assertEqual(parse_time("00:00:01,000 --> whatever"), 1000)


class FormatTimeTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(format_time(0), "00:00:00,000")

    def test_negative_clamps_to_zero(self):
        self.assertEqual(format_time(-5000), "00:00:00,000")

    def test_millisecond_boundary(self):
        self.assertEqual(format_time(3_661_001), "01:01:01,001")

    def test_hours_over_99_are_not_truncated(self):
        # 100 hours in ms; the field isn't clamped to two digits,
        # it just grows past them.
        hundred_hours_ms = 100 * 3_600_000
        self.assertEqual(format_time(hundred_hours_ms), "100:00:00,000")

    def test_round_trip_with_parse_time(self):
        ms = 12_345_678
        self.assertEqual(parse_time(format_time(ms)), ms)


class ParseSrtTests(unittest.TestCase):
    def test_empty_content_yields_no_cues(self):
        self.assertEqual(parse_srt(""), [])

    def test_single_cue(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Hello there\n"
        )
        cues = parse_srt(content)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].start, 1000)
        self.assertEqual(cues[0].end, 2000)
        self.assertEqual(cues[0].text, "Hello there")

    def test_multiline_text_is_preserved(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "line one\n"
            "line two\n"
        )
        cues = parse_srt(content)
        self.assertEqual(cues[0].text, "line one\nline two")

    def test_missing_cue_number_is_tolerated(self):
        # arrow line is found by scanning rather than assuming a
        # fixed position, so a dropped index line still parses.
        content = "00:00:01,000 --> 00:00:02,000\nHello\n"
        cues = parse_srt(content)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "Hello")

    def test_block_without_arrow_line_is_skipped(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Hello\n"
            "\n"
            "2\n"
            "just some stray text\n"
            "with no timestamp\n"
        )
        cues = parse_srt(content)
        self.assertEqual(len(cues), 1)

    def test_windows_line_endings(self):
        content = (
            "1\r\n"
            "00:00:01,000 --> 00:00:02,000\r\n"
            "Hello\r\n"
        )
        cues = parse_srt(content)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "Hello")

    def test_extra_blank_lines_between_blocks(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "First\n"
            "\n"
            "\n"
            "\n"
            "2\n"
            "00:00:03,000 --> 00:00:04,000\n"
            "Second\n"
        )
        cues = parse_srt(content)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1].text, "Second")

    def test_render_srt_renumbers_sequentially(self):
        content = (
            "5\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "First\n"
            "\n"
            "9\n"
            "00:00:03,000 --> 00:00:04,000\n"
            "Second\n"
        )
        cues = parse_srt(content)
        rendered = render_srt(cues)
        self.assertTrue(rendered.startswith("1\n"))
        self.assertIn("\n2\n", rendered)


class TransformTests(unittest.TestCase):
    def test_shift_only(self):
        cues = parse_srt(
            "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
        )
        transform(cues, scale=1.0, shift_ms=500)
        self.assertEqual(cues[0].start, 1500)
        self.assertEqual(cues[0].end, 2500)

    def test_shift_clamped_at_render_time(self):
        cues = parse_srt(
            "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
        )
        transform(cues, scale=1.0, shift_ms=-5000)
        self.assertEqual(cues[0].start, -4000)
        rendered = render_srt(cues)
        self.assertIn("00:00:00,000 --> 00:00:00,000", rendered)

    def test_scale_applied_before_shift(self):
        cues = parse_srt(
            "1\n00:00:10,000 --> 00:00:20,000\nHello\n"
        )
        transform(cues, scale=2.0, shift_ms=100)
        self.assertEqual(cues[0].start, 20_100)
        self.assertEqual(cues[0].end, 40_100)


if __name__ == "__main__":
    unittest.main()
