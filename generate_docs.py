#!/usr/bin/env python3
"""
Generate docs/ markdown from results/*/summary.json files.

Produces:
  docs/index.md              — grouped WER matrix (HTML table)
  docs/datasets/index.md     — list of datasets
  docs/datasets/{id}.md      — dataset overview page
  docs/corpora/index.md      — flat list of corpora
  docs/corpora/{id}.md       — corpus / component / speech-class page
  docs/systems/index.md      — list of systems
  docs/systems/{id}.md       — system detail page

Run automatically by orchestrate.py after new results, or manually:
    python generate_docs.py
"""
import json
from datetime import datetime
from pathlib import Path

import yaml

RESULTS_DIR  = Path("results")
DOCS_DIR     = Path("docs")
CORPORA_DIR  = Path("corpora")
SYSTEMS_DIR  = Path("systems")
DATASETS_DIR = Path("datasets")


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def fmt_wer(v: float) -> str:
    return f"{v:.1f}%"


def collect_summaries() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(RESULTS_DIR.glob("*/*/summary.json"))]


def load_datasets() -> dict:
    """Load all dataset yamls, keyed by id, ordered by display_order."""
    datasets = {}
    for p in sorted(DATASETS_DIR.glob("*/dataset.yaml")):
        meta = load_yaml(p)
        if meta.get("id"):
            datasets[meta["id"]] = meta
    return datasets


def load_corpora() -> dict:
    """Load all corpus yamls, keyed by id."""
    corpora = {}
    for p in CORPORA_DIR.glob("*/corpus.yaml"):
        meta = load_yaml(p)
        if meta.get("id"):
            corpora[meta["id"]] = meta
    return corpora


def load_system_metas() -> dict:
    """Load all system yamls, keyed by id."""
    metas = {}
    for p in SYSTEMS_DIR.glob("*/system.yaml"):
        meta = load_yaml(p)
        if meta.get("id"):
            metas[meta["id"]] = meta
    return metas


def system_matrix_label(sys_meta: dict) -> str:
    """Label for WER matrix row header: name + compute type if known."""
    name = sys_meta.get("name", sys_meta.get("id", "?"))
    ct = (sys_meta.get("config") or {}).get("compute_type")
    if ct:
        return f"{name} ({ct})"
    return name


def matrix_label(corpus_meta: dict) -> str:
    """Short label for the WER matrix column header."""
    if corpus_meta.get("matrix_label"):
        return corpus_meta["matrix_label"]
    name = corpus_meta.get("name", corpus_meta.get("id", "?"))
    # Strip trailing parenthetical, e.g. " (read speech)" → ""
    if " (" in name:
        name = name[: name.index(" (")]
    return name


# ── Matrix layout ─────────────────────────────────────────────────────────────

def build_grouped_layout(summaries, corpora, datasets):
    """
    Returns:
      systems        — sorted list of system ids that appear in any result
      dataset_groups — list of (dataset_id | None, [corpus_id, ...])
      wer            — {(sys_id, corpus_id): wer_float}
    """
    wer = {(s["system"], s["corpus"]): s["overall_wer"] for s in summaries}
    active = {s["corpus"] for s in summaries
              if not corpora.get(s["corpus"], {}).get("exclude_from_matrix")}
    systems = sorted({s["system"] for s in summaries})

    ordered_ds = sorted(datasets.values(), key=lambda d: d.get("display_order", 99))
    dataset_groups = []
    assigned: set[str] = set()

    for ds in ordered_ds:
        corpus_ids = [c for c in ds.get("corpus_order", []) if c in active]
        if corpus_ids:
            dataset_groups.append((ds["id"], corpus_ids))
            assigned.update(corpus_ids)

    unassigned = sorted(active - assigned)
    if unassigned:
        dataset_groups.append((None, unassigned))

    return systems, dataset_groups, wer


# ── Index (grouped HTML table) ────────────────────────────────────────────────

