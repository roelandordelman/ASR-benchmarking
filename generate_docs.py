#!/usr/bin/env python3
"""
Generate docs/ markdown from results/*/summary.json files.

Run automatically by orchestrate.py after new results, or manually:
    python generate_docs.py
"""
import json
from datetime import datetime
from pathlib import Path

import yaml

RESULTS_DIR = Path("results")
DOCS_DIR = Path("docs")
CORPORA_DIR = Path("corpora")
SYSTEMS_DIR = Path("systems")


def load_yaml(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def collect_summaries() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(RESULTS_DIR.glob("*/*/summary.json"))]


def fmt_wer(v: float) -> str:
    return f"{v:.1f}%"


def build_matrix(summaries):
    systems = sorted({s["system"] for s in summaries})
    corpora = sorted({s["corpus"] for s in summaries})
    wer = {(s["system"], s["corpus"]): s["overall_wer"] for s in summaries}
    return systems, corpora, wer


def write_index(systems, corpora, wer):
    cols = " | ".join(f"[{c}](corpora/{c}.md)" for c in corpora)
    sep  = "|".join(["-------"] * (len(corpora) + 1))
    rows = []
    for sys in systems:
        cells = [fmt_wer(wer[(sys, c)]) if (sys, c) in wer else "—" for c in corpora]
        rows.append(f"| [{sys}](systems/{sys}.md) | " + " | ".join(cells) + " |")

    content = f"""---
title: ASR NL Benchmark Results
---

# Dutch ASR Benchmark — WER Matrix

*Lower is better. Generated {datetime.now().strftime('%Y-%m-%d')}.*

| System | {cols} |
|{sep}|
""" + "\n".join(rows) + """

---

Browse details by [corpus](corpora/) or [system](systems/).
"""
    (DOCS_DIR / "index.md").write_text(content)
    print("  wrote docs/index.md")


def write_corpus_index(corpora):
    items = "\n".join(f"- [{c}]({c}.md)" for c in corpora)
    (DOCS_DIR / "corpora" / "index.md").write_text(f"# Corpora\n\n{items}\n")


def write_system_index(systems):
    items = "\n".join(f"- [{s}]({s}.md)" for s in systems)
    (DOCS_DIR / "systems" / "index.md").write_text(f"# Systems\n\n{items}\n")


def write_corpus_pages(summaries, corpora):
    (DOCS_DIR / "corpora").mkdir(exist_ok=True)
    for corpus_id in corpora:
        meta = load_yaml(CORPORA_DIR / corpus_id / "corpus.yaml")
        rows = [
            f"| [{s['system']}](../systems/{s['system']}.md) | {fmt_wer(s['overall_wer'])} |"
            for s in summaries if s["corpus"] == corpus_id
        ]
        content = f"""---
title: "{meta.get('name', corpus_id)}"
---

# {meta.get('name', corpus_id)}

| | |
|---|---|
| **Domain** | {meta.get('domain', '—')} |
| **Language** | {meta.get('language', '—')} |
| **Size** | {meta.get('size_hours', '—')} hours |
| **License** | {meta.get('license', '—')} |

{meta.get('description', '')}

## Results

| System | WER |
|--------|-----|
""" + "\n".join(rows) + "\n"
        (DOCS_DIR / "corpora" / f"{corpus_id}.md").write_text(content)
        print(f"  wrote docs/corpora/{corpus_id}.md")


def _fmt_hardware(hw: dict) -> str:
    if not hw:
        return ""
    lines = ["## Hardware"]
    lines.append("\n| | |")
    lines.append("|---|---|")
    for key, label in [
        ("model",       "Machine"),
        ("chip",        "Chip"),
        ("cores",       "Cores"),
        ("ram_gb",      "RAM (GB)"),
        ("device",      "Accelerator"),
        ("gpu",         "GPU"),
        ("vram_gb",     "VRAM (GB)"),
        ("os",          "OS"),
        ("ctranslate2", "CTranslate2"),
        ("python",      "Python"),
    ]:
        val = hw.get(key)
        if val:
            lines.append(f"| **{label}** | {val} |")
    return "\n".join(lines)


def write_system_pages(summaries, systems):
    (DOCS_DIR / "systems").mkdir(exist_ok=True)
    for sys_id in systems:
        meta = load_yaml(SYSTEMS_DIR / sys_id / "system.yaml")
        sys_summaries = [s for s in summaries if s["system"] == sys_id]
        rows = [
            f"| [{s['corpus']}](../corpora/{s['corpus']}.md) | {fmt_wer(s['overall_wer'])} | {s.get('rtf', '—')} |"
            for s in sys_summaries
        ]
        # Use hardware from the most recent run
        hw = next((s.get("hardware", {}) for s in reversed(sys_summaries)), {})
        hf = meta.get("hf_model_id", "")
        hf_link = f"[{hf}](https://huggingface.co/{hf})" if hf else "—"
        hw_section = _fmt_hardware(hw)
        content = f"""---
title: "{meta.get('name', sys_id)}"
---

# {meta.get('name', sys_id)}

| | |
|---|---|
| **HuggingFace** | {hf_link} |
| **Language** | {meta.get('language', '—')} |
| **Type** | {meta.get('type', '—')} |

{meta.get('description', '')}

## Results

| Corpus | WER | RTF |
|--------|-----|-----|
""" + "\n".join(rows) + f"\n\n{hw_section}\n"
        (DOCS_DIR / "systems" / f"{sys_id}.md").write_text(content)
        print(f"  wrote docs/systems/{sys_id}.md")


def main():
    summaries = collect_summaries()
    if not summaries:
        print("No results found — nothing to generate.")
        return

    systems, corpora, wer = build_matrix(summaries)
    print(f"Generating docs for {len(systems)} system(s), {len(corpora)} corpus/corpora...")
    write_index(systems, corpora, wer)
    write_corpus_index(corpora)
    write_system_index(systems)
    write_corpus_pages(summaries, corpora)
    write_system_pages(summaries, systems)
    print("Done.")


if __name__ == "__main__":
    main()
