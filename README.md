# ASR NL Benchmark

Automated benchmark for Dutch ASR systems. Runs evaluation across a matrix of systems × corpora and publishes results as a static website.

## Quick start

```bash
pip install -r requirements.txt

# Test the full pipeline with precomputed example data (no audio or GPU needed)
python orchestrate.py --use-precomputed

# Open docs/index.md to see the generated matrix
```

## Adding a corpus

1. Create `corpora/{id}/` with:
   - `corpus.yaml` — metadata
   - `reference.stm` — reference transcripts
   - `precomputed/hyp.ctm` — optional, for smoke-testing without audio
2. Place audio files in `$ASR_CORPUS_ROOT/{id}/audio/` (local only, not committed)
3. Run `python orchestrate.py`

## Adding a system

1. Create `systems/{id}/` with:
   - `system.yaml` — metadata
   - `run.py` — transcribes `--audio-dir` → `--output-ctm`
   - `requirements.txt`
2. Run `python orchestrate.py`

## Audio storage

Audio is kept locally and never committed. Set the root path in `.env`:

```bash
cp .env.example .env
# edit ASR_CORPUS_ROOT=/your/local/path
```

For team collaboration, [DVC](https://dvc.org) can sync audio to a shared remote (SSH, S3, NAS) while keeping the rest of the repo in git.

## Nightly HuggingFace watcher

```bash
# Check for new Dutch ASR models on HuggingFace
python scripts/hf_watcher.py

# Register them as systems and run benchmarks
python scripts/hf_watcher.py --register --run
```

Add to crontab for nightly automation:
```
0 2 * * * cd /path/to/ASR-benchmarking && python scripts/hf_watcher.py --register --run >> logs/hf_watcher.log 2>&1
```

## Evaluation

Uses the [ASR_NL_benchmark](https://github.com/opensource-spraakherkenning-nl/ASR_NL_benchmark) Docker image (NIST SCTK / sclite). Requires Docker to be running.

## Website

Results are published via GitHub Pages. Enable Pages on the `docs/` folder in your repo settings. The site rebuilds automatically when you push updated markdown.
