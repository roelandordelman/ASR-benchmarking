#!/usr/bin/env python3
"""
ASR Benchmark Orchestrator

Detects missing (system, corpus) pairs, runs ASR + evaluation, updates docs.

Usage:
    python orchestrate.py                        # run all missing pairs
    python orchestrate.py --system whisper_large_v3
    python orchestrate.py --corpus example
    python orchestrate.py --use-precomputed      # skip ASR, use corpora/X/precomputed/hyp.ctm
    python orchestrate.py --dry-run
    python orchestrate.py --force                # re-run even if results exist
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional

import yaml
import pandas as pd

SYSTEMS_DIR = Path("systems")
CORPORA_DIR = Path("corpora")
RESULTS_DIR = Path("results")
EVAL_DOCKER_IMAGE = "asrnlbenchmark/asr-nl-benchmark:latest"


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def get_corpora():
    return sorted(p for p in CORPORA_DIR.iterdir() if p.is_dir() and (p / "corpus.yaml").exists())


def get_systems():
    return sorted(p for p in SYSTEMS_DIR.iterdir() if p.is_dir() and (p / "system.yaml").exists())


def result_dir(system: Path, corpus: Path) -> Path:
    return RESULTS_DIR / system.name / corpus.name


def summary_exists(system: Path, corpus: Path) -> bool:
    return (result_dir(system, corpus) / "summary.json").exists()


def resolve_audio_dir(corpus: Path, corpus_meta: Optional[dict] = None) -> Optional[Path]:
    # Support audio_corpus: redirect to a different corpus's audio directory
    audio_id = (corpus_meta or {}).get("audio_corpus", corpus.name)
    corpus_root = os.getenv("ASR_CORPUS_ROOT")
    if corpus_root:
        candidate = Path(corpus_root) / audio_id / "audio"
        if candidate.exists():
            return candidate
    local = corpus.parent / audio_id / "audio"
    if local.exists():
        return local
    return None


def try_fetch_audio(corpus: Path) -> Optional[Path]:
    """Attempt SFTP fetch if corpus.yaml has sftp config and audio is missing."""
    meta = load_yaml(corpus / "corpus.yaml")
    if not meta.get("sftp"):
        return None
    print(f"  → Audio not found locally — attempting SFTP fetch for {corpus.name}")
    result = subprocess.run(
        [sys.executable, "scripts/fetch_corpus.py", corpus.name],
        check=False,
    )
    if result.returncode != 0:
        print(f"  [warn] SFTP fetch failed — to request access: {meta.get('contact', 'see corpus.yaml')}")
        return None
    return resolve_audio_dir(corpus, meta)


def run_asr(system: Path, audio_dir: Path, work_dir: Path, corpus_meta: dict) -> Path:
    ctm_path = work_dir / "hyp.ctm"
    run_script = system / "run.py"
    print(f"  → ASR: {system.name} on {audio_dir}")
    cmd = [sys.executable, str(run_script), "--audio-dir", str(audio_dir), "--output-ctm", str(ctm_path)]
    if corpus_meta.get("segment_audio"):
        cmd += ["--reference-stm", str(work_dir / "reference.stm")]
        print(f"  → Segmented transcription (reference-guided)")
    subprocess.run(cmd, check=True)
    return ctm_path


def run_eval(system: Path, work_dir: Path) -> Path:
    abs_work = work_dir.resolve()
    print(f"  → Eval Docker ({EVAL_DOCKER_IMAGE})")
    cmd = [
        "docker", "run", "--rm",
        "--mount", f"type=bind,source={abs_work},target=/input",
        EVAL_DOCKER_IMAGE,
        "python", "ASR_NL_benchmark",
        "-hyp", "hyp.ctm", "ctm",
        "-ref", "reference.stm", "stm",
        "-kind", system.name,
    ]
    subprocess.run(cmd, check=True)
    return work_dir / "results"


def parse_results(results_subdir: Path) -> dict:
    csvs = list(results_subdir.glob("results_category_*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No results CSV in {results_subdir}")
    df = pd.read_csv(csvs[0])
    df["product"] = df["WER"] * df["ref_words"]
    overall_wer = float(df["product"].sum() / df["ref_words"].sum())
    return {
        "overall_wer": round(overall_wer, 4),
        "categories": df[["category", "ref_words", "WER"]].to_dict(orient="records"),
    }


def main():
    parser = argparse.ArgumentParser(description="ASR Benchmark Orchestrator")
    parser.add_argument("--system", help="Run only this system id")
    parser.add_argument("--corpus", help="Run only this corpus id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--use-precomputed", action="store_true",
                        help="Use corpora/X/precomputed/hyp.ctm instead of running ASR")
    parser.add_argument("--force", action="store_true", help="Re-run even if results exist")
    parser.add_argument("--skip-asr", action="store_true", help="Skip ASR, use existing hyp.ctm and re-run eval only")
    args = parser.parse_args()

    corpora = get_corpora()
    systems = get_systems()
    if args.corpus:
        corpora = [c for c in corpora if c.name == args.corpus]
    if args.system:
        systems = [s for s in systems if s.name == args.system]

    if not corpora:
        sys.exit("No matching corpora found.")
    if not systems:
        sys.exit("No matching systems found.")

    ran = skipped = 0

    for system in systems:
        for corpus in corpora:
            tag = f"{system.name} × {corpus.name}"

            if summary_exists(system, corpus) and not args.force and not args.skip_asr:
                print(f"[skip]  {tag}")
                skipped += 1
                continue

            if args.dry_run:
                print(f"[would] {tag}")
                continue

            print(f"[run]   {tag}")
            work_dir = result_dir(system, corpus)
            work_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy(corpus / "reference.stm", work_dir / "reference.stm")
            uem_src = corpus / "reference.uem"
            if uem_src.exists():
                shutil.copy(uem_src, work_dir / "reference.uem")

            corpus_meta = load_yaml(corpus / "corpus.yaml")
            t_asr_start = time.time()
            if args.skip_asr:
                if not (work_dir / "hyp.ctm").exists():
                    print(f"  [skip] no hyp.ctm found in {work_dir} — run ASR first")
                    continue
                print(f"  → Skipping ASR, using existing hyp.ctm")
                asr_duration_s = None
            elif args.use_precomputed:
                precomputed = corpus / "precomputed" / "hyp.ctm"
                if not precomputed.exists():
                    print(f"  [skip] no precomputed CTM at {precomputed}")
                    continue
                shutil.copy(precomputed, work_dir / "hyp.ctm")
                asr_duration_s = None
            else:
                audio_dir = resolve_audio_dir(corpus, corpus_meta)
                if audio_dir is None:
                    audio_dir = try_fetch_audio(corpus)
                if audio_dir is None:
                    print(f"  [skip] audio not found — set ASR_CORPUS_ROOT or add corpora/{corpus.name}/audio/")
                    continue
                run_asr(system, audio_dir, work_dir, corpus_meta)
                asr_duration_s = time.time() - t_asr_start

            results_subdir = run_eval(system, work_dir)

            summary = parse_results(results_subdir)
            summary["system"] = system.name
            summary["corpus"] = corpus.name
            summary["timestamp"] = datetime.now(timezone.utc).isoformat()

            audio_hours = corpus_meta.get("size_hours")
            if asr_duration_s and audio_hours:
                rtf = round(asr_duration_s / (audio_hours * 3600), 3)
                summary["rtf"] = rtf
                print(f"  [done] WER = {summary['overall_wer']:.1f}%  RTF = {rtf:.3f}")
            else:
                print(f"  [done] WER = {summary['overall_wer']:.1f}%")

            sys.path.insert(0, str(Path(__file__).parent / "scripts"))
            from detect_hardware import detect as detect_hardware
            summary["hardware"] = detect_hardware()

            (work_dir / "summary.json").write_text(json.dumps(summary, indent=2))
            ran += 1

    print(f"\nDone: {ran} run, {skipped} skipped.")

    if ran > 0 and not args.dry_run:
        subprocess.run([sys.executable, "generate_docs.py"], check=True)


if __name__ == "__main__":
    main()
