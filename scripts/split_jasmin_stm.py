#!/usr/bin/env python3
"""
Split a Jasmin reference.stm into per-group STM files and create corpus directories.

Groups in jasmin_nl_compq:
  native_children, native_teens, nonnative_minors, nonnative_adults, native_elderly

Usage:
    python3 scripts/split_jasmin_stm.py

Creates:
    corpora/jasmin_nl_compq_<group>/corpus.yaml
    corpora/jasmin_nl_compq_<group>/reference.stm
"""
from pathlib import Path
import yaml

SOURCE_STM   = Path("corpora/jasmin_nl_compq/reference.stm")
SOURCE_YAML  = Path("corpora/jasmin_nl_compq/corpus.yaml")
CORPORA_DIR  = Path("corpora")

GROUPS = {
    "native_children":   "Native Children",
    "native_teens":      "Native Teenagers",
    "nonnative_minors":  "Non-native Minors",
    "nonnative_adults":  "Non-native Adults",
    "native_elderly":    "Native Elderly",
}


def main():
    with open(SOURCE_YAML) as f:
        base_meta = yaml.safe_load(f)

    lines = SOURCE_STM.read_text().splitlines(keepends=True)

    for group_id, group_name in GROUPS.items():
        corpus_id = f"jasmin_nl_compq_{group_id}"
        corpus_dir = CORPORA_DIR / corpus_id
        corpus_dir.mkdir(exist_ok=True)

        # Filter STM lines for this group
        group_lines = [l for l in lines if f",{group_id}," in l or l.startswith(";;")]
        stm_path = corpus_dir / "reference.stm"
        stm_path.write_text("".join(group_lines))

        # Calculate total speech duration from STM
        total_s = 0.0
        n_segments = 0
        for l in group_lines:
            if l.startswith(";;"):
                continue
            parts = l.split()
            if len(parts) >= 5:
                try:
                    total_s += float(parts[4]) - float(parts[3])
                    n_segments += 1
                except ValueError:
                    pass
        size_hours = round(total_s / 3600, 2)
        print(f"  {corpus_id}: {n_segments} segments, {size_hours}h → {stm_path}")

        # Write corpus.yaml
        meta = {
            "id":          corpus_id,
            "name":        f"Jasmin NL comp-q — {group_name}",
            "description": (
                f"Jasmin corpus, read speech component (comp-q), Dutch, {group_name} subset. "
                f"Subset of jasmin_nl_compq."
            ),
            "language":    base_meta.get("language", "nl"),
            "domain":      base_meta.get("domain", "read_speech"),
            "license":     base_meta.get("license", "restricted"),
            "access":      base_meta.get("access", "request"),
            "contact":     base_meta.get("contact", ""),
            "size_hours":  size_hours,
            "segment_audio": True,
            "audio_corpus": "jasmin_nl_compq",  # shared audio directory
        }
        if base_meta.get("sftp"):
            meta["sftp"] = base_meta["sftp"]
        if base_meta.get("reference"):
            meta["reference"] = base_meta["reference"]

        yaml_path = corpus_dir / "corpus.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(meta, f, allow_unicode=True, sort_keys=False)
        print(f"  wrote {yaml_path}")

    print("\nDone. Run orchestrate.py with --corpus jasmin_nl_compq_<group> to benchmark each group.")


if __name__ == "__main__":
    main()