def write_index(systems, dataset_groups, wer, corpora, datasets, system_metas):
    """Write docs/index.md with an HTML grouped WER table."""

    header1 = ['<th rowspan="2" style="text-align:left">System</th>']
    header2 = []
    all_corpus_ids: list[str] = []

    for ds_id, corpus_ids in dataset_groups:
        n = len(corpus_ids)
        if ds_id and ds_id in datasets:
            ds_name = datasets[ds_id].get("name", ds_id)
            label = f'<a href="datasets/{ds_id}.md">{ds_name}</a>'
        else:
            label = "Other"
        header1.append(f'<th colspan="{n}" style="text-align:center">{label}</th>')
        for cid in corpus_ids:
            cm = corpora.get(cid, {"id": cid})
            lbl = matrix_label(cm)
            header2.append(
                f'<th style="text-align:center"><a href="corpora/{cid}.md">{lbl}</a></th>'
            )
            all_corpus_ids.append(cid)

    rows = []
    for sys_id in systems:
        sm = system_metas.get(sys_id, {})
        sys_label = system_matrix_label(sm)
        cells = [f'<td><a href="systems/{sys_id}.md">{sys_label}</a></td>']
        for cid in all_corpus_ids:
            v = wer.get((sys_id, cid))
            cells.append(
                f'<td style="text-align:center">{fmt_wer(v) if v is not None else "—"}</td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    table = (
        "<table>\n<thead>\n"
        f"<tr>{''.join(header1)}</tr>\n"
        f"<tr>{''.join(header2)}</tr>\n"
        "</thead>\n<tbody>\n"
        + "\n".join(rows)
        + "\n</tbody>\n</table>"
    )

    content = f"""---
title: ASR NL Benchmark Results
---

# Dutch ASR Benchmark — WER Matrix

*Lower is better. Generated {datetime.now().strftime('%Y-%m-%d')}.*

{table}

> **Note on quantization:** compute type (e.g. int8 vs float16) materially affects WER —
> typically 2–4 points on challenging speech. It is shown in the System column for each entry.
> See individual [system pages](systems/) for the full inference configuration.

---

Browse details by [dataset](datasets/) or [system](systems/).
"""
    (DOCS_DIR / "index.md").write_text(content)
    print("  wrote docs/index.md")


# ── Index pages ───────────────────────────────────────────────────────────────

def write_dataset_index(datasets):
    (DOCS_DIR / "datasets").mkdir(exist_ok=True)
    items = []
    for ds_id, ds in sorted(datasets.items(), key=lambda x: x[1].get("display_order", 99)):
        items.append(f"- [{ds.get('name', ds_id)}]({ds_id}.md)")
    (DOCS_DIR / "datasets" / "index.md").write_text(
        "---\ntitle: Datasets\n---\n\n# Datasets\n\n" + "\n".join(items) + "\n"
    )
    print("  wrote docs/datasets/index.md")


def write_corpus_index(active_corpora, corpora):
    items = []
    for cid in sorted(active_corpora):
        cm = corpora.get(cid, {})
        items.append(f"- [{cm.get('name', cid)}]({cid}.md)")
    (DOCS_DIR / "corpora" / "index.md").write_text(
        "---\ntitle: Corpora\n---\n\n# Corpora\n\n" + "\n".join(items) + "\n"
    )
    print("  wrote docs/corpora/index.md")


def write_system_index(system_ids, system_metas):
    items = "\n".join(
        f"- [{system_metas.get(s, {}).get('name', s)}]({s}.md)"
        for s in sorted(system_ids)
    )
    (DOCS_DIR / "systems" / "index.md").write_text(
        "---\ntitle: Systems\n---\n\n# Systems\n\n" + items + "\n"
    )
    print("  wrote docs/systems/index.md")


# ── Dataset pages ─────────────────────────────────────────────────────────────

