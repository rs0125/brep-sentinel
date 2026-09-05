"""Real-corpus demo: fetch real third-party STEP files, then baseline +
infect + score them. Mirrors `python run.py ingest` and `python run.py real`.

Kept as a separate router from /api/batch because it's a distinct id space
(real_corpus/ is one shared directory refreshed in place, not per-run) and a
distinct workflow (network fetch, then a fixed infection suite) from the
synthetic corpus pipeline.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import pipeline
from ..storage import get_run, list_runs, new_run_id, record_run

router = APIRouter(prefix="/api/real", tags=["real"])


class RealRunRequest(BaseModel):
    label: str | None = None


@router.post("/ingest")
def ingest():
    """Refreshes real_corpus/ from its upstream sources. Requires outbound
    network access from wherever the API is running -- if egress is
    restricted, drop files into real_corpus/ manually instead (the repo
    already ships a small committed set with SOURCES.json provenance)."""
    try:
        manifest = pipeline.run_ingest_real_corpus()
    except Exception as e:
        raise HTTPException(502, f"Ingest failed: {type(e).__name__}: {e}")
    run_id = new_run_id()
    record_run("ingest", run_id, {"files_fetched": len(manifest["files"])})
    return {"run_id": run_id, "manifest": manifest}


@router.post("/run")
def run_real_demo(body: RealRunRequest = RealRunRequest()):
    run_id = new_run_id()
    try:
        result = pipeline.run_real_demo(run_id)
    except FileNotFoundError as e:
        raise HTTPException(
            409, f"real_corpus/ is empty or missing -- run POST /api/real/ingest "
                 f"first: {e}")
    except Exception as e:
        raise HTTPException(500, f"Real-corpus demo failed: {type(e).__name__}: {e}")

    summary = result["result"].get("summary", {})
    record_run("real", run_id, {"label": body.label, **summary})
    return {"run_id": run_id, **result}


@router.get("/history")
def history(limit: int = 50):
    return list_runs(kind="real", limit=limit)


@router.get("/{run_id}/report")
def get_report(run_id: str):
    entry = get_run(run_id)
    if entry is None or entry["kind"] != "real":
        raise HTTPException(404, "No real-corpus run with that id")
    markdown = pipeline.get_real_report_markdown(run_id)
    if markdown is None:
        raise HTTPException(404, "Run recorded but REAL_REPORT.md missing on disk")
    return {"run_id": run_id, "markdown": markdown}
