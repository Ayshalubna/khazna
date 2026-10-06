"""Hugging Face Space entry point (free tier).

Fetches Khazna from GitHub, downloads the small open model (Qwen2.5-1.5B-Instruct) once, loads it into this
process, switches on the egress guard, then serves the FastAPI web app on port 7860. After start-up the process
cannot open any connection outside the container: questions and documents never leave it.
Gradio itself is not used; the Space only needs a process listening on 7860.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/Ayshalubna/khazna.git"
SRC = Path.home() / "khazna-src"

os.environ.setdefault("KHAZNA_DB", "/tmp/khazna_audit.db")
os.environ.setdefault("KHAZNA_LLM", "transformers")
os.environ.setdefault("KHAZNA_EGRESS_GUARD", "1")
os.environ.setdefault("OMP_NUM_THREADS", str(os.cpu_count() or 2))

if not (SRC / "khazna").exists():
    subprocess.run(["git", "clone", "--depth", "1", REPO, str(SRC)], check=True)

os.chdir(SRC)
sys.path.insert(0, str(SRC))

if os.environ["KHAZNA_LLM"] == "transformers":
    try:
        from huggingface_hub import snapshot_download

        model = os.getenv("KHAZNA_HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
        snapshot_download(model, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "merges.txt"])
        os.environ["HF_HUB_OFFLINE"] = "1"          # from here on, nothing is fetched from the internet
    except Exception as e:                          # never leave the demo down: fall back to verified quotes
        print(f"model download failed ({e}); using built-in quoting", flush=True)
        os.environ["KHAZNA_LLM"] = "extractive"

import spaces  # noqa: E402
import uvicorn  # noqa: E402


@spaces.GPU
def _gpu_placeholder():
    """The free ZeroGPU tier requires one GPU-decorated function; Khazna runs entirely on CPU."""
    return None


# ZeroGPU normally reports readiness when a Gradio app launches; we serve FastAPI directly, so report it ourselves.
from spaces.config import Config as _SpacesConfig  # noqa: E402

if _SpacesConfig.zero_gpu:
    from spaces import zero as _zero

    _zero.startup()

from khazna.api import api  # noqa: E402

uvicorn.run(api, host="0.0.0.0", port=int(os.getenv("PORT", "7860")),
            proxy_headers=True, forwarded_allow_ips="*", timeout_keep_alive=30)