def write_dataset_pages(datasets, corpora, summaries):
    (DOCS_DIR / "datasets").mkdir(exist_ok=True)
    wer = {(s["system"], s["corpus"]): s["overall_wer"] for s in summaries}
    systems = sorted({s["system"] for s in summaries})
    active = {s["corpus"] for s in summaries}
    sys_metas = load_system_metas()

    for ds_id, ds in datasets.items():
        ds_corpora = [c for c in ds.get("corpus_order", []) if c in active]

        # Results table: corpora as columns, systems as rows
        if ds_corpora and systems:
            col_hdrs = " | ".join(
                f"[{matrix_label(corpora.get(c, {'id': c}))}](../corpora/{c}.md)"
                for c in ds_corpora
            )
            sep = "|".join(["---"] * (len(ds_corpora) + 1))
            result_rows = []
            for sys_id in systems:
                cells = [
                    fmt_wer(wer[(sys_id, c)]) if (sys_id, c) in wer else "—"
                    for c in ds_corpora
                ]
                sys_label = system_matrix_label(sys_metas.get(sys_id, {}))
                result_rows.append(
                    f"| [{sys_label}](../systems/{sys_id}.md) | " + " | ".join(cells) + " |"
                )
            results_section = (
                f"## Results\n\n| System | {col_hdrs} |\n|{sep}|\n"
                + "\n".join(result_rows)
            )
        else:
            results_section = "*No results yet.*"

        # Corpora / components table
        corpus_rows = []
        for cid in ds.get("corpus_order", []):
            cm = corpora.get(cid, {})
            if not cm:
                continue
            hours = cm.get("size_hours", "?")
            domain = cm.get("domain", "—").replace("_", " ")
            parent = cm.get("parent_corpus", "")
            indent = "↳ " if parent else ""
            corpus_rows.append(
                f"| {indent}[{cm.get('name', cid)}](../corpora/{cid}.md) | {hours}h | {domain} |"
            )

        corpora_section = ""
        if corpus_rows:
            corpora_section = (
                "## Corpora\n\n| Name | Size | Domain |\n|---|---|---|\n"
                + "\n".join(corpus_rows)
            )

        ref = ds.get("reference", "")
        ref_line = f"\n**Reference:** {ref}\n" if ref else ""
        url = ds.get("url", "")
        url_line = f"**Website:** [{url}]({url})\n\n" if url else ""

        content = f"""---
title: "{ds.get('name', ds_id)}"
---

[Datasets](index.md)

# {ds.get('full_name', ds.get('name', ds_id))}

{ds.get('description', '').strip()}

{url_line}| | |
|---|---|
| **Language** | {ds.get('language', 'nl')} |
| **License** | {ds.get('license', '—')} |
{ref_line}
{corpora_section}

{results_section}
"""
        (DOCS_DIR / "datasets" / f"{ds_id}.md").write_text(content)
        print(f"  wrote docs/datasets/{ds_id}.md")


# ── Corpus pages ──────────────────────────────────────────────────────────────

def write_corpus_pages(summaries, corpora, datasets):
    (DOCS_DIR / "corpora").mkdir(exist_ok=True)
    wer = {(s["system"], s["corpus"]): s["overall_wer"] for s in summaries}
    systems = sorted({s["system"] for s in summaries})
    active = {s["corpus"] for s in summaries}
    sys_metas = load_system_metas()

    # Also write pages for parent corpora that act as component index pages
    parent_ids = {cm.get("parent_corpus") for cm in corpora.values() if cm.get("parent_corpus")}
    pages_to_write = active | parent_ids

    for corpus_id in sorted(pages_to_write):
        cm = corpora.get(corpus_id, {"id": corpus_id, "name": corpus_id})

        # Breadcrumb
        crumbs = ["[Datasets](../datasets/)"]
        ds_id = cm.get("dataset")
        if ds_id and ds_id in datasets:
            ds_name = datasets[ds_id].get("name", ds_id)
            crumbs.append(f"[{ds_name}](../datasets/{ds_id}.md)")
        parent_id = cm.get("parent_corpus")
        if parent_id and parent_id in corpora:
            pm = corpora[parent_id]
            crumbs.append(f"[{pm.get('name', parent_id)}]({parent_id}.md)")
        breadcrumb = " › ".join(crumbs)

        # Results table (direct results on this corpus)
        if corpus_id in active:
            result_rows = [
                f"| [{system_matrix_label(sys_metas.get(sid, {}))}](../systems/{sid}.md)"
                f" | {fmt_wer(wer[(sid, corpus_id)])} |"
                for sid in systems
                if (sid, corpus_id) in wer
            ]
            results_section = (
                "## Results\n\n| System | WER |\n|--------|-----|\n"
                + "\n".join(result_rows)
            )
        else:
            results_section = ""

        # Sub-corpora (children of this corpus)
        children = sorted(
            [cid for cid, cm2 in corpora.items() if cm2.get("parent_corpus") == corpus_id]
        )
        if children:
            child_rows = []
            for cid in children:
                ccm = corpora[cid]
                best_wer = min(
                    (wer[(sid, cid)] for sid in systems if (sid, cid) in wer),
                    default=None,
                )
                best_str = fmt_wer(best_wer) if best_wer is not None else "—"
                child_rows.append(
                    f"| [{ccm.get('name', cid)}]({cid}.md)"
                    f" | {ccm.get('size_hours', '?')}h"
                    f" | {best_str} |"
                )
            sub_section = (
                "## Sub-corpora\n\n| Name | Size | Best WER |\n|---|---|---|\n"
                + "\n".join(child_rows)
            )
        else:
            sub_section = ""

        desc = str(cm.get("description", "")).strip()
        ref = cm.get("reference", "")
        ref_line = f"\n**Reference:** {ref}\n" if ref else ""

        size_hours = cm.get("size_hours", "—")
        domain = str(cm.get("domain", "—")).replace("_", " ")

        content = f"""---
title: "{cm.get('name', corpus_id)}"
---

{breadcrumb}

# {cm.get('name', corpus_id)}

| | |
|---|---|
| **Domain** | {domain} |
| **Language** | {cm.get('language', '—')} |
| **Size** | {size_hours} hours |
| **License** | {cm.get('license', '—')} |

{desc}
{ref_line}
{sub_section}

{results_section}
"""
        (DOCS_DIR / "corpora" / f"{corpus_id}.md").write_text(content)
        print(f"  wrote docs/corpora/{corpus_id}.md")


