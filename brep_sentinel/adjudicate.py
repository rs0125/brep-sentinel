"""Stage 5 -- differential + invariant-based adjudication (the core contribution).

Plain parser-differential techniques only tell you the two kernels DISAGREE.
B-rep validity invariants let us go further and adjudicate WHO IS WRONG: we diff
the two descriptors, and where they diverge we consult each side's validity
report to decide whether one interpretation is invalid while the other is valid.

Classification buckets (from the brief):
  (a) clean            -> convergent + both valid
  (b) benign_ambiguity -> divergent but both valid  (residual risk: a polyglot
                          hides here; flagged as SUSPECT, not malformed)
  (c) flagged          -> divergent with exactly one side invalid  (the tell-tale
                          of a defect one kernel silently heals -- adversarial
                          signature)
  (d) malformed        -> convergent but both invalid (broken the same way in
                          both kernels)

Every decision is returned with its reasoning trace.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .common import Descriptor
from .invariants import validity_report


# verdicts
CLEAN = "clean"
BENIGN_AMBIGUITY = "benign_ambiguity"
FLAGGED = "flagged"
MALFORMED = "malformed"


@dataclass
class Adjudication:
    source_file: str
    verdict: str
    convergent: bool
    a_valid: bool
    b_valid: bool
    count_diffs: dict = field(default_factory=dict)
    structural_diffs: list = field(default_factory=list)
    a_failures: list = field(default_factory=list)
    b_failures: list = field(default_factory=list)
    healing_ops: int = 0
    reasoning: list = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "source_file": self.source_file,
            "verdict": self.verdict,
            "convergent": self.convergent,
            "a_valid": self.a_valid,
            "b_valid": self.b_valid,
            "count_diffs": self.count_diffs,
            "structural_diffs": self.structural_diffs,
            "a_failures": self.a_failures,
            "b_failures": self.b_failures,
            "healing_ops": self.healing_ops,
            "reasoning": self.reasoning,
        }


def _diff_counts(a: Descriptor, b: Descriptor) -> dict:
    out = {}
    ca, cb = a.counts(), b.counts()
    for k in ("V", "E", "F", "S", "R"):
        if ca[k] != cb[k]:
            out[k] = {"kernel_a": ca[k], "kernel_b": cb[k]}
    return out


def _structural_diffs(a: Descriptor, b: Descriptor) -> list:
    """Beyond counts: differences in per-shell closure and edge incidence
    profile that indicate the two kernels built different solids."""
    diffs = []
    a_closed = sorted((s.id, s.closed) for s in a.shells)
    b_closed = sorted((s.id, s.closed) for s in b.shells)
    if a_closed != b_closed:
        diffs.append({"kind": "shell_closure",
                      "kernel_a": a_closed, "kernel_b": b_closed})

    def inc_profile(d: Descriptor):
        prof = {}
        for _eid, uses in d.edge_uses.items():
            n = len({u[0] for u in uses})
            prof[n] = prof.get(n, 0) + 1
        return dict(sorted(prof.items()))

    pa, pb = inc_profile(a), inc_profile(b)
    if pa != pb:
        diffs.append({"kind": "edge_incidence_profile",
                      "kernel_a": pa, "kernel_b": pb})
    return diffs


def adjudicate(a: Descriptor, b: Descriptor) -> Adjudication:
    ra = validity_report(a)
    rb = validity_report(b)
    count_diffs = _diff_counts(a, b)
    struct = _structural_diffs(a, b)
    convergent = (not count_diffs) and (not struct)
    a_valid, b_valid = ra["valid"], rb["valid"]

    adj = Adjudication(
        source_file=a.source_file,
        verdict="", convergent=convergent,
        a_valid=a_valid, b_valid=b_valid,
        count_diffs=count_diffs, structural_diffs=struct,
        a_failures=ra["failures"], b_failures=rb["failures"],
        healing_ops=len(a.healing_log),
    )
    r = adj.reasoning

    if convergent:
        if a_valid and b_valid:
            adj.verdict = CLEAN
            r.append("Both kernels converged to identical topology counts, "
                     "shell closure, and edge-incidence profile.")
            r.append("Both interpretations satisfy all four validity invariants.")
            r.append("-> CLEAN: no divergence to adjudicate; nothing to flag.")
        else:
            adj.verdict = MALFORMED
            r.append("Both kernels converged to the SAME topology, but that "
                     "shared interpretation violates invariants "
                     f"(A fails {ra['failures']}, B fails {rb['failures']}).")
            r.append("No differential signal, but the file is not a valid solid.")
            r.append("-> MALFORMED: broken identically in both kernels "
                     "(consistent with an honest/accidental defect, not a "
                     "kernel-divergent attack).")
    else:
        r.append("Kernels DIVERGED: " +
                 (f"count diffs {count_diffs}; " if count_diffs else "") +
                 (f"structural diffs {[d['kind'] for d in struct]}; " if struct else ""))
        if a.healing_log:
            r.append(f"Kernel A (tolerant) applied {len(a.healing_log)} healing "
                     f"operation(s): e.g. {a.healing_log[0]}")
        if a_valid and not b_valid:
            adj.verdict = FLAGGED
            r.append("Adjudication: Kernel A's interpretation is VALID, Kernel B's "
                     f"is INVALID (B fails {rb['failures']}).")
            r.append("The literal file (Kernel B) is not a well-formed solid; the "
                     "tolerant kernel SILENTLY HEALED it into a valid but DIFFERENT "
                     "solid. The approved/displayed model would not match the file.")
            r.append("-> FLAGGED: divergence adjudicated to a one-sided defect that "
                     "healing masks -- the signature of a crafted/kernel-divergent "
                     "input, not benign noise.")
        elif b_valid and not a_valid:
            adj.verdict = FLAGGED
            r.append("Adjudication: Kernel B's interpretation is VALID, Kernel A's "
                     f"is INVALID (A fails {ra['failures']}).")
            r.append("The tolerant kernel's healing itself produced an invalid "
                     "solid while the literal reading is valid -- a divergence that "
                     "would manifest differently downstream.")
            r.append("-> FLAGGED: one-sided invalidity under divergence.")
        elif not a_valid and not b_valid:
            adj.verdict = MALFORMED
            r.append("Adjudication: both interpretations are invalid "
                     f"(A fails {ra['failures']}, B fails {rb['failures']}), "
                     "and they disagree on the topology.")
            r.append("-> MALFORMED: divergent AND both invalid.")
        else:
            adj.verdict = BENIGN_AMBIGUITY
            r.append("Adjudication: both interpretations are individually VALID "
                     "solids, yet they DIFFER.")
            r.append("Invariants cannot name a wrong side -- this is genuine "
                     "specification ambiguity. NOTE: this bucket is exactly where a "
                     "B-rep polyglot would hide (two valid but different solids); it "
                     "is surfaced as SUSPECT residual risk, not cleared.")
            r.append("-> BENIGN_AMBIGUITY (SUSPECT): divergent, both valid.")

    return adj


def adjudicate_file(path: str) -> Adjudication:
    from . import kernel_a, kernel_b
    return adjudicate(kernel_a.load(path), kernel_b.load(path))


if __name__ == "__main__":
    import json
    import sys
    adj = adjudicate_file(sys.argv[1])
    print(json.dumps(adj.to_json(), indent=2))
