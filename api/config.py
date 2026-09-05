"""Central paths and constants for the API layer.

This module assumes the `api/` package lives at the repo root, next to
`brep_sentinel/`, `run.py`, and `real_corpus/`:

    brep-sentinel/
    ├── brep_sentinel/
    ├── real_corpus/
    ├── run.py
    └── api/            <- this package

That layout is what lets `from brep_sentinel import kernel_a` etc. resolve
without any path hacking, as long as uvicorn is started from the repo root.
"""
from __future__ import annotations

import os

API_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(API_DIR)

# All API-owned state (upload files, per-run pipeline output, run history)
# lives under api_storage/, sitting next to brep_sentinel_out/ but never
# touching it -- the CLI (run.py) and the API can be used side by side
# without clobbering each other's output directories.
STORAGE_DIR = os.path.join(REPO_ROOT, "api_storage")
SINGLE_DIR = os.path.join(STORAGE_DIR, "single")   # one dir per single-file run
BATCH_DIR = os.path.join(STORAGE_DIR, "batch")     # one dir per batch pipeline run
REAL_DIR = os.path.join(STORAGE_DIR, "real")       # one dir per real-corpus demo run
INDEX_FILE = os.path.join(STORAGE_DIR, "runs_index.json")

# The repo's existing real_corpus/ directory (shared, refreshed by /ingest).
REAL_CORPUS_DIR = os.path.join(REPO_ROOT, "real_corpus")

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB safety cap on a single STEP upload

for _d in (STORAGE_DIR, SINGLE_DIR, BATCH_DIR, REAL_DIR):
    os.makedirs(_d, exist_ok=True)
