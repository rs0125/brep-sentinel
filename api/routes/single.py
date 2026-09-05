"""POST a .step file -> full adjudication (kernel A, kernel B, invariants,
verdict, advisory) in one response. This is the core "upload a file" flow
the frontend's Upload/VerdictView/KernelDiff pages are built around.
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import MAX_UPLOAD_BYTES
from ..services import pipeline
from ..storage import get_run, list_runs, new_run_id, record_run

router = APIRouter(prefix="/api/adjudicate", tags=["single"])


@router.post("")
async def adjudicate_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".step", ".stp")):
        raise HTTPException(400, "Expected a .step or .stp file")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")
    if not data:
        raise HTTPException(400, "Uploaded file is empty")

    run_id = new_run_id()
    run_dir = pipeline.single_run_dir(run_id)
    step_path = os.path.join(run_dir, file.filename)
    with open(step_path, "wb") as fh:
        fh.write(data)

    try:
        result = pipeline.adjudicate_single(step_path)
    except Exception as e:
        # A file that fails to parse at all (not STEP, truncated, binary
        # garbage) raises out of the parser rather than coming back as a
        # MALFORMED verdict -- surface that distinctly from a real verdict.
        raise HTTPException(422, f"Could not parse file: {type(e).__name__}: {e}")

    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w") as fh:
        json.dump(result, fh, indent=2)

    record_run("single", run_id, {
        "filename": file.filename,
        "verdict": result["verdict"],
        "file_sha256": result["kernel_b"]["file_sha256"],
        "bytes": len(data),
    })

    return {"run_id": run_id, **result}


@router.get("/history")
def history(limit: int = 50):
    return list_runs(kind="single", limit=limit)


@router.get("/{run_id}")
def get_result(run_id: str):
    entry = get_run(run_id)
    if entry is None or entry["kind"] != "single":
        raise HTTPException(404, "No single-file run with that id")
    result_path = os.path.join(pipeline.single_run_dir(run_id), "result.json")
    if not os.path.exists(result_path):
        raise HTTPException(404, "Run recorded but result file missing on disk")
    with open(result_path) as fh:
        result = json.load(fh)
    return {"run_id": run_id, "meta": entry, **result}
