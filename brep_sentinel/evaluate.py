"""Stage 7 -- evaluation harness.

Runs the full corpus (clean + valid perturbations + adversarial fixtures)
through stages 2-5 (+ advisory), and scores the detector:

  * confusion matrix  : ground-truth category  x  adjudication verdict
  * false-positive rate on the 64 structurally-VALID files (the metric that
    decides whether this is usable in practice)
  * recall of invariant adjudication on crafted-INVALID fixtures
  * layered recall (adjudication + geometric advisory) incl. geometric weakening
  * per-invariant hit rate on the crafted set

All per-file descriptors, validity reports, and adjudications are written under
<out>/analysis/ so any result is independently inspectable.
"""
from __future__ import annotations

import glob
import json
import os
from collections import Counter, defaultdict

from . import kernel_a, kernel_b
from .adjudicate import adjudicate, FLAGGED, MALFORMED, CLEAN, BENIGN_AMBIGUITY
from .advisory import advisory
from .invariants import validity_report
from .common import env_fingerprint

# ground-truth categories
CLEAN_CORPUS = "clean"
BENIGN = "benign_redundancy"
WEAKENING = "geometric_weakening"
ADV_FLAGGED = "adversarial_flagged"
ADV_MALFORMED = "adversarial_malformed"
ADV_AMBIGUOUS = "adversarial_ambiguous"

VALID_CATEGORIES = {CLEAN_CORPUS, BENIGN, WEAKENING}
POSITIVE_VERDICTS = {FLAGGED, MALFORMED}


def _inventory(out_dir: str):
    items = []
    # clean
    cm = json.load(open(os.path.join(out_dir, "corpus", "manifest.json")))
    for p in cm["parts"]:
        items.append((p["id"], os.path.join(out_dir, p["path"]), CLEAN_CORPUS,
                      p.get("ground_truth")))
    # perturbed
    pth = os.path.join(out_dir, "perturbed", "manifest.json")
    if os.path.exists(pth):
        pm = json.load(open(pth))
        for p in pm["parts"]:
            cat = WEAKENING if p["perturbation_type"].startswith("weakening") else BENIGN
            items.append((p["id"], os.path.join(out_dir, p["path"]), cat,
                          {"perturbation_type": p["perturbation_type"]}))
    # fixtures
    fth = os.path.join(out_dir, "fixtures", "manifest.json")
    if os.path.exists(fth):
        fm = json.load(open(fth))
        cmap = {"flagged": ADV_FLAGGED, "malformed": ADV_MALFORMED,
                "benign_ambiguity": ADV_AMBIGUOUS}
        for p in fm["parts"]:
            items.append((p["id"], os.path.join(out_dir, p["path"]),
                          cmap[p["expected_bucket"]], {"fixture_kind": p["fixture_kind"]}))
    return items


def evaluate(out_dir: str) -> dict:
    adir = os.path.join(out_dir, "analysis")
    os.makedirs(adir, exist_ok=True)
    rows = []
    confusion = defaultdict(Counter)
    for pid, path, category, meta in _inventory(out_dir):
        da = kernel_a.load(path)
        db = kernel_b.load(path)
        ra = validity_report(da)
        rb = validity_report(db)
        adj = adjudicate(da, db)
        adv = advisory(db)

        da.dump(os.path.join(adir, f"{pid}.kernelA.json"))
        db.dump(os.path.join(adir, f"{pid}.kernelB.json"))
        with open(os.path.join(adir, f"{pid}.adjudication.json"), "w") as fh:
            json.dump({"adjudication": adj.to_json(),
                       "validity_a": ra, "validity_b": rb,
                       "advisory": adv}, fh, indent=2)

        confusion[category][adj.verdict] += 1
        rows.append({
            "id": pid, "category": category, "verdict": adj.verdict,
            "a_valid": adj.a_valid, "b_valid": adj.b_valid,
            "advisory": adv["any"], "advisory_flags": [f["type"] for f in adv["flags"]],
            "b_failures": rb["failures"], "meta": meta,
        })

    # ---- metrics ----
    valid_files = [r for r in rows if r["category"] in VALID_CATEGORIES]
    false_positives = [r for r in valid_files if r["verdict"] in POSITIVE_VERDICTS]
    fp_rate = len(false_positives) / len(valid_files) if valid_files else 0.0

    crafted_invalid = [r for r in rows
                       if r["category"] in (ADV_FLAGGED, ADV_MALFORMED)]
    caught = [r for r in crafted_invalid if r["verdict"] in POSITIVE_VERDICTS]
    recall = len(caught) / len(crafted_invalid) if crafted_invalid else 0.0

    weakening = [r for r in rows if r["category"] == WEAKENING]
    weakening_advisory = [r for r in weakening if r["advisory"]]
    layered_pos = [r for r in (crafted_invalid + weakening)
                   if r["verdict"] in POSITIVE_VERDICTS or r["advisory"]]
    layered_targets = crafted_invalid + weakening
    layered_recall = len(layered_pos) / len(layered_targets) if layered_targets else 0.0

    # per-invariant hit rate on crafted-invalid (which invariant caught it, via B)
    inv_hits = Counter()
    for r in crafted_invalid:
        for f in r["b_failures"]:
            inv_hits[f] += 1

    # precision over the whole set (positive = flagged/malformed)
    all_pos = [r for r in rows if r["verdict"] in POSITIVE_VERDICTS]
    tp = [r for r in all_pos if r["category"] in (ADV_FLAGGED, ADV_MALFORMED)]
    precision = len(tp) / len(all_pos) if all_pos else 1.0

    results = {
        "env": env_fingerprint(),
        "counts": {
            "clean": sum(1 for r in rows if r["category"] == CLEAN_CORPUS),
            "benign_perturbations": sum(1 for r in rows if r["category"] == BENIGN),
            "weakening_perturbations": len(weakening),
            "adversarial_fixtures": sum(1 for r in rows if r["category"].startswith("adversarial")),
            "total": len(rows),
        },
        "confusion_matrix": {c: dict(v) for c, v in confusion.items()},
        "metrics": {
            "valid_files": len(valid_files),
            "false_positives": len(false_positives),
            "false_positive_rate": round(fp_rate, 4),
            "crafted_invalid": len(crafted_invalid),
            "adjudication_recall": round(recall, 4),
            "precision": round(precision, 4),
            "weakening_total": len(weakening),
            "weakening_caught_by_advisory": len(weakening_advisory),
            "layered_recall": round(layered_recall, 4),
        },
        "per_invariant_hits_on_crafted": dict(inv_hits),
        "false_positive_files": [r["id"] for r in false_positives],
        "rows": rows,
    }
    with open(os.path.join(out_dir, "evaluation.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    return results


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "brep_sentinel_out"
    res = evaluate(out)
    m = res["metrics"]
    print("=== brep-sentinel evaluation ===")
    print("files:", res["counts"])
    print(f"false-positive rate (valid files): {m['false_positive_rate']:.1%} "
          f"({m['false_positives']}/{m['valid_files']})")
    print(f"adjudication recall (crafted-invalid): {m['adjudication_recall']:.1%} "
          f"({len(res['rows']) and ''}{m['crafted_invalid']} targets)")
    print(f"layered recall (adjudication+advisory): {m['layered_recall']:.1%}")
    print("per-invariant hits on crafted:", res["per_invariant_hits_on_crafted"])
    print("confusion matrix:")
    for c, v in res["confusion_matrix"].items():
        print(f"  {c:22s} {v}")
