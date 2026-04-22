---
title: "Broadcast News NL (N-Best 2008)"
---

[Datasets](../datasets/) › [N-Best 2008](../datasets/nbest2008.md)

# Broadcast News NL (N-Best 2008)

| | |
|---|---|
| **Domain** | broadcast news |
| **Language** | nl |
| **Size** | 9.0 hours |
| **License** | restricted |

Dutch broadcast news evaluation corpus from the N-Best 2008 evaluation campaign. 15 recordings, ~541 minutes. Contains BN-NL (broadcast news, Netherlands accent) and BN-VL (Flemish accent). Focus conditions: F0=clean, F1=spontaneous, F2=telephone/interview. Best system in 2008 achieved 17.8% WER on BN-NL. Reference transcriptions exclude advertisements, non-Dutch speech, and linguistically unchallenging content (e.g. weather forecasts). Non-lexical events (hesitations, filled pauses) are excluded from scoring but can cause insertions in hypothesis. Note on comparability: the UT open benchmark (opensource-spraakherkenning-nl.github.io/ASR_NL_results) reports 12.5% WER for faster-whisper large-v3 on BN-NL. The ~5 point gap with our results is likely due to: (1) int8 vs float16 quantization, (2) whisper-timestamped vs faster-whisper timestamp alignment, (3) additional manual CTM corrections applied by UT, (4) extra number/spelling normalization beyond the ASR_NL_benchmark Docker tool. The UT methodology is not fully documented. Our results are fully automated and reproducible.

**Reference:** Van Leeuwen, D.A., Kessens, J., Sanders, E. & Van den Heuvel, H. (2008). Results of the N-Best 2008 Dutch Speech Recognition Evaluation. https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=32b10cb0f4cb99ba934f5be5066638a5ad9b19f2

## Sub-corpora

| Name | Size | Best WER |
|---|---|---|
| [Broadcast News NL Mini (N-Best 2008)](nbest2008_mini.md) | 0.77h | 16.8% |

## Results

| System | WER |
|--------|-----|
| [Whisper large-v3](../systems/whisper_large_v3.md) | 17.6% |
| [Whisper large-v3-turbo](../systems/whisper_large_v3_turbo.md) | 16.3% |
