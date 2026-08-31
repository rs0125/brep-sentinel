# brep-sentinel

A research prototype that detects **topologically anomalous B-rep CAD models**
via **cross-kernel differential parsing with invariant-based adjudication** —
positioned at the point where an untrusted STEP file is ingested, *before*
manufacturing, **reference-free** (no golden model) and **exploit-agnostic** (no
CVE signature).

The core idea: a valid B-rep solid must satisfy mathematical validity invariants
(Euler-Poincaré, shell closure, orientation coherence, no degeneracy). When two
independent kernels interpret the same file differently, those invariants let us
**adjudicate** the divergence — decide *which* interpretation, if any, is invalid
— instead of merely observing that the parsers disagree. That "who is wrong"
step is the contribution.

## Quick start

```bash
python run.py all           # generate corpus + perturbations + fixtures, evaluate, report
cat brep_sentinel_out/REPORT.md
```

No third-party dependencies — standard library only.

## Result (this run)

| metric | value |
|---|---|
| False-positive rate on 64 structurally-valid files | **0.0%** |
| Adjudication recall on crafted-invalid fixtures | **100%** (3/3) |
| Layered recall (adjudication + geometric advisory) | **100%** |

Every clean, benign, and *valid-but-weakened* file is left `CLEAN`; a
sub-tolerance crack that a forgiving kernel silently heals is `FLAGGED`;
non-manifold / missing-face inputs are `MALFORMED`; a vertex-weld polyglot lands
in `BENIGN_AMBIGUITY` (SUSPECT — the residual-risk bucket).

## Pipeline (each stage independently runnable)

| stage | module | what it does |
|---|---|---|
| 1 corpus | `brep_sentinel/corpus/generate.py` | generate clean STEP solids with known ground truth |
| 2 kernel A | `brep_sentinel/kernel_a.py` | tolerant/healing reader → normalized descriptor |
| 3 kernel B | `brep_sentinel/kernel_b.py` | strict/literal reader → normalized descriptor |
| 4 invariants | `brep_sentinel/invariants.py` | per-descriptor validity report (4 invariants) |
| 5 adjudicate | `brep_sentinel/adjudicate.py` | diff + adjudication → clean/benign/flagged/malformed |
| 6 perturb | `brep_sentinel/perturb.py` | STRUCTURALLY VALID perturbations (FP stress test) |
| — advisory | `brep_sentinel/advisory.py` | complementary geometric check (void/thin-wall/notch) |
| — fixtures | `brep_sentinel/fixtures.py` | analysis-only crafted invalid/divergent test vectors |
| 7 evaluate | `brep_sentinel/evaluate.py` | confusion matrix, FP rate, recall, per-invariant hits |
| 8 report | `brep_sentinel/report.py` | markdown summary with worked examples |

Per-file usage:

```bash
python run.py kernel-b   FILE.step   # strict descriptor
python run.py invariants FILE.step   # validity report
python run.py adjudicate FILE.step   # full adjudication + reasoning
python run.py advisory   FILE.step   # geometric advisory
```

## The two kernels (important honesty note)

`pythonocc-core` (OpenCASCADE) is conda-only and was **not available** in this
environment. Per the brief's stated fallback, both kernels are **independent
standalone STEP entity-graph parsers**:

- **Kernel B — strict/literal**: interprets the entity graph exactly as written.
  Vertex identity = `VERTEX_POINT` record id; a crack stays a crack.
- **Kernel A — tolerant/healing**: models a forgiving kernel's healing pass —
  merges near-coincident vertices, stitches duplicate edges, drops
  zero-length edges, repairs non-manifold edges — and logs every action.

On clean input they converge exactly; healing only changes the answer when the
file contains a defect, which is precisely the differential signal the
adjudicator uses. Drop real `.step` files into `brep_sentinel_out/corpus/clean/`
and the rest of the pipeline consumes them unchanged; if OCCT is installed, a
`pythonocc` reader can be slotted in as Kernel A behind the same descriptor
schema.

## Corpus substitution

The ABC / Fusion360 datasets are large, non-deterministic downloads. For a
self-contained, reproducible demonstration the corpus is **synthesized** as
genuine spec-shaped STEP solids (boxes, L/U-blocks, prisms, through-holed and
double-holed blocks; genus 0/1/2) whose exact `(V,E,F,S,R,H)` is known a priori —
better for *validating an invariant checker* because ground truth is exact.

## Test-input policy

The stage-6 generator emits **structurally valid perturbations only** — benign
redundancy and legitimate geometric weakening. It never fabricates malformed
topology, crafted count/length fields, degenerate entities, or anything meant to
crash or mis-heal a kernel. The invalid/divergent inputs used to demonstrate the
detector live in `fixtures.py` and are **inert, analysis-only topology-graph test
vectors** — they target no real kernel and carry no exploit payload; the "defect"
exists purely so the invariant checker has something to catch.

## Findings

See `brep_sentinel_out/REPORT.md`. Summary: invariant-based adjudication is a
real, non-fuzzy detection method for **divergence/validity** attacks (0% FP, 100%
recall on that class here). It cannot, by construction, flag topologically-valid
**geometric weakening** (that needs the complementary geometric advisory), and it
routes **both-valid-but-divergent** inputs to an explicit SUSPECT bucket — the
genuine residual risk where a B-rep polyglot would hide.
