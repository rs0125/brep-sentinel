Prompt for the coding agent:

Build a research prototype called brep-sentinel that detects topologically anomalous B-rep CAD models via cross-kernel differential parsing with invariant-based adjudication. Python, OpenCASCADE via pythonocc-core as kernel A. For kernel B, use a second independent parser — start with the steputils/ifcopenshell-style text-level STEP reader OR a second OCCT version pinned differently; if neither gives clean independence, implement a minimal standalone STEP entity-graph parser (records, IDs, references only — no geometry evaluation). Document which you used.

Pipeline stages, each a separate module:

Corpus fetch. Pull clean STEP files from the ABC dataset and the Fusion360 Gallery / "Better STEP" public sets. ~50 parts, varied complexity. Cache locally. Record source and hash per file.
Kernel-A load. Parse each file in OCCT. Extract topology counts (V, E, F, shells, genus), per-face surface type, orientation flags, and the face-edge adjacency graph. Store as a normalized JSON descriptor.
Kernel-B load. Parse the same file independently. Produce the same descriptor schema.
Invariant checker. For each descriptor independently, evaluate: Euler-Poincaré consistency (V−E+F vs 2(S−G)); shell closure / watertightness; orientation coherence across shared edges; presence of degenerate entities (zero-length edges, zero-area faces, edges referenced by ≠2 faces). Output a per-descriptor validity report — which invariants hold, which fail, where.
Differential + adjudication. Diff the two descriptors. Where they disagree, use the invariant reports to adjudicate: is one side's interpretation invalid while the other's is valid? Classify each file as (a) convergent + both valid → clean, (b) divergent but both valid → benign ambiguity, (c) divergent with one side invalid → flagged, (d) convergent but both invalid → malformed. This adjudication step is the core contribution — log its reasoning per file.
Test-input generator — STRUCTURALLY VALID PERTURBATIONS ONLY. To exercise the detector, generate modified copies of clean files using only these operations, all of which keep the file a well-formed, inert, parseable STEP:
Geometric weakening edits: introduce an internal void (closed interior surface where solid was expected), reduce local wall thickness, or add a reentrant notch on a face — via legitimate modeling ops in OCCT, re-exported as valid STEP.
Benign redundancy: add duplicate-but-consistent entities, reordered adjacency lists, or extra unreferenced records — nothing malformed, just non-canonical.
Do NOT generate malformed topology references, crafted length/count fields, degenerate entities designed to trip a parser, or any structure whose purpose is to make a kernel crash, misparse, or heal into a different solid. If a perturbation can't be produced through valid modeling operations that re-export as spec-conforming STEP, it is out of scope — skip it and note why. Label every generated file with its perturbation type for scoring.
Evaluation harness. Run the whole corpus (clean + perturbed) through stages 2–5. Report: do clean files land in bucket (a)? Do weakening edits get caught by the invariant/adjudication logic? Confusion matrix by perturbation type. Precision/recall. Highlight any clean file misclassified as flagged (false positives — the thing that would make this unusable in practice).
Report. Emit a markdown summary with the matrix, per-invariant hit rates, and 2–3 worked examples showing the adjudication reasoning on a caught perturbation vs a clean file.

Constraints: deterministic where possible (log kernel versions and seeds); every stage independently runnable and testable; no network calls outside stage 1; keep all generated test files in a clearly-labeled perturbed/ directory with a manifest.
