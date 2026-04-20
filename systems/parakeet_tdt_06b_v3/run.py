#!/usr/bin/env python3
"""Transcribe a directory of audio files using nvidia/parakeet-tdt-0.6b-v3 via transformers.
Output: CTM format — filename channel start_time duration word confidence

Requires:
    pip install 'transformers>=4.40' torch soundfile librosa
"""
import argparse
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def transcribe_to_ctm(audio_dir: Path, output_ctm: Path, model_name: str = "nvidia/parakeet-tdt-0.6b-v3"):
    from transformers import pipeline
    import torch

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    asr = pipeline(
        "automatic-speech-recognition",
        model=model_name,
        device=device,
        return_timestamps="word",
    )

    audio_files = sorted(f for f in audio_dir.iterdir() if f.suffix.lower() in AUDIO_EXTENSIONS)
    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {audio_dir}")

    with open(output_ctm, "w") as out:
        for audio_file in audio_files:
            result = asr(str(audio_file))
            chunks = result.get("chunks", [])
            if not chunks:
                continue
            for chunk in chunks:
                text = chunk["text"].strip()
                if not text:
                    continue
                ts = chunk.get("timestamp", (None, None))
                start = max(float(ts[0]) if ts[0] is not None else 0.0, 0.0)
                end = float(ts[1]) if ts[1] is not None else start + 0.1
                duration = round(max(end - start, 0.01), 2)
                out.write(
                    f"{audio_file.stem} 1 {start:.2f} {duration:.2f} {text} 1.00\n"
                )


def main():
    parser = argparse.ArgumentParser(description="Parakeet TDT 0.6B v3 → CTM")
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--output-ctm", required=True)
    parser.add_argument("--model", default="nvidia/parakeet-tdt-0.6b-v3")
    args = parser.parse_args()

    transcribe_to_ctm(Path(args.audio_dir), Path(args.output_ctm), args.model)


if __name__ == "__main__":
    main()
