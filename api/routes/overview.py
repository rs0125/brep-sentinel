"""Cross-run aggregation for the Overview dashboard: counts by run kind,
verdict distribution across every single-file adjudication, a chronological
FP-rate/recall series across batch runs (for a trend chart), and a recent-
activity feed spanning all run kinds. Pure read-side aggregation over the
runs table -- no pipeline code runs here.
"""
from __future__ import annotations

from fastapi import APIRouter

from .. import storage

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview")
def overview():
    return {
        "counts_by_kind": storage.counts_by_kind(),
        "verdict_distribution": storage.verdict_distribution(),
        "batch_metrics_series": storage.batch_metrics_series(),
        "recent_activity": storage.recent_activity(),
    }
