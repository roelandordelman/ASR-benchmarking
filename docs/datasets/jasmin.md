---
title: "Jasmin-CGN"
---

[Datasets](index.md)

# Jasmin-CGN (Dutch Speech Database)

The Jasmin-CGN corpus is a large Dutch speech database containing read speech and human-machine interaction (HMI) speech from diverse speaker groups: native children (7–11), native teenagers (12–16), non-native minors (7–16), non-native adults (18–60, CEFR A1–B2), and native elderly (65+). Collected jointly by multiple Dutch and Belgian research groups. Particularly challenging for ASR due to child speech, non-native accents, and spontaneous HMI dialogue.

**Website:** [https://taalmaterialen.ivdnt.org/download/tstc-jasmin-cgn/](https://taalmaterialen.ivdnt.org/download/tstc-jasmin-cgn/)

| | |
|---|---|
| **Language** | nl |
| **License** | restricted |

## Corpora

| Name | Size | Domain |
|---|---|---|
| [Jasmin NL — Read Speech (comp-q)](../corpora/jasmin_nl_compq.md) | 21.3h | read speech |
| ↳ [Native Children (read speech)](../corpora/jasmin_nl_compq_native_children.md) | 6.56h | read speech |
| ↳ [Native Teenagers (read speech)](../corpora/jasmin_nl_compq_native_teens.md) | 3.68h | read speech |
| ↳ [Native Elderly (read speech)](../corpora/jasmin_nl_compq_native_elderly.md) | 6.39h | read speech |
| ↳ [Non-native Adults (read speech)](../corpora/jasmin_nl_compq_nonnative_adults.md) | 2.59h | read speech |
| ↳ [Non-native Minors (read speech)](../corpora/jasmin_nl_compq_nonnative_minors.md) | 2.1h | read speech |

## Results

| System | [Native Teens](../corpora/jasmin_nl_compq_native_teens.md) | [Native Elderly](../corpora/jasmin_nl_compq_native_elderly.md) | [Non-native Adults](../corpora/jasmin_nl_compq_nonnative_adults.md) | [Non-native Minors](../corpora/jasmin_nl_compq_nonnative_minors.md) |
|---|---|---|---|---|
| [Whisper large-v3 (int8)](../systems/whisper_large_v3.md) | — | — | — | — |
| [Whisper large-v3-turbo (int8)](../systems/whisper_large_v3_turbo.md) | 10.6% | 11.6% | 28.6% | 27.6% |
