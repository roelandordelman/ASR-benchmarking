---
title: "Whisper large-v3"
---

[Systems](index.md)

# Whisper large-v3

| | |
|---|---|
| **HuggingFace** | [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3) |
| **Language** | nl |
| **Type** | whisper |

OpenAI Whisper large-v3 via faster-whisper. Audio is pre-segmented using reference STM windows for corpora with partial annotation (e.g. N-Best 2008), with utterances separated by less than 5 seconds merged into single chunks (matching UT convention). Results are fully automated without manual CTM corrections.

## Results

| Corpus | WER |
|--------|-----|
| [Example Corpus (ASR_NL_benchmark)](../corpora/example.md) | 7.5% || [Broadcast News NL (N-Best 2008)](../corpora/nbest2008.md) | 17.6% || [Broadcast News NL Mini (N-Best 2008)](../corpora/nbest2008_mini.md) | 17.5% |

## Configuration

| | |
|---|---|
| **Inference library** | faster-whisper |
| **Compute type** | int8 |
| **Device** | auto |
| **Beam size** | 5 |
| **VAD filter** | True |
| **Condition on prev. text** | False |
| **Word timestamps** | True |
| **Language hint** | nl |

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
