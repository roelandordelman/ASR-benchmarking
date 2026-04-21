#!/usr/bin/env python3
"""
System compatibility check for ASR benchmarking.
Checks Python, Docker, ffmpeg, faster-whisper, GPU, and RAM.
Generates a human-readable report with a usability verdict.

Usage:
    python3 scripts/check_system.py
"""
import platform
import shutil
import subprocess
import sys


def header(title):
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print(f"{'=' * 55}")


def ok(msg):   print(f"  ✓  {msg}")
def warn(msg): print(f"  ⚠  {msg}")
def fail(msg): print(f"  ✗  {msg}")
def info(msg): print(f"     {msg}")


# ── Python ────────────────────────────────────────────────
def check_python():
    header("Python")
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if v.major == 3 and v.minor >= 9:
        ok(f"Python {ver}")
        return True
    else:
        fail(f"Python {ver} — need 3.9+")
        return False


# ── Docker ────────────────────────────────────────────────
def check_docker():
    header("Docker (required for eval)")
    if not shutil.which("docker"):
        fail("docker not found — install: apt install docker.io  /  brew install docker")
        return False
    try:
        r = subprocess.run(
            ["docker", "run", "--rm", "hello-world"],
            capture_output=True, text=True, timeout=30
        )
        if "Hello from Docker" in r.stdout:
            ok("Docker installed and daemon running")
            return True
        else:
            fail("Docker installed but daemon not running — start Docker Desktop or: sudo systemctl start docker")
            return False
    except Exception as e:
        fail(f"Docker error: {e}")
        return False


# ── ffmpeg ────────────────────────────────────────────────
def check_ffmpeg():
    header("ffmpeg (required for audio segmentation)")
    if not shutil.which("ffmpeg"):
        fail("ffmpeg not found — install: apt install ffmpeg  /  brew install ffmpeg")
        return False
    r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    ver = r.stdout.splitlines()[0] if r.stdout else "unknown"
    ok(ver)
    return True


# ── Python packages ───────────────────────────────────────
def check_packages():
    header("Python packages")
    all_ok = True
    packages = [
        ("faster_whisper", "faster-whisper", True),
        ("pandas",         "pandas",         True),
        ("yaml",           "pyyaml",         True),
        ("paramiko",       "paramiko",       False),
        ("torch",          "torch",          False),
    ]
    for mod, pkg, required in packages:
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "?")
            ok(f"{pkg} {ver}")
        except ImportError:
            if required:
                fail(f"{pkg} not installed — pip3 install {pkg}")
                all_ok = False
            else:
                warn(f"{pkg} not installed (optional) — pip3 install {pkg}")
    return all_ok


# ── GPU ───────────────────────────────────────────────────
def check_gpu():
    header("GPU / Accelerator")
    score = 0

    # CUDA via torch
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                p = torch.cuda.get_device_properties(i)
                vram = round(p.total_memory / 1e9, 1)
                ok(f"CUDA GPU {i}: {p.name} — {vram} GB VRAM")
                if vram >= 10:
                    score = 3
                elif vram >= 6:
                    score = 2
                else:
                    score = 1
        else:
            warn("torch installed but CUDA not available")
    except ImportError:
        pass

    # Apple Silicon MPS
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        ok("Apple Silicon (M-series) — Metal/AMX acceleration available")
        score = max(score, 2)

    # nvidia-smi fallback
    if score == 0 and shutil.which("nvidia-smi"):
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                            "--format=csv,noheader"], capture_output=True, text=True)
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                ok(f"nvidia-smi: {line.strip()}")
            score = 2

    if score == 0:
        warn("No GPU detected — ASR will run on CPU (slow for large models)")

    return score


# ── RAM ───────────────────────────────────────────────────
def check_ram():
    header("Memory")
    try:
        import psutil
        total = psutil.virtual_memory().total / 1e9
        available = psutil.virtual_memory().available / 1e9
        ok(f"RAM: {total:.0f} GB total, {available:.0f} GB available")
        return total
    except ImportError:
        pass

    # Fallback: /proc/meminfo on Linux
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    gb = kb / 1e6
                    ok(f"RAM: {gb:.0f} GB total")
                    return gb
    except Exception:
        pass

    # macOS fallback
    if platform.system() == "Darwin":
        r = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
        if r.returncode == 0:
            gb = int(r.stdout.strip()) / 1e9
            ok(f"RAM: {gb:.0f} GB total")
            return gb

    warn("Could not determine RAM — install psutil: pip3 install psutil")
    return 0


# ── CPU ───────────────────────────────────────────────────
def check_cpu():
    header("CPU")
    cpu = platform.processor() or "unknown"
    cores = None
    try:
        import psutil
        cores = psutil.cpu_count(logical=False)
        threads = psutil.cpu_count(logical=True)
        ok(f"{cpu}")
        ok(f"{cores} physical cores, {threads} threads")
    except ImportError:
        ok(f"{cpu}")
    return cores or 1


# ── Verdict ───────────────────────────────────────────────
def verdict(py_ok, docker_ok, ffmpeg_ok, pkg_ok, gpu_score, ram_gb, cpu_cores):
    header("Verdict")

    issues = []
    if not py_ok:      issues.append("Python 3.9+ required")
    if not docker_ok:  issues.append("Docker required for evaluation")
    if not ffmpeg_ok:  issues.append("ffmpeg required for audio segmentation")
    if not pkg_ok:     issues.append("Missing required Python packages")

    if issues:
        fail("NOT READY — fix the following:")
        for i in issues:
            info(f"→ {i}")
        print()
        return

    if gpu_score >= 3:
        rating = "EXCELLENT"
        note = "Large models (Whisper large-v3, Parakeet) will run fast."
    elif gpu_score == 2:
        rating = "GOOD"
        note = "Large models will run at reasonable speed."
    elif gpu_score == 1:
        rating = "FAIR"
        note = "GPU available but limited VRAM — use turbo or medium models."
    else:
        if ram_gb >= 32:
            rating = "LIMITED (CPU only)"
            note = "No GPU — large models will be very slow. Suitable for eval-only (--skip-asr) or small models."
        else:
            rating = "POOR"
            note = "No GPU and limited RAM — not practical for large ASR models."

    print(f"\n  Rating: {rating}")
    info(note)

    print("\n  Estimated RTF for Whisper large-v3 (rough guide):")
    if gpu_score >= 3:
        info("  ~0.1–0.2x  (GPU, 10+ GB VRAM)")
    elif gpu_score == 2:
        info("  ~0.2–0.5x  (GPU / Apple Silicon)")
    elif gpu_score == 1:
        info("  ~0.5–1.0x  (low VRAM GPU)")
    else:
        info(f"  ~3–10x     (CPU, {cpu_cores} cores) — 21h Jasmin corpus = days")

    print()


# ── Main ──────────────────────────────────────────────────
def main():
    print("\nASR Benchmark — System Compatibility Check")
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")

    py_ok     = check_python()
    docker_ok = check_docker()
    ffmpeg_ok = check_ffmpeg()
    pkg_ok    = check_packages()
    gpu_score = check_gpu()
    ram_gb    = check_ram()
    cpu_cores = check_cpu()

    verdict(py_ok, docker_ok, ffmpeg_ok, pkg_ok, gpu_score, ram_gb, cpu_cores)


if __name__ == "__main__":
    main()
