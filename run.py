#!/usr/bin/env python3
"""brep-sentinel pipeline orchestrator.

Every stage is independently runnable and testable. Examples:

    python run.py all                     # run the whole pipeline
    python run.py corpus                  # stage 1: generate clean corpus
    python run.py perturb                 # stage 6: generate valid perturbations
    python run.py fixtures                # generate adversarial test vectors
    python run.py kernel-a FILE.step      # stage 2: strict descriptor to stdout
    python run.py kernel-b FILE.step      # stage 3: strict descriptor to stdout
    python run.py invariants FILE.step    # stage 4: validity report to stdout
    python run.py adjudicate FILE.step    # stage 5: adjudication to stdout
    python run.py advisory FILE.step      # geometric advisory to stdout
    python run.py evaluate                # stage 7: run corpus, write evaluation.json
    python run.py report                  # stage 8: write REPORT.md

Default output directory: ./brep_sentinel_out  (override with --out DIR)
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description="brep-sentinel pipeline")
    ap.add_argument("stage", choices=[
        "all", "corpus", "perturb", "fixtures", "kernel-a", "kernel-b",
        "invariants", "adjudicate", "advisory", "evaluate", "report",
        "ingest", "real"])
    ap.add_argument("file", nargs="?", help="STEP file for per-file stages")
    ap.add_argument("--out", default="brep_sentinel_out", help="output directory")
    args = ap.parse_args(argv)
    out = args.out

    if args.stage in ("all", "corpus"):
        from brep_sentinel.corpus.generate import generate_corpus
        m = generate_corpus(out)
        print(f"[corpus]   {len(m['parts'])} clean parts -> {out}/corpus/clean")
    if args.stage in ("all", "perturb"):
        from brep_sentinel.perturb import generate_perturbations
        m = generate_perturbations(out)
        print(f"[perturb]  {len(m['parts'])} valid perturbations -> {out}/perturbed")
    if args.stage in ("all", "fixtures"):
        from brep_sentinel.fixtures import generate_fixtures
        m = generate_fixtures(out)
        print(f"[fixtures] {len(m['parts'])} adversarial vectors -> {out}/fixtures")
    if args.stage in ("all", "evaluate"):
        from brep_sentinel.evaluate import evaluate
        res = evaluate(out)
        mm = res["metrics"]
        print(f"[evaluate] {res['counts']['total']} files · "
              f"FP={mm['false_positive_rate']:.1%} · "
              f"recall={mm['adjudication_recall']:.1%} · "
              f"layered={mm['layered_recall']:.1%}")
    if args.stage in ("all", "report"):
        from brep_sentinel.report import build_report
        build_report(out)
        print(f"[report]   {out}/REPORT.md")
    if args.stage == "ingest":
        from brep_sentinel.ingest import ingest
        m = ingest()
        print(f"[ingest]   {len(m['files'])} real files -> real_corpus/ "
              f"(provenance in real_corpus/SOURCES.json)")
    if args.stage in ("all", "real"):
        from brep_sentinel.demo_real import run as run_real, build_real_report
        rr = run_real(out_dir=out)
        build_real_report(out)
        sm = rr["summary"]
        print(f"[real]     {sm['real_solids_tested']} real solids · "
              f"baseline clean {sm['baseline_clean']}/{sm['real_solids_tested']} · "
              f"FP {sm['baseline_false_positives']} · report -> {out}/REAL_REPORT.md")

    # per-file stages
    if args.stage in ("kernel-a", "kernel-b", "invariants", "adjudicate", "advisory"):
        if not args.file:
            ap.error(f"stage '{args.stage}' requires a FILE.step argument")
        from brep_sentinel import kernel_a, kernel_b
        if args.stage == "kernel-a":
            print(json.dumps(kernel_a.load(args.file).to_json(), indent=2))
        elif args.stage == "kernel-b":
            print(json.dumps(kernel_b.load(args.file).to_json(), indent=2))
        elif args.stage == "invariants":
            from brep_sentinel.invariants import validity_report
            print(json.dumps(validity_report(kernel_b.load(args.file)), indent=2))
        elif args.stage == "adjudicate":
            from brep_sentinel.adjudicate import adjudicate_file
            print(json.dumps(adjudicate_file(args.file).to_json(), indent=2))
        elif args.stage == "advisory":
            from brep_sentinel.advisory import advisory
            print(json.dumps(advisory(kernel_b.load(args.file)), indent=2))


if __name__ == "__main__":
    main()
