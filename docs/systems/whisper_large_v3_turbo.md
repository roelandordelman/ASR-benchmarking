---
title: "Whisper large-v3-turbo"
---

# Whisper large-v3-turbo

| | |
|---|---|
| **HuggingFace** | [openai/whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo) |
| **Language** | nl |
| **Type** | whisper |

OpenAI Whisper large-v3-turbo via faster-whisper (int8 quantization, VAD filter enabled). ~8x faster than large-v3 with competitive accuracy. Audio is pre-segmented using reference STM windows for corpora with partial annotation (e.g. N-Best 2008). Results are fully automated without manual CTM corrections.

## Results

| Corpus | WER |
|--------|-----|
| [nbest2008](../corpora/nbest2008.md) | 16.3% |
| [nbest2008_mini](../corpora/nbest2008_mini.md) | 16.8% |

## Hardware

| | |
|---|---|
| **Machine** | MacBook Pro (Mac16,8) |
| **Chip** | Apple M4 Pro |
| **Cores** | 14-core (10P+4E) |
| **RAM (GB)** | 48 |
| **Accelerator** | cpu (Apple Accelerate/AMX) |
| **OS** | Darwin 25.4.0 |
| **CTranslate2** | 4.7.1 |
| **Python** | 3.9.6 |
