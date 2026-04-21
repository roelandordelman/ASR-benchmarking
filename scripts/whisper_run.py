"""Shared transcription logic for faster-whisper based systems."""
import subprocess
import tempfile
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def parse_stm_segments(stm_path: Path) -> dict:
    """Return {stem: [(start, end), ...]} sorted by start time."""
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
                start, end = float(parts[3]), float(parts[4])
            except ValueError:
                continue
            segments.setdefault(parts[0], []).append((start, end))
    return {k: sorted(v) for k, v in segments.items()}


def merge_segments(segs: list, gap: float = 5.0) -> list:
    """Merge segments separated by less than gap seconds (matches UT convention)."""
    if not segs:
        return []
    merged = [[segs[0][0], segs[0][1]]]
    for start, end in segs[1:]:
        if start - merged[-1][1] < gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def _extract_segment(audio_file: Path, start: float, duration: float, tmp_path: str):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-ss", str(start), "-t", str(duration),
         "-i", str(audio_file), tmp_path],
        check=True,
    )


def _write_words(segments_iter, offset: float, stem: str, out):
    for segment in segments_iter:
        if segment.words is None:
            continue
        for word in segment.words:
            text = word.word.strip()
            if not text:
                continue
            start = max(word.start + offset, 0.0)
            duration = round(max(word.end - word.start, 0.01), 2)
            out.write(f"{stem} 1 {start:.2f} {duration:.2f} {text} {word.probability:.2f}\n")


def transcribe_to_ctm(
    audio_dir: Path,
    output_ctm: Path,
    model_size: str,
    language: str,
    reference_stm: Path = None,
):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="int8")
    audio_files = sorted(f for f in audio_dir.iterdir()
                         if f.suffix.lower() in AUDIO_EXTENSIONS and not f.name.startswith("._"))
    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {audio_dir}")

    stm_segments = {}
    if reference_stm and reference_stm.exists():
        raw = parse_stm_segments(reference_stm)
        stm_segments = {k: merge_segments(v) for k, v in raw.items()}

    transcribe_kwargs = dict(
        language=language,
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    with open(output_ctm, "w") as out:
        for audio_file in audio_files:
            stem = audio_file.stem
            if stem in stm_segments:
                print(f"    segmented: {stem} ({len(stm_segments[stem])} segments)")
                for seg_start, seg_end in stm_segments[stem]:
                    dur = seg_end - seg_start
                    if dur <= 0:
                        continue
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp_path = tmp.name
                    try:
                        _extract_segment(audio_file, seg_start, dur, tmp_path)
                        result, _ = model.transcribe(tmp_path, **transcribe_kwargs)
                        _write_words(result, seg_start, stem, out)
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
            else:
                result, _ = model.transcribe(str(audio_file), **transcribe_kwargs)
                _write_words(result, 0.0, stem, out)
