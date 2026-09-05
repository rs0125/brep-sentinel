"""Static metadata for the frontend -- lets the dashboard render the pipeline
diagram (stage name -> module -> description) without hardcoding the table
from the README into React. Update this list if brep_sentinel/ gains or
renames a stage; it is display-only and calls no pipeline code.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["meta"])

PIPELINE_STAGES = [
    {"stage": 1, "name": "corpus", "module": "brep_sentinel/corpus/generate.py",
     "description": "Generate clean STEP solids with known ground truth."},
    {"stage": 2, "name": "kernel_a", "module": "brep_sentinel/kernel_a.py",
     "description": "Tolerant/healing reader -> normalized descriptor."},
    {"stage": 3, "name": "kernel_b", "module": "brep_sentinel/kernel_b.py",
     "description": "Strict/literal reader -> normalized descriptor."},
    {"stage": 4, "name": "invariants", "module": "brep_sentinel/invariants.py",
     "description": "Per-descriptor validity report (4 invariants)."},
    {"stage": 5, "name": "adjudicate", "module": "brep_sentinel/adjudicate.py",
     "description": "Diff + adjudication -> clean/benign/flagged/malformed."},
    {"stage": 6, "name": "perturb", "module": "brep_sentinel/perturb.py",
     "description": "Structurally valid perturbations (false-positive stress test)."},
    {"stage": None, "name": "advisory", "module": "brep_sentinel/advisory.py",
     "description": "Complementary geometric check (void/thin-wall/notch)."},
    {"stage": None, "name": "fixtures", "module": "brep_sentinel/fixtures.py",
     "description": "Analysis-only crafted invalid/divergent test vectors."},
    {"stage": 7, "name": "evaluate", "module": "brep_sentinel/evaluate.py",
     "description": "Confusion matrix, FP rate, recall, per-invariant hits."},
    {"stage": 8, "name": "report", "module": "brep_sentinel/report.py",
     "description": "Markdown summary with worked examples."},
]


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/pipeline/stages")
def pipeline_stages():
    return PIPELINE_STAGES
