# subshift

A subtitle file is almost never in sync on the first try. You download an
`.srt` for a movie and it's timed against a different release cut, or a
frame-rate conversion (23.976 vs 25 fps) has stretched every timestamp by a
few percent. Most subtitle players let you nudge things by a fixed offset
but can't fix that kind of drift, which grows over the runtime instead of
staying constant.

`subshift` is a small command-line tool that does two things to an SRT
file's timestamps:

- shift every timestamp by a fixed number of milliseconds
- rescale every timestamp by a multiplier, to correct frame-rate drift

Both can be combined in one pass (scale is applied first, then shift).

## Usage

Shift subtitles 2.5 seconds later:

```
python3 subshift.py movie.srt --shift 2500
```

Shift them 1.2 seconds earlier:

```
python3 subshift.py movie.srt --shift -1200
```

Fix subtitles authored for 25 fps video being played at 23.976 fps:

```
python3 subshift.py movie.srt --scale 25/23.976
```

Combine a scale correction with a small manual offset, and write to a
specific file:

```
python3 subshift.py movie.srt --scale 25/23.976 --shift 300 -o movie.fixed.srt
```

By default the result is written next to the input as
`<name>.shifted.srt`. Pass `-o -` to print the result to stdout instead of
writing a file.

## How it works

The parser looks for the `HH:MM:SS,mmm --> HH:MM:SS,mmm` line in each
subtitle block rather than assuming a fixed line position, since some
exported files drop or duplicate the cue-number line. Everything after
that line up to the next blank line is treated as the cue's text and
passed through unchanged. Output cues are renumbered sequentially
starting at 1.

Timestamps that would go negative after shifting are clamped to zero
rather than wrapping or erroring.

## Requirements

Python 3.8 or newer, standard library only.

## Tests

```
python3 -m unittest discover -s tests
```

## Limitations (for now)

- Only the SubRip (`.srt`) format is supported. No WebVTT, no ASS/SSA.
- No overlap detection or cue merging.
- Text formatting tags (`<i>`, `{\an8}`, etc.) are passed through as-is,
  not validated.
