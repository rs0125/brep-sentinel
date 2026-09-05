"""Runs the synthetic-corpus batch pipeline: corpus -> perturb -> fixtures ->
evaluate -> report. This is exactly `python run.py all`, isolated per run_id
so the dashboard can show a history of runs with their FP rate / recall
trending over time, and let the user open any past run's full report.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import pipeline
from ..storage import get_run, list_runs, new_run_id, record_run

router = APIRouter(prefix="/api/batch", tags=["batch"])


class BatchRunRequest(BaseModel):
    label: str | None = None


@router.post("/run")
def run_batch(body: BatchRunRequest = BatchRunRequest()):
    run_id = new_run_id()
    try:
        result = pipeline.run_batch_pipeline(run_id)
    except Exception as e:
        raise HTTPException(500, f"Batch pipeline failed: {type(e).__name__}: {e}")

    metrics = result["evaluation"]["metrics"]
    counts = result["evaluation"]["counts"]
    record_run("batch", run_id, {
        "label": body.label,
        "total_files": counts["total"],
        "false_positive_rate": metrics["false_positive_rate"],
        "adjudication_recall": metrics["adjudication_recall"],
        "layered_recall": metrics["layered_recall"],
    })
    return {"run_id": run_id, **result}


@router.get("/history")
def history(limit: int = 50):
    return list_runs(kind="batch", limit=limit)


@router.get("/{run_id}")
def get_evaluation(run_id: str):
    entry = get_run(run_id)
    if entry is None or entry["kind"] != "batch":
        raise HTTPException(404, "No batch run with that id")
    evaluation = pipeline.get_batch_evaluation(run_id)
    if evaluation is None:
        raise HTTPException(404, "Run recorded but evaluation.json missing on disk")
    return {"run_id": run_id, "meta": entry, "evaluation": evaluation}


@router.get("/{run_id}/report")
def get_report(run_id: str):
    entry = get_run(run_id)
    if entry is None or entry["kind"] != "batch":
        raise HTTPException(404, "No batch run with that id")
    markdown = pipeline.get_batch_report_markdown(run_id)
    if markdown is None:
        raise HTTPException(404, "Run recorded but REPORT.md missing on disk")
    return {"run_id": run_id, "markdown": markdown}
