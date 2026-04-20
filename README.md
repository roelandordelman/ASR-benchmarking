# ASR NL Benchmark

Automated benchmark for Dutch ASR systems. Runs evaluation across a matrix of systems × corpora and publishes results as a static website at [roelandordelman.github.io/ASR-benchmarking](https://roelandordelman.github.io/ASR-benchmarking/).

## Requirements

- Python 3.9+
- Docker Desktop (running) — used for the NIST sclite evaluation step
- SSH key access to Hetzner Storage Box — for corpus audio (request access via `corpus.yaml`)

```bash
pip3 install -r requirements.txt
```

## Quick start — smoke test (no audio needed)

```bash
python3 orchestrate.py --use-precomputed
```

Uses the precomputed example CTM bundled with the repo. Runs the full eval + doc generation pipeline in under a minute.

## Running a real benchmark

```bash
cp .env.example .env
# edit: set ASR_CORPUS_ROOT and optionally HF_TOKEN

export $(cat .env | xargs)
python3 orchestrate.py --corpus nbest2008_mini
```

The orchestrator will:
1. Fetch missing audio from the Hetzner Storage Box via SFTP (if you have access)
2. Run the ASR system on the audio
3. Score with the [ASR_NL_benchmark](https://github.com/opensource-spraakherkenning-nl/ASR_NL_benchmark) Docker image (sclite)
4. Save `results/{system}/{corpus}/summary.json`
5. Regenerate `docs/` markdown

## Audio storage

Audio files are never committed to git. They live locally at:

```
$ASR_CORPUS_ROOT/{corpus_id}/audio/
```

Each corpus with a restricted or large audio set is backed by the Hetzner Storage Box. The fetch script handles download:

```bash
python3 scripts/fetch_corpus.py nbest2008_mini          # download missing files
python3 scripts/fetch_corpus.py nbest2008_mini --list   # inspect remote without downloading
```

**Requesting access:** contact the maintainer listed in the relevant `corpus.yaml`.  
**SSH key:** set `ASR_SFTP_KEY=/path/to/key` (default: `~/.ssh/id_hetzner_rclone`).

## Adding a corpus

1. Create `corpora/{id}/` with:
   - `corpus.yaml` — metadata, SFTP location, license, contact
   - `reference.stm` — reference transcripts in STM format
   - `precomputed/hyp.ctm` — optional, for smoke-testing without audio
2. Upload audio to storage and add the `sftp:` block to `corpus.yaml`
3. Place audio locally at `$ASR_CORPUS_ROOT/{id}/audio/`
4. Run `python3 orchestrate.py --corpus {id}`

### Corpus annotation coverage

Some corpora (e.g. N-Best 2008) only annotate selected segments of each audio file — not the full recording. Running ASR on the full file causes Whisper to transcribe unannotated regions, inflating the insertion rate and producing unrealistically high WER (we observed ~47% instead of the expected ~10%).

Set `segment_audio: true` in `corpus.yaml` for these corpora. The orchestrator will then pass the reference STM to the ASR system, which uses it to extract and transcribe only the annotated segments (matching the [UT methodology](https://opensource-spraakherkenning-nl.github.io/ASR_NL_results/)). Timestamps are offset back to the original file timeline before scoring.

## Adding a system

1. Create `systems/{id}/` with:
   - `system.yaml` — metadata, HuggingFace model id, type
   - `run.py` — standard interface: `--audio-dir DIR --output-ctm FILE`
   - `requirements.txt`
2. Run `python3 orchestrate.py --system {id}`

See `systems/whisper_large_v3/` as a reference implementation.

## Corpus overview

| Corpus | Domain | Size | Access | Notes |
|--------|--------|------|--------|-------|
| `example` | Broadcast news | ~2 min | Public (bundled) | |
| `nbest2008_mini` | Broadcast news | ~46 min | Request | Partial annotation — uses `segment_audio` |
| `nbest2008` | Broadcast news | ~541 min | Request | Partial annotation — uses `segment_audio` |
| `jasmin_nl_compq` | Read + spontaneous speech (children & adults) | ~21 h | Request | Fully annotated |

## Nightly HuggingFace watcher

Automatically detects new Dutch ASR models on HuggingFace and registers them as benchmark systems:

```bash
python3 scripts/hf_watcher.py                  # dry run — show new models
python3 scripts/hf_watcher.py --register       # write system dirs for new models
python3 scripts/hf_watcher.py --register --run # register + benchmark
```

Add to crontab for nightly automation:
```
0 2 * * * cd /path/to/ASR-benchmarking && python3 scripts/hf_watcher.py --register --run >> logs/hf_watcher.log 2>&1
```

## Website

Results are published via GitHub Pages from the `docs/` folder. The site rebuilds automatically when you push. Run `python3 generate_docs.py` locally to preview changes before pushing.
