#!/usr/bin/env python3
"""Transcribe a directory of audio files using faster-whisper (large-v3-turbo).
Output: CTM format — filename channel start_time duration word confidence
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from whisper_run import transcribe_to_ctm


def main():
    parser = argparse.ArgumentParser(description="Whisper large-v3-turbo → CTM")
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--output-ctm", required=True)
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--language", default="nl")
    parser.add_argument("--reference-stm", default=None)
    args = parser.parse_args()

    transcribe_to_ctm(
        Path(args.audio_dir),
        Path(args.output_ctm),
        args.model,
        args.language,
        Path(args.reference_stm) if args.reference_stm else None,
    )


if __name__ == "__main__":
    main()
