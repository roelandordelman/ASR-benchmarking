---
title: "Whisper large-v3-turbo"
---

[Systems](index.md)

# Whisper large-v3-turbo

| | |
|---|---|
| **HuggingFace** | [openai/whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo) |
| **Language** | nl |
| **Type** | whisper |

OpenAI Whisper large-v3-turbo via faster-whisper. Approximately 8x faster than large-v3 with competitive accuracy due to a reduced decoder. Same inference configuration as large-v3. Audio is pre-segmented using reference STM windows for corpora with partial annotation (e.g. N-Best 2008), with utterances separated by less than 5 seconds merged into single chunks (matching UT convention). Results are fully automated without manual CTM corrections.

## Results

| Corpus | WER |
|--------|-----|
| [Native Elderly (read speech)](../corpora/jasmin_nl_compq_native_elderly.md) | 11.6% || [Native Teenagers (read speech)](../corpora/jasmin_nl_compq_native_teens.md) | 10.6% || [Non-native Adults (read speech)](../corpora/jasmin_nl_compq_nonnative_adults.md) | 28.6% || [Non-native Minors (read speech)](../corpora/jasmin_nl_compq_nonnative_minors.md) | 27.6% || [Broadcast News NL (N-Best 2008)](../corpora/nbest2008.md) | 16.3% || [Broadcast News NL Mini (N-Best 2008)](../corpora/nbest2008_mini.md) | 16.8% |

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
