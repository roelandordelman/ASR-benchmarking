---
title: "Whisper large-v3"
---

# Whisper large-v3

| | |
|---|---|
| **HuggingFace** | [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3) |
| **Language** | nl |
| **Type** | whisper |

OpenAI Whisper large-v3 via faster-whisper. Word-level timestamps enable direct CTM output.

## Results

| Corpus | WER |
|--------|-----|
| [example](../corpora/example.md) | 7.5% |
| [nbest2008_mini](../corpora/nbest2008_mini.md) | 47.5% |

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
