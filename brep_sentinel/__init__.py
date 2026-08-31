"""brep-sentinel: reference-free, exploit-agnostic detection of adversarially
malformed B-rep CAD (STEP) files via cross-kernel differential parsing with
invariant-based adjudication.

Pipeline stages (each independently runnable via the CLI in run.py):
    1. corpus   - obtain/generate a corpus of clean STEP B-rep parts
    2. kernel-a - tolerant/healing STEP reader  -> normalized descriptor
    3. kernel-b - strict/literal STEP reader     -> normalized descriptor
    4. invariants - per-descriptor validity report (Euler-Poincare, closure,
                    orientation coherence, degeneracy)
    5. adjudicate - diff the two descriptors and adjudicate divergence using the
                    invariant reports -> clean / benign-ambiguity / flagged / malformed
    6. perturb  - generate STRUCTURALLY VALID perturbations (false-positive stress test)
    7. evaluate - run the whole corpus through 2-5; confusion matrix, precision/recall
    8. report   - markdown summary with matrix, per-invariant hit rates, worked examples
"""

__version__ = "0.1.0"
