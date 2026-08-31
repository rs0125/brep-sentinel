"""Complementary GEOMETRIC advisory (beyond the core invariant contribution).

Topologically-valid *geometric weakening* edits (internal void, thin wall,
reentrant notch) satisfy every B-rep invariant, so the differential/invariant
adjudicator correctly leaves them CLEAN -- it has no basis to flag a well-formed
solid. That is the honest limit of invariant adjudication. This module adds a
separate, best-effort GEOMETRIC heuristic (NOT a topological verdict) that can
surface such weakening as an advisory, so the two layers together cover both
kinds of threat. Heuristics are intentionally simple and tuned for the demo's
axis-aligned planar corpus.
"""
from __future__ import annotations

import math

from .common import Descriptor

MIN_EDGE_RATIO = 0.05
MIN_WALL_RATIO = 0.08


def _bbox_diag(desc: Descriptor) -> float:
    if not desc.vertices:
        return 1.0
    xs = [v.xyz for v in desc.vertices]
    lo = [min(p[i] for p in xs) for i in range(3)]
    hi = [max(p[i] for p in xs) for i in range(3)]
    return math.dist(lo, hi) or 1.0


def _anti_parallel_wall(desc: Descriptor, diag: float):
    """Min separation between anti-parallel planar faces whose in-plane extents
    overlap -- a proxy for wall thickness."""
    faces = [f for f in desc.faces if f.surface_type == "plane"]
    vd = {v.id: v.xyz for v in desc.vertices}
    ed = {e.id: e.vertex_ids for e in desc.edges}

    def face_pts(f):
        vs = set()
        for loop in [f.outer_loop_edges, *f.inner_loops]:
            for eid in loop:
                for vid in ed.get(eid, []):
                    vs.add(vid)
        return [vd[v] for v in vs if v in vd]

    def unit(n):
        m = math.sqrt(sum(c * c for c in n)) or 1.0
        return [c / m for c in n]

    best = None
    info = None
    for i in range(len(faces)):
        for j in range(i + 1, len(faces)):
            n1, n2 = unit(faces[i].normal), unit(faces[j].normal)
            if not (abs(n1[0] + n2[0]) < 1e-6 and abs(n1[1] + n2[1]) < 1e-6
                    and abs(n1[2] + n2[2]) < 1e-6):
                continue
            axis = max(range(3), key=lambda k: abs(n1[k]))
            if abs(n1[axis]) < 0.9:
                continue
            p1, p2 = face_pts(faces[i]), face_pts(faces[j])
            if not p1 or not p2:
                continue
            # overlap in the two in-plane axes
            other = [k for k in range(3) if k != axis]
            ov = True
            for k in other:
                a0, a1 = min(p[k] for p in p1), max(p[k] for p in p1)
                b0, b1 = min(p[k] for p in p2), max(p[k] for p in p2)
                if min(a1, b1) - max(a0, b0) <= 1e-9:
                    ov = False
                    break
            if not ov:
                continue
            sep = abs(p1[0][axis] - p2[0][axis])
            if sep > 1e-9 and (best is None or sep < best):
                best = sep
                info = (faces[i].id, faces[j].id)
    return best, info


def advisory(desc: Descriptor) -> dict:
    diag = _bbox_diag(desc)
    flags = []

    # 1. enclosed void
    voids = [s.id for s in desc.shells if s.kind == "void"]
    if voids or len(desc.shells) > 1:
        flags.append({"type": "enclosed_void",
                      "detail": f"solid has {len(desc.shells)} shells; "
                                f"void shells={voids} -- unexpected internal cavity"})

    # 2. small feature (short edges relative to part size) -> notch / sliver
    if desc.edges:
        me = min(desc.edges, key=lambda e: e.length)
        ratio = me.length / diag
        if ratio < MIN_EDGE_RATIO:
            flags.append({"type": "small_feature",
                          "detail": f"min edge #{me.id} length {me.length:.3f} = "
                                    f"{ratio:.1%} of bbox diagonal (possible notch/"
                                    f"sliver / stress concentrator)"})

    # 3. thin wall (anti-parallel face separation)
    sep, pair = _anti_parallel_wall(desc, diag)
    if sep is not None and sep / diag < MIN_WALL_RATIO:
        flags.append({"type": "thin_wall",
                      "detail": f"faces {pair} separated by {sep:.3f} = "
                                f"{sep/diag:.1%} of bbox diagonal (thin wall)"})

    return {"any": len(flags) > 0, "flags": flags, "bbox_diag": round(diag, 4)}


if __name__ == "__main__":
    import json, sys
    from . import kernel_b
    print(json.dumps(advisory(kernel_b.load(sys.argv[1])), indent=2))
