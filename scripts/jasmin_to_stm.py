#!/usr/bin/env python3
"""
Convert Jasmin-CGN ORT TextGrid annotations to STM format for ASR benchmarking.

Usage:
    # NL native adults (group 5), comp-q, both components combined:
    python3 scripts/jasmin_to_stm.py --lang nl --group 5 --output corpora/jasmin_nl_g5/reference.stm

    # NL all groups, comp-p only:
    python3 scripts/jasmin_to_stm.py --lang nl --component comp-p --output corpora/jasmin_nl_compp/reference.stm

    # Dry-run: show stats without writing:
    python3 scripts/jasmin_to_stm.py --lang nl --group 5 --dry-run

STM output format:
    <filename> <channel> <speaker_id> <begin_time> <end_time> <tags> <text>

Category tags encode: component, group, gender — enabling per-category WER in sclite.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

JASMIN_ROOT = Path("/Users/roeland.ordelman/data/jasmin")
ORT_ROOT    = JASMIN_ROOT / "data/annot/text/ort"
META_ROOT   = JASMIN_ROOT / "data/meta/text"

GROUP_LABELS = {
    "1": "native_children",    # ages 7-11
    "2": "native_teens",       # ages 12-16
    "3": "nonnative_minors",   # ages 7-16, non-native
    "4": "nonnative_adults",   # ages 18-60, non-native (CEF A1-B2)
    "5": "native_elderly",     # ages 65+
}

CEF_LEVELS = {"A1", "A2", "B1", "B2"}


def load_metadata(lang: str) -> dict:
    """Return dict of filename → metadata row."""
    meta_file = META_ROOT / lang / "recordings.txt"
    if not meta_file.exists():
        sys.exit(f"Metadata not found: {meta_file}")
    meta = {}
    with open(meta_file) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            root = row["Root"].strip()
            if root:
                meta[root] = row
    return meta


def parse_short_textgrid(path: Path) -> list[dict]:
    """
    Parse Praat 'short' TextGrid format.
    Returns list of tiers: [{"name": str, "intervals": [(xmin, xmax, text), ...]}]
    """
    # Jasmin files are latin-1 encoded
    try:
        lines = path.read_text(encoding="latin-1").splitlines()
    except Exception:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    it = iter(lines)

    def nextval():
        for line in it:
            line = line.strip()
            if line:
                return line
        return None

    # Header
    file_type = nextval()
    if "ooTextFile short" not in file_type:
        raise ValueError(f"Unexpected TextGrid format in {path}: {file_type}")
    nextval()  # "TextGrid"
    nextval()  # xmin
    nextval()  # xmax
    nextval()  # <exists>

    n_tiers = int(nextval())
    tiers = []

    for _ in range(n_tiers):
        tier_type = nextval().strip('"')
        tier_name = nextval().strip('"')
        nextval()  # tier xmin
        nextval()  # tier xmax
        n_intervals = int(nextval())

        intervals = []
        for _ in range(n_intervals):
            raw_xmin = nextval()
            raw_xmax = nextval()
            try:
                xmin = float(raw_xmin)
                xmax = float(raw_xmax)
            except ValueError:
                # Malformed tier (e.g. recording-quality note with text where xmax expected)
                nextval()  # consume remaining value and skip this tier's intervals
                intervals = []
                break
            raw  = nextval()
            text = raw.strip('"').strip()
            if text:
                intervals.append((xmin, xmax, text))

        tiers.append({"name": tier_name, "type": tier_type, "intervals": intervals})

    return tiers


def make_tags(row: dict) -> str:
    """Build sclite STM category tag string from metadata row."""
    component = row.get("Component", "").strip().replace("-", "")  # compp / compq
    group     = row.get("Group", "").strip()
    gender    = row.get("Gender", "").strip() or "U"
    cef       = row.get("CEF", "").strip()

    label = GROUP_LABELS.get(group, f"g{group}")
    return f"<o,{component},{label},{gender}>"


def convert(lang: str, components: list, groups: list, output: Path, dry_run: bool, min_duration: float):
    meta = load_metadata(lang)

    # Collect ORT files
    ort_files = []
    for comp in components:
        comp_dir = ORT_ROOT / comp / lang
        if not comp_dir.exists():
            print(f"[warn] ORT directory not found: {comp_dir}")
            continue
        ort_files.extend(sorted(comp_dir.glob("*.ort")))

    if not ort_files:
        sys.exit("No ORT files found for the given filters.")

    segments = []
    skipped_files = 0
    skipped_segs  = 0

    for ort_path in ort_files:
        stem = ort_path.stem
        row  = meta.get(stem)

        if row is None:
            skipped_files += 1
            continue

        if groups and row.get("Group", "").strip() not in groups:
            continue

        try:
            tiers = parse_short_textgrid(ort_path)
        except Exception as e:
            print(f"[warn] Could not parse {ort_path.name}: {e}")
            skipped_files += 1
            continue

        # Skip TTS tier — use the second tier (speaker tier)
        speaker_tiers = [t for t in tiers if t["name"] != "TTS"]
        if not speaker_tiers:
            skipped_files += 1
            continue

        speaker_id = speaker_tiers[0]["name"]
        tags       = make_tags(row)

        for xmin, xmax, text in speaker_tiers[0]["intervals"]:
            duration = xmax - xmin
            if duration < min_duration:
                skipped_segs += 1
                continue
            # Normalise Jasmin transcription conventions:
            text = re.sub(r"\[.*?\]", "", text)      # [laughter], [noise] etc.
            text = re.sub(r"\bggg+\b", "", text)      # filled pauses / laughter marker
            text = re.sub(r"\*[a-z]?", "", text)     # annotation codes: hun*f→hun, Bolla*→Bolla
            text = re.sub(r"\+", "", text)            # overlap marker
            text = re.sub(r"[<>]", "", text)          # angle bracket annotations
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                skipped_segs += 1
                continue
            segments.append((stem, speaker_id, xmin, xmax, tags, text))

    if dry_run:
        files = sorted({s[0] for s in segments})
        speakers = sorted({s[1] for s in segments})
        total_dur = sum(s[3] - s[2] for s in segments)
        print(f"Files    : {len(files)}")
        print(f"Speakers : {len(speakers)}")
        print(f"Segments : {len(segments)}  (skipped: {skipped_segs})")
        print(f"Duration : {total_dur/60:.1f} min")
        print(f"Skipped files (no meta / parse error): {skipped_files}")
        print("\nSample output (first 5 segments):")
        for stem, spk, xmin, xmax, tags, text in segments[:5]:
            print(f"  {stem} 1 {spk} {xmin:.3f} {xmax:.3f} {tags} {text}")
        return

    if not segments:
        sys.exit("No segments produced — check filters.")

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        for stem, spk, xmin, xmax, tags, text in segments:
            f.write(f"{stem} 1 {spk} {xmin:.3f} {xmax:.3f} {tags} {text}\n")

    total_dur = sum(s[3] - s[2] for s in segments)
    print(f"Written {len(segments)} segments ({total_dur/60:.1f} min) to {output}")
    print(f"Skipped: {skipped_files} files, {skipped_segs} segments")


def main():
    parser = argparse.ArgumentParser(description="Convert Jasmin ORT TextGrids to STM")
    parser.add_argument("--lang",      choices=["nl", "vl"], default="nl")
    parser.add_argument("--component", choices=["comp-p", "comp-q", "both"], default="both")
    parser.add_argument("--group",     help="Comma-separated group numbers (1-5). Default: all")
    parser.add_argument("--output",    type=Path, default=Path("corpora/jasmin_nl/reference.stm"))
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--min-duration", type=float, default=0.1,
                        help="Minimum segment duration in seconds (default: 0.1)")
    args = parser.parse_args()

    components = ["comp-p", "comp-q"] if args.component == "both" else [args.component]
    groups = [g.strip() for g in args.group.split(",")] if args.group else []

    convert(
        lang=args.lang,
        components=components,
        groups=groups,
        output=args.output,
        dry_run=args.dry_run,
        min_duration=args.min_duration,
    )


if __name__ == "__main__":
    main()
