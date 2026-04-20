#!/usr/bin/env python3
"""
Download corpus audio from Hetzner Storage Box via SFTP.

Usage:
    python3 scripts/fetch_corpus.py nbest2008
    python3 scripts/fetch_corpus.py nbest2008 --list      # list remote files only
    python3 scripts/fetch_corpus.py nbest2008 --force     # re-download even if local copy exists

Access:
    Requires SSH key access to the Storage Box. Set via env var or ~/.ssh/config:
        ASR_SFTP_KEY   path to private key (default: ~/.ssh/id_hetzner_rclone)

    To request access, contact the corpus maintainer listed in corpus.yaml.
"""
import argparse
import os
import sys
from pathlib import Path

import yaml

CORPORA_DIR = Path("corpora")
DEFAULT_KEY = Path.home() / ".ssh" / "id_hetzner_rclone"


def load_corpus(corpus_id: str) -> dict:
    path = CORPORA_DIR / corpus_id / "corpus.yaml"
    if not path.exists():
        sys.exit(f"Corpus not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def get_sftp_client(host: str, port: int, user: str, key_file: Path):
    try:
        import paramiko
    except ImportError:
        sys.exit("paramiko not installed — run: pip3 install paramiko")

    key = paramiko.Ed25519Key.from_private_key_file(str(key_file))
    transport = paramiko.Transport((host, port))
    transport.connect(username=user, pkey=key)
    return paramiko.SFTPClient.from_transport(transport), transport


def fetch(corpus_id: str, force: bool = False, list_only: bool = False):
    meta = load_corpus(corpus_id)

    sftp_conf = meta.get("sftp")
    if not sftp_conf:
        sys.exit(f"No sftp config in {corpus_id}/corpus.yaml")

    host = sftp_conf["host"]
    port = sftp_conf.get("port", 23)
    user = sftp_conf["user"]
    remote_path = sftp_conf["path"]

    key_file = Path(os.getenv("ASR_SFTP_KEY", str(DEFAULT_KEY)))
    if not key_file.exists():
        sys.exit(
            f"SSH key not found: {key_file}\n"
            f"Set ASR_SFTP_KEY or contact {meta.get('contact', 'the corpus maintainer')} for access."
        )

    corpus_root = Path(os.getenv("ASR_CORPUS_ROOT", "corpora"))
    local_audio = corpus_root / corpus_id / "audio"

    print(f"Connecting to {user}@{host}:{port} ...")
    sftp, transport = get_sftp_client(host, port, user, key_file)

    try:
        remote_files = sftp.listdir(remote_path)
        audio_files = sorted(f for f in remote_files if f.endswith((".wav", ".mp3", ".flac")))

        if list_only:
            print(f"\nRemote files in {remote_path}:")
            for f in audio_files:
                attr = sftp.stat(f"{remote_path}/{f}")
                print(f"  {f}  ({attr.st_size / 1e6:.1f} MB)")
            return

        local_audio.mkdir(parents=True, exist_ok=True)
        to_fetch = []
        for f in audio_files:
            local_f = local_audio / f
            if force or not local_f.exists():
                to_fetch.append(f)
            else:
                remote_size = sftp.stat(f"{remote_path}/{f}").st_size
                if local_f.stat().st_size != remote_size:
                    to_fetch.append(f)

        if not to_fetch:
            print(f"All {len(audio_files)} files already present in {local_audio}")
            return

        print(f"Fetching {len(to_fetch)}/{len(audio_files)} files to {local_audio} ...")
        for i, f in enumerate(to_fetch, 1):
            remote_f = f"{remote_path}/{f}"
            local_f = local_audio / f
            size_mb = sftp.stat(remote_f).st_size / 1e6
            print(f"  [{i}/{len(to_fetch)}] {f} ({size_mb:.1f} MB)")
            sftp.get(remote_f, str(local_f))

        print(f"\nDone. {len(to_fetch)} file(s) downloaded to {local_audio}")

    finally:
        sftp.close()
        transport.close()


def main():
    parser = argparse.ArgumentParser(description="Fetch corpus audio from Hetzner Storage Box")
    parser.add_argument("corpus_id", help="Corpus id (matches corpora/ directory name)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    parser.add_argument("--list", action="store_true", dest="list_only", help="List remote files only")
    args = parser.parse_args()
    fetch(args.corpus_id, force=args.force, list_only=args.list_only)


if __name__ == "__main__":
    main()
