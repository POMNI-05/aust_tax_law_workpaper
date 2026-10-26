"""Run the optional local reviewer in the foreground; Ctrl+C stops it."""

from __future__ import annotations

import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DIR = ROOT / ".local_ai"


def main() -> None:
    portable = LOCAL_DIR / "runtime" / "ollama"
    executable = str(portable) if portable.exists() else shutil.which("ollama")
    if not executable:
        raise SystemExit("Ollama is not installed. See docs/local_ai_review.md for setup.")
    env = os.environ.copy()
    env.update({
        "OLLAMA_HOST": "127.0.0.1:11434",
        "OLLAMA_MODELS": str(LOCAL_DIR / "models"),
        "OLLAMA_NO_CLOUD": "1",
        "OLLAMA_KEEP_ALIVE": "0",
        "OLLAMA_NUM_PARALLEL": "1",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_MAX_QUEUE": "1",
        "OLLAMA_CONTEXT_LENGTH": "8192",
    })
    print("Local review server: http://127.0.0.1:11434; one request at a time.", flush=True)
    print("Models unload after requests. Press Ctrl+C to stop the server.", flush=True)
    os.execvpe("nice", ["nice", "-n", "10", executable, "serve"], env)


if __name__ == "__main__":
    main()
