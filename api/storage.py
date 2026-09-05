"""Lightweight run-history index, backed by a single JSON file.

This is intentionally not a database. brep_sentinel itself is a stdlib-only,
file-based pipeline (manifests + JSON artifacts on disk), so the API layer
follows the same philosophy for run bookkeeping instead of bolting on a
database dependency for a handful of dashboard rows. record_run / list_runs /
get_run (plus the read-only aggregation helpers below) are the whole
interface the routes depend on, so swapping the backend later only means
rewriting this one file.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .config import INDEX_FILE

_lock = threading.Lock()


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_index() -> list[dict[str, Any]]:
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE) as fh:
        return json.load(fh)


def _write_index(rows: list[dict[str, Any]]) -> None:
    tmp = INDEX_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(rows, fh, indent=2)
    os.replace(tmp, INDEX_FILE)


def init_db() -> None:
    """Ensures the index file exists. Called once at API startup; a no-op
    if it's already there. Named to match whatever backend main.py wires
    up, in case this ever gets swapped for a real database."""
    if not os.path.exists(INDEX_FILE):
        _write_index([])


def record_run(kind: str, run_id: str, summary: dict[str, Any]) -> dict[str, Any]:
    """kind: 'single' | 'batch' | 'real' | 'ingest'

    `summary` is whatever small, list-friendly fields the dashboard needs to
    render a history row or chart point (e.g. filename + verdict for
    'single'; fp_rate + recall for 'batch') -- not the full nested result,
    which stays on disk under the run's own directory and is fetched
    separately by run_id.
    """
    entry = {"run_id": run_id, "kind": kind, "created_at": _now(), **summary}
    with _lock:
        rows = _read_index()
        rows.append(entry)
        _write_index(rows)
    return entry


def list_runs(kind: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        rows = _read_index()
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    rows = list(reversed(rows))  # newest first
    return rows[:limit]


def get_run(run_id: str) -> dict[str, Any] | None:
    with _lock:
        rows = _read_index()
    for r in rows:
        if r["run_id"] == run_id:
            return r
    return None


# ---------------------------------------------------------------------------
# Read-only aggregation for the Overview dashboard. No writes happen here --
# these just fold over the same JSON index above.
# ---------------------------------------------------------------------------
def counts_by_kind() -> dict[str, int]:
    with _lock:
        rows = _read_index()
    return dict(Counter(r["kind"] for r in rows))


def verdict_distribution() -> dict[str, int]:
    """Verdict counts across every single-file adjudication ever run."""
    singles = list_runs(kind="single", limit=100000)
    return dict(Counter(s["verdict"] for s in singles if "verdict" in s))


def batch_metrics_series(limit: int = 20) -> list[dict[str, Any]]:
    """Chronological (oldest -> newest) FP-rate/recall points for a trend chart."""
    rows = list_runs(kind="batch", limit=limit)
    rows.reverse()
    return [
        {
            "run_id": r["run_id"],
            "label": r.get("label") or r["run_id"][:6],
            "created_at": r["created_at"],
            "false_positive_rate": r["false_positive_rate"],
            "adjudication_recall": r["adjudication_recall"],
            "layered_recall": r["layered_recall"],
        }
        for r in rows
    ]


def recent_activity(limit: int = 15) -> list[dict[str, Any]]:
    return list_runs(kind=None, limit=limit)
