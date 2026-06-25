"""Tiny config loader. Reads a local .env (no extra dependency) into os.environ.

Put secrets in F:\\projects\\dealbreaker\\.env (gitignored), e.g.:

    TFNSW_API_KEY=your-key-from-opendata.transport.nsw.gov.au
"""
import os
from pathlib import Path


def _load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env()

TFNSW_API_KEY = os.environ.get("TFNSW_API_KEY", "").strip()
