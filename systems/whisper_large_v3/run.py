#!/usr/bin/env python3
"""Transcribe a directory of audio files using faster-whisper.
Output: CTM format — filename channel start_time duration word confidence
"""
import argparse
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def transcribe_to_ctm(audio_dir: Path, output_ctm: Path, model_size: str = "large-v3", language: str = "nl"):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="int8")

    audio_files = sorted(f for f in audio_dir.iterdir() if f.suffix.lower() in AUDIO_EXTENSIONS)
    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {audio_dir}")

    with open(output_ctm, "w") as out:
        for audio_file in audio_files:
            segments, _ = model.transcribe(str(audio_file), language=language, word_timestamps=True)
            for segment in segments:
                if segment.words is None:
                    continue
                for word in segment.words:
                    text = word.word.strip()
                    if not text:
                        continue
                    duration = round(word.end - word.start, 2)
                    out.write(
                        f"{audio_file.stem} 1 {word.start:.2f} {duration:.2f} {text} {word.probability:.2f}\n"
                    )


def main():
    parser = argparse.ArgumentParser(description="Whisper large-v3 → CTM")
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--output-ctm", required=True)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--language", default="nl")
    args = parser.parse_args()

    transcribe_to_ctm(Path(args.audio_dir), Path(args.output_ctm), args.model, args.language)


if __name__ == "__main__":
    main()
