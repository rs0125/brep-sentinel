"""Thin wrappers around brep_sentinel pipeline functions.

Every function here calls exactly what run.py's stages call -- this module
adds no new detection/pipeline logic of its own. It only adds:
  - per-run directory isolation (so two batch runs, or two uploads, never
    clobber each other's brep_sentinel_out/-style output), and
  - JSON shaping (bundling descriptor + validity + adjudication + advisory
    into one payload the frontend can render in a single request).

Signatures below are copied verbatim from the repo (checked against
brep_sentinel/{kernel_a,kernel_b,adjudicate,invariants,advisory,evaluate,
report,ingest,demo_real}.py) -- if your partner changes one of those
signatures, this is the only file that needs updating.
"""
from __future__ import annotations

import json
import os
from typing import Any

from brep_sentinel import kernel_a, kernel_b
from brep_sentinel.adjudicate import adjudicate
from brep_sentinel.advisory import advisory
from brep_sentinel.invariants import validity_report
from brep_sentinel.corpus.generate import generate_corpus
from brep_sentinel.perturb import generate_perturbations
from brep_sentinel.fixtures import generate_fixtures
from brep_sentinel.evaluate import evaluate as run_evaluate
from brep_sentinel.report import build_report
from brep_sentinel.ingest import ingest as run_ingest
from brep_sentinel.demo_real import run as run_demo_real, build_real_report

from ..config import SINGLE_DIR, BATCH_DIR, REAL_DIR, REAL_CORPUS_DIR


# ---------------------------------------------------------------------------
# Single-file adjudication
# mirrors: run.py kernel-a / kernel-b / invariants / adjudicate / advisory
# FILE.step, combined into one call so the frontend gets everything at once.
# ---------------------------------------------------------------------------
def single_run_dir(run_id: str) -> str:
    d = os.path.join(SINGLE_DIR, run_id)
    os.makedirs(d, exist_ok=True)
    return d


def adjudicate_single(step_path: str) -> dict[str, Any]:
    """Run both kernels + invariants + adjudication + advisory on one file.

    Raises whatever kernel_a.load/kernel_b.load raise on a truly unparseable
    file (e.g. not STEP at all) -- the route layer turns that into a 422.
    A file that *parses* but is malformed does NOT raise: it comes back with
    parse_errors / failed invariants and a MALFORMED or FLAGGED verdict,
    which is the whole point of the tool.
    """
    da = kernel_a.load(step_path)
    db = kernel_b.load(step_path)
    ra = validity_report(da)
    rb = validity_report(db)
    adj = adjudicate(da, db)
    adv = advisory(db)
    return {
        "verdict": adj.verdict,
        "adjudication": adj.to_json(),
        "kernel_a": da.to_json(),
        "kernel_b": db.to_json(),
        "validity_a": ra,
        "validity_b": rb,
        "advisory": adv,
    }


# ---------------------------------------------------------------------------
# Batch pipeline
# mirrors: run.py all  (corpus -> perturb -> fixtures -> evaluate -> report)
# Isolated per run_id under api_storage/batch/<run_id> so historical runs are
# each independently inspectable, the same way brep_sentinel_out/analysis/
# already lets you inspect any single result.
# ---------------------------------------------------------------------------
def batch_run_dir(run_id: str) -> str:
    d = os.path.join(BATCH_DIR, run_id)
    os.makedirs(d, exist_ok=True)
    return d


def run_batch_pipeline(run_id: str) -> dict[str, Any]:
    out = batch_run_dir(run_id)
    corpus_m = generate_corpus(out)
    perturb_m = generate_perturbations(out)
    fixtures_m = generate_fixtures(out)
    evaluation = run_evaluate(out)               # writes out/evaluation.json
    report_text = build_report(out)              # writes out/REPORT.md
    return {
        "out_dir": out,
        "corpus_parts": len(corpus_m["parts"]),
        "perturbed_parts": len(perturb_m["parts"]),
        "fixture_parts": len(fixtures_m["parts"]),
        "evaluation": evaluation,
        "report_markdown": report_text,
    }


def get_batch_evaluation(run_id: str) -> dict[str, Any] | None:
    path = os.path.join(batch_run_dir(run_id), "evaluation.json")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def get_batch_report_markdown(run_id: str) -> str | None:
    path = os.path.join(batch_run_dir(run_id), "REPORT.md")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Real-corpus ingest + demo
# mirrors: run.py ingest, run.py real
# ---------------------------------------------------------------------------
def run_ingest_real_corpus() -> dict[str, Any]:
    """Refreshes the repo's single shared real_corpus/ directory.

    Not isolated per-run on purpose: real_corpus/ is a shared, provenance-
    tracked asset (see real_corpus/SOURCES.json), the same file the CLI
    (`python run.py ingest`) writes to. Re-running this just re-fetches it.
    """
    return run_ingest(REAL_CORPUS_DIR)


def real_run_dir(run_id: str) -> str:
    d = os.path.join(REAL_DIR, run_id)
    os.makedirs(d, exist_ok=True)
    return d


def run_real_demo(run_id: str) -> dict[str, Any]:
    out = real_run_dir(run_id)
    result = run_demo_real(real_dir=REAL_CORPUS_DIR, out_dir=out)
    build_real_report(out)                        # writes out/REAL_REPORT.md
    return {"out_dir": out, "result": result}


def get_real_report_markdown(run_id: str) -> str | None:
    path = os.path.join(real_run_dir(run_id), "REAL_REPORT.md")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return fh.read()