# ── System pages ──────────────────────────────────────────────────────────────

def _fmt_config(cfg: dict) -> str:
    if not cfg:
        return ""
    labels = [
        ("library",                  "Inference library"),
        ("compute_type",             "Compute type"),
        ("device",                   "Device"),
        ("beam_size",                "Beam size"),
        ("vad_filter",               "VAD filter"),
        ("condition_on_previous_text", "Condition on prev. text"),
        ("word_timestamps",          "Word timestamps"),
        ("language",                 "Language hint"),
    ]
    lines = ["## Configuration\n\n| | |", "|---|---|"]
    for key, label in labels:
        val = cfg.get(key)
        if val is not None:
            lines.append(f"| **{label}** | {val} |")
    return "\n".join(lines)


def _fmt_hardware(hw: dict) -> str:
    if not hw:
        return ""
    lines = ["## Hardware\n\n| | |", "|---|---|"]
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


def write_system_pages(summaries, system_metas, corpora):
    (DOCS_DIR / "systems").mkdir(exist_ok=True)
    system_ids = sorted({s["system"] for s in summaries})

    for sys_id in system_ids:
        sm = system_metas.get(sys_id, {})
        sys_summaries = [s for s in summaries if s["system"] == sys_id]

        rows = [
            f"| [{corpora.get(s['corpus'], {}).get('name', s['corpus'])}]"
            f"(../corpora/{s['corpus']}.md)"
            f" | {fmt_wer(s['overall_wer'])} |"
            for s in sorted(sys_summaries, key=lambda x: x["corpus"])
        ]

        hw = next((s.get("hardware", {}) for s in reversed(sys_summaries)), {})
        hf = sm.get("hf_model_id", "")
        hf_link = f"[{hf}](https://huggingface.co/{hf})" if hf else "—"
        cfg_section = _fmt_config(sm.get("config", {}))
        hw_section = _fmt_hardware(hw)

        content = f"""---
title: "{sm.get('name', sys_id)}"
---

[Systems](index.md)

# {sm.get('name', sys_id)}

| | |
|---|---|
| **HuggingFace** | {hf_link} |
| **Language** | {sm.get('language', '—')} |
| **Type** | {sm.get('type', '—')} |

{sm.get('description', '').strip()}

## Results

| Corpus | WER |
|--------|-----|
{"".join(rows)}

{cfg_section}

{hw_section}
"""
        (DOCS_DIR / "systems" / f"{sys_id}.md").write_text(content)
        print(f"  wrote docs/systems/{sys_id}.md")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    summaries = collect_summaries()
    if not summaries:
        print("No results found — nothing to generate.")
        return

    datasets    = load_datasets()
    corpora     = load_corpora()
    sys_metas   = load_system_metas()
    systems, dataset_groups, wer = build_grouped_layout(summaries, corpora, datasets)
    active      = {s["corpus"] for s in summaries}

    print(
        f"Generating docs for {len(systems)} system(s), "
        f"{len(active)} corpus/corpora, "
        f"{len(datasets)} dataset(s)..."
    )

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "datasets").mkdir(exist_ok=True)
    (DOCS_DIR / "corpora").mkdir(exist_ok=True)
    (DOCS_DIR / "systems").mkdir(exist_ok=True)

    write_index(systems, dataset_groups, wer, corpora, datasets, sys_metas)
    write_dataset_index(datasets)
    write_corpus_index(active, corpora)
    write_system_index(systems, sys_metas)
    write_dataset_pages(datasets, corpora, summaries)
    write_corpus_pages(summaries, corpora, datasets)
    write_system_pages(summaries, sys_metas, corpora)
    print("Done.")


if __name__ == "__main__":
    main()
