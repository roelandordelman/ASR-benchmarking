"""
Detect hardware and runtime environment at benchmark time.
Returns a dict that gets stored in summary.json alongside WER and RTF.
"""
import json
import platform
import subprocess
import sys


def _macos_hardware() -> dict:
    try:
        raw = subprocess.check_output(
            ["system_profiler", "SPHardwareDataType", "-json"],
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(raw)["SPHardwareDataType"][0]
        cores_raw = data.get("number_processors", "")
        # "proc 14:10:4:0" → "14-core (10P+4E)"
        cores = _parse_cores(cores_raw)
        return {
            "model":   f"{data.get('machine_name', '')} ({data.get('machine_model', '')})",
            "chip":    data.get("chip_type") or data.get("cpu_type", ""),
            "cores":   cores,
            "ram_gb":  _parse_ram(data.get("physical_memory", "")),
        }
    except Exception:
        return {}


def _parse_ram(s: str) -> str:
    return s.split()[0] if s else ""


def _parse_cores(s: str) -> str:
    # "proc 14:10:4:0" → "14-core (10P+4E)"
    try:
        parts = s.replace("proc ", "").split(":")
        total, perf, eff = int(parts[0]), int(parts[1]), int(parts[2])
        if perf and eff:
            return f"{total}-core ({perf}P+{eff}E)"
        return f"{total}-core"
    except Exception:
        return s


def _accelerator() -> dict:
    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb  = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
            return {"device": device, "gpu": gpu_name, "vram_gb": vram_gb}
        if torch.backends.mps.is_available():
            device = "mps"
    except ImportError:
        pass
    return {"device": device}


def detect() -> dict:
    info: dict = {
        "os":     f"{platform.system()} {platform.release()}",
        "arch":   platform.machine(),
        "python": platform.python_version(),
    }

    if platform.system() == "Darwin":
        info.update(_macos_hardware())
    else:
        info["cpu"] = platform.processor()
        try:
            import psutil
            info["ram_gb"] = str(round(psutil.virtual_memory().total / 1e9))
        except ImportError:
            pass

    info.update(_accelerator())

    # faster-whisper / ctranslate2 version if available
    try:
        import ctranslate2
        info["ctranslate2"] = ctranslate2.__version__
    except ImportError:
        pass

    return info


if __name__ == "__main__":
    import pprint
    pprint.pprint(detect())
