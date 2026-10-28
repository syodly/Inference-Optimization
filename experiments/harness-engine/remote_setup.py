"""Project-local setup on songprojgpu1; invoked as independent model/env jobs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path.home() / "harness-engine"
MODEL = "Qwen/Qwen3.8-27B"


def save(name: str, data: dict) -> None:
    path = ROOT / "state" / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def model_job() -> dict:
    from modelscope import snapshot_download
    from modelscope.hub.api import HubApi

    api = HubApi()
    revision = api.get_valid_revision_detail(MODEL, revision="master")
    print("MODEL_REVISION", json.dumps(revision, ensure_ascii=False), flush=True)
    save("model_revision", {"model_id": MODEL, "detail": revision, "time": time.time()})
    files = api.get_model_files(MODEL, revision="master", recursive=True)
    (ROOT / "state" / "modelscope_files.json").write_text(
        json.dumps(files, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    path = Path(snapshot_download(MODEL, revision="master", cache_dir=ROOT / "models", max_workers=8))
    manifest = []
    for f in sorted(path.rglob("*")):
        if f.is_file():
            entry = {"path": str(f.relative_to(path)), "bytes": f.stat().st_size}
            if f.stat().st_size < 20_000_000:
                entry["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
            manifest.append(entry)
    result = {"model_id": MODEL, "path": str(path), "revision": revision,
              "files": manifest, "finished": time.time()}
    save("model_manifest", result)
    return {"path": str(path), "files": len(manifest)}


def environment_job() -> dict:
    env_path = ROOT / ".venv-engine"
    python = env_path / "bin" / "python"
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(ROOT / "cache" / "uv")
    commands = [
        ["uv", "venv", "--python", "3.12", "--python-preference", "only-managed", str(env_path)],
        ["uv", "pip", "install", "--python", str(python), "--torch-backend=auto",
         "vllm==0.32.0", "modelscope==1.40.2", "httpx", "datasets", "pyarrow",
         "numpy", "scipy", "matplotlib", "psutil"],
    ]
    for command in commands:
        print("COMMAND", json.dumps(command), flush=True)
        subprocess.run(command, env=env, check=True)
    frozen = subprocess.check_output(["uv", "pip", "freeze", "--python", str(python)], env=env, text=True)
    (ROOT / "state" / "requirements-engine.lock").write_text(frozen, encoding="utf-8")
    check = subprocess.check_output([str(python), "-c",
        "import torch,vllm,transformers,json;print(json.dumps({'torch':torch.__version__,"
        "'cuda':torch.version.cuda,'cuda_available':torch.cuda.is_available(),"
        "'vllm':vllm.__version__,'transformers':transformers.__version__}))"], env=env, text=True)
    print("INSTALLED", check, flush=True)
    return {"python": str(python), "versions": check.strip()}


def main() -> None:
    job = sys.argv[1]
    for name in ("state", "models", "cache", "logs", "runs", "datasets"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    started = time.time()
    save(job, {"status": "running", "pid": os.getpid(), "started": started})
    try:
        result = {"model": model_job, "env": environment_job}[job]()
    except Exception as exc:
        save(job, {"status": "failed", "started": started, "finished": time.time(), "error": repr(exc)})
        raise
    save(job, {"status": "complete", "started": started, "finished": time.time(), "result": result})


if __name__ == "__main__":
    main()
