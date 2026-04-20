#!/usr/bin/env python3
"""
HuggingFace model watcher — finds new Dutch ASR models and registers them as benchmark systems.

Usage:
    python scripts/hf_watcher.py              # show new models, dry-run
    python scripts/hf_watcher.py --register   # write system.yaml + run.py for each new model
    python scripts/hf_watcher.py --register --run  # also trigger orchestrate.py

Schedule as a nightly cron / launchd job. Example crontab line:
    0 2 * * * cd /path/to/ASR-benchmarking && python scripts/hf_watcher.py --register --run >> logs/hf_watcher.log 2>&1
"""
import argparse
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml
from huggingface_hub import list_models, ModelFilter

SYSTEMS_DIR = Path("systems")
KNOWN_SYSTEMS_FILE = Path("scripts/known_hf_models.txt")

WHISPER_TEMPLATE_RUN = """\
#!/usr/bin/env python3
\"\"\"Auto-generated run.py for {model_id} via faster-whisper.\"\"\"
import argparse
from pathlib import Path

AUDIO_EXTENSIONS = {{".wav", ".mp3", ".flac", ".ogg", ".m4a"}}


def transcribe_to_ctm(audio_dir, output_ctm, model_id="{model_id}", language="nl"):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_id, device="auto", compute_type="int8")
    audio_files = sorted(f for f in audio_dir.iterdir() if f.suffix.lower() in AUDIO_EXTENSIONS)
    with open(output_ctm, "w") as out:
        for audio_file in audio_files:
            segments, _ = model.transcribe(str(audio_file), language=language, word_timestamps=True)
            for segment in segments:
                for word in (segment.words or []):
                    text = word.word.strip()
                    if text:
                        out.write(f"{{audio_file.stem}} 1 {{word.start:.2f}} {{word.end - word.start:.2f}} {{text}} {{word.probability:.2f}}\\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--output-ctm", required=True)
    parser.add_argument("--language", default="nl")
    args = parser.parse_args()
    transcribe_to_ctm(Path(args.audio_dir), Path(args.output_ctm), language=args.language)


if __name__ == "__main__":
    main()
"""


def load_known() -> set[str]:
    if KNOWN_SYSTEMS_FILE.exists():
        return set(KNOWN_SYSTEMS_FILE.read_text().splitlines())
    return set()


def save_known(known: set[str]):
    KNOWN_SYSTEMS_FILE.parent.mkdir(exist_ok=True)
    KNOWN_SYSTEMS_FILE.write_text("\n".join(sorted(known)) + "\n")


def safe_id(model_id: str) -> str:
    return model_id.replace("/", "__").replace("-", "_").replace(".", "_").lower()


def detect_type(model_id: str, tags: list) -> str:
    combined = model_id.lower() + " ".join(tags or [])
    if "whisper" in combined:
        return "whisper"
    if "wav2vec" in combined or "wav2vec2" in combined:
        return "wav2vec2"
    return "transformers"


def register_system(model_id: str, model_info) -> Path:
    sys_id = safe_id(model_id)
    sys_dir = SYSTEMS_DIR / sys_id
    sys_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "id": sys_id,
        "name": model_id,
        "description": f"Auto-registered from HuggingFace: {model_id}",
        "hf_model_id": model_id,
        "hf_model_revision": "main",
        "language": "nl",
        "type": detect_type(model_id, getattr(model_info, "tags", [])),
    }
    (sys_dir / "system.yaml").write_text(yaml.dump(meta, allow_unicode=True))

    model_type = meta["type"]
    if model_type == "whisper":
        (sys_dir / "run.py").write_text(WHISPER_TEMPLATE_RUN.format(model_id=model_id))
        (sys_dir / "requirements.txt").write_text("faster-whisper>=1.0.0\n")
    else:
        # Generic transformers pipeline — timestamps via forced-alignment (best-effort)
        run_content = textwrap.dedent(f"""\
            #!/usr/bin/env python3
            \"\"\"Auto-generated run.py for {model_id} (transformers pipeline).
            Note: no word-level timestamps — outputs TRN format instead of CTM.
            sclite supports TRN; adjust orchestrate.py if needed.
            \"\"\"
            # TODO: implement transcription for {model_id}
            raise NotImplementedError("Implement run.py for {model_id}")
        """)
        (sys_dir / "run.py").write_text(run_content)
        (sys_dir / "requirements.txt").write_text("transformers>=4.40\ntorch\n")

    print(f"  registered: {sys_id} → {sys_dir}")
    return sys_dir


def main():
    parser = argparse.ArgumentParser(description="HuggingFace Dutch ASR model watcher")
    parser.add_argument("--register", action="store_true", help="Write system dirs for new models")
    parser.add_argument("--run", action="store_true", help="Trigger orchestrate.py after registration")
    parser.add_argument("--limit", type=int, default=100, help="Max models to fetch from HF")
    args = parser.parse_args()

    known = load_known()

    print("Fetching Dutch ASR models from HuggingFace...")
    models = list(list_models(
        filter=ModelFilter(language="nl", task="automatic-speech-recognition"),
        sort="lastModified",
        direction=-1,
        limit=args.limit,
    ))
    print(f"  found {len(models)} models")

    new_models = [m for m in models if m.modelId not in known]
    if not new_models:
        print("No new models found.")
        return

    print(f"\nNew models ({len(new_models)}):")
    for m in new_models:
        print(f"  {m.modelId}  (last modified: {m.lastModified})")

    if not args.register:
        print("\nRe-run with --register to add these as benchmark systems.")
        return

    registered = []
    for m in new_models:
        register_system(m.modelId, m)
        registered.append(m.modelId)
        known.add(m.modelId)

    save_known(known)
    print(f"\nRegistered {len(registered)} system(s).")

    if args.run and registered:
        print("\nTriggering orchestrate.py...")
        subprocess.run([sys.executable, "orchestrate.py"], check=True)


if __name__ == "__main__":
    main()
