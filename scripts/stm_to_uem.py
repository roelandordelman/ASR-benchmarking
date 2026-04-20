#!/usr/bin/env python3
"""
Generate a UEM file from a reference STM.

UEM (Unpartitioned Evaluation Map) defines which portions of each audio file
are scored. Each line: <filename> <channel> <start_time> <end_time>

The UEM is derived by taking the union of all annotated segment windows per
file, merging overlapping or adjacent segments.

Usage:
    python3 scripts/stm_to_uem.py corpora/nbest2008/reference.stm > corpora/nbest2008/reference.uem
    python3 scripts/stm_to_uem.py corpora/nbest2008_mini/reference.stm > corpora/nbest2008_mini/reference.uem
"""
import sys
from pathlib import Path


def parse_stm(stm_path: Path) -> dict:
    segments = {}
    with open(stm_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";;"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                filename, channel = parts[0], parts[1]
                start, end = float(parts[3]), float(parts[4])
            except ValueError:
                continue
            segments.setdefault((filename, channel), []).append((start, end))
    return segments


def merge(segs: list) -> list:
    """Merge overlapping or adjacent segments."""
    if not segs:
        return []
    merged = list(sorted(segs))
    result = [list(merged[0])]
    for start, end in merged[1:]:
        if start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def main():
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} reference.stm [output.uem]")

    stm_path = Path(sys.argv[1])
    segments = parse_stm(stm_path)

    lines = []
    for (filename, channel), segs in sorted(segments.items()):
        for start, end in merge(segs):
            lines.append(f"{filename} {channel} {start:.3f} {end:.3f}")

    output = "\n".join(lines) + "\n"

    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text(output)
        print(f"Wrote {len(lines)} UEM entries to {sys.argv[2]}")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
