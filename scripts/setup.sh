#!/usr/bin/env bash
# Re-runnable installation without touching journal data or dependency declarations.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir /tmp/omoide-pip-cache --require-hashes -r requirements.lock
PIP_CACHE_DIR=/tmp/omoide-pip-cache .venv/bin/python -m pip check
.venv/bin/python -m pytest -q
