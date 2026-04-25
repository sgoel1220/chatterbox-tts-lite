"""Download models and LoRAs from CivitAI / HuggingFace at container startup.

Environment variables
---------------------
CIVITAI_TOKEN          Your CivitAI API token (required for CivitAI downloads).

BASE_CIVITAI_ID        CivitAI *version* ID for the base checkpoint.
                       e.g. "456194" for Juggernaut XL Ragnarok.
                       Skipped if BASE_MODEL_PATH already exists.

BASE_HF_REPO           HuggingFace repo to fall back to when no CivitAI ID
                       is given (default: stabilityai/stable-diffusion-xl-base-1.0).
                       The server's BASE_MODEL_ID env var handles this — no need
                       to set BASE_HF_REPO separately unless you want a different HF model.

LORA_CIVITAI_IDS       Comma-separated  name:version_id  pairs.
                       e.g. "ClassipeintXL_v2.1:12345,Eldritch_Impressionism:67890"

LORA_HF_REPOS          Comma-separated  name:repo/path  pairs for HuggingFace LoRAs.
                       e.g. "my-lora:user/repo/lora.safetensors"

Destination paths
-----------------
Base model  → /models/base.safetensors   (BASE_MODEL_PATH is set to this)
LoRAs       → /loras/<name>.safetensors
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

CIVITAI_TOKEN = os.getenv("CIVITAI_TOKEN", "")
CIVITAI_DL = "https://civitai.com/api/download/models/{id}"

MODELS_DIR = Path("/models")
LORAS_DIR = Path(os.getenv("LORAS_DIR", "/loras"))
BASE_PATH = MODELS_DIR / "base.safetensors"

CHUNK = 8 * 1024 * 1024  # 8 MB


def _download(url: str, dest: Path, label: str) -> None:
    if dest.exists():
        print(f"  [skip] {label} already at {dest}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    headers = {}
    if "civitai.com" in url and CIVITAI_TOKEN:
        headers["Authorization"] = f"Bearer {CIVITAI_TOKEN}"
    # Public CivitAI models work without a token — CIVITAI_TOKEN is optional

    print(f"  [download] {label} → {dest}")
    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=CHUNK):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        gb = downloaded / 1024**3
                        print(f"    {pct:.1f}%  {gb:.2f} GB", end="\r", flush=True)
        tmp.rename(dest)
        print(f"\n  [done] {label} ({dest.stat().st_size / 1024**3:.2f} GB)")
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        print(f"\n  [error] {label}: {exc}", file=sys.stderr)
        raise


def _civitai_url(version_id: str) -> str:
    url = CIVITAI_DL.format(id=version_id.strip())
    if CIVITAI_TOKEN:
        url += f"?token={CIVITAI_TOKEN}"
    return url
    # No token = public download (works for most models)


def _hf_url(repo_path: str) -> str:
    # repo_path: "user/repo/path/to/file.safetensors"
    # or         "user/repo" (downloads model_index.json — not useful for single files)
    parts = repo_path.split("/", 2)
    if len(parts) < 3:
        raise ValueError(f"HF path must be 'owner/repo/filename', got: {repo_path}")
    owner, repo, filename = parts[0], parts[1], parts[2]
    token_param = f"?token={os.getenv('HF_TOKEN')}" if os.getenv("HF_TOKEN") else ""
    return f"https://huggingface.co/{owner}/{repo}/resolve/main/{filename}{token_param}"


def main() -> None:
    print("=== Startup download ===")

    # ── Base checkpoint ──────────────────────────────────────────────────────
    civitai_base = os.getenv("BASE_CIVITAI_ID", "").strip()
    if civitai_base:
        _download(_civitai_url(civitai_base), BASE_PATH, "base model (CivitAI)")
        # Tell the server to use this file
        os.environ["BASE_MODEL_PATH"] = str(BASE_PATH)
        # Write to a file so start.sh can export it to the uvicorn process
        Path("/tmp/env_extra").write_text(f"BASE_MODEL_PATH={BASE_PATH}\n")
    else:
        print("  [skip] BASE_CIVITAI_ID not set — server will use BASE_MODEL_ID (HuggingFace)")

    # ── CivitAI LoRAs ────────────────────────────────────────────────────────
    lora_ids_raw = os.getenv("LORA_CIVITAI_IDS", "").strip()
    if lora_ids_raw:
        for entry in lora_ids_raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" not in entry:
                print(f"  [warn] bad LORA_CIVITAI_IDS entry (expected name:id): {entry}", file=sys.stderr)
                continue
            name, version_id = entry.split(":", 1)
            dest = LORAS_DIR / f"{name.strip()}.safetensors"
            _download(_civitai_url(version_id.strip()), dest, f"LoRA {name} (CivitAI)")

    # ── HuggingFace LoRAs ────────────────────────────────────────────────────
    lora_hf_raw = os.getenv("LORA_HF_REPOS", "").strip()
    if lora_hf_raw:
        for entry in lora_hf_raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" not in entry:
                print(f"  [warn] bad LORA_HF_REPOS entry (expected name:owner/repo/file): {entry}", file=sys.stderr)
                continue
            name, repo_path = entry.split(":", 1)
            dest = LORAS_DIR / f"{name.strip()}.safetensors"
            _download(_hf_url(repo_path.strip()), dest, f"LoRA {name} (HuggingFace)")

    print("=== Download complete ===")


if __name__ == "__main__":
    main()
