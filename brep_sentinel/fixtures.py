"""Analysis-only ADVERSARIAL FIXTURES for the detector (not a payload factory).

These are inert, non-executable STEP graphs that are deliberately topologically
INVALID or KERNEL-DIVERGENT. Their sole purpose is to prove the invariant
checker + adjudicator can (a) detect invalidity and (b) adjudicate *which* kernel
is wrong -- the load-bearing question. They target no real kernel and contain no
crafted length/count fields, buffer-overflow strings, or crash triggers; the
"defect" is purely at the topology-graph level so the detector has something to
catch. Each maps to an expected adjudication bucket.

  fixture_crack       -> divergent, A valid / B invalid  => FLAGGED   (bucket c)
                        A duplicated vertex + shifted copy opens a crack B reads
                        literally but A silently heals shut.
  fixture_nonmanifold -> both invalid (edge incidence 3) => MALFORMED (bucket d)
  fixture_missingface -> both invalid (open shell, Euler) => MALFORMED (bucket d)
  fixture_weld_polyglot -> divergent, both valid          => BENIGN_AMBIGUITY /
                        SUSPECT (bucket b) -- two boxes sharing a coincident
                        vertex: A welds (V-1), B keeps separate; both valid,
                        different meshes. This is where a polyglot hides.
"""
from __future__ import annotations

import json
import os

from .common import sha256_bytes
from .step_parser import (Record, Ref, parse_step, serialize, max_id, find_roots)
from .step_model import Solid, write_step
from .corpus.generate import _extrude, _rect


def _clean_box_records(name="fix_base"):
    txt = _extrude(name, _rect(10, 10), None, 0, 10)
    return parse_step(write_step(txt))


# ------------------------------------------------------------------------------
def fixture_crack(delta=1e-6, name="fixture_crack") -> str:
    """Open a sub-tolerance crack: pick a vertex used by >=2 faces, clone it at
    +delta, and rewire ONE incident face to the clone. Kernel B sees boundary
    edges (open, invalid); Kernel A merges the clone back (delta < 1e-4) and
    stitches -> closed valid. Divergent + one-sided invalid => FLAGGED."""
    recs = _clean_box_records(name)
    nid = max_id(recs)

    # map: vertex_point id -> incident edge_curve ids
    vp_edges: dict[int, list[int]] = {}
    for r in recs.values():
        if r.type == "EDGE_CURVE":
            for vp in (r.args[1].id, r.args[2].id):
                vp_edges.setdefault(vp, []).append(r.id)

    # faces (advanced_face) -> set of edge_curve ids used
    def face_edges(fr: Record) -> set[int]:
        out = set()
        for b in fr.args[1]:
            br = recs[b.id]
            loop = recs[br.args[1].id]
            for oe in loop.args[1]:
                out.add(recs[oe.id].args[3].id)
        return out

    faces = [r for r in recs.values() if r.type == "ADVANCED_FACE"]
    # pick a vertex and a single face that uses one of its edges
    target_vp = next(vp for vp, es in vp_edges.items() if len(es) >= 2)
    target_edges = set(vp_edges[target_vp])
    target_face = next(f for f in faces if face_edges(f) & target_edges)

    # clone the CARTESIAN_POINT + VERTEX_POINT with +delta on x
    vpr = recs[target_vp]
    cp_id = vpr.args[1].id
    cp = recs[cp_id]
    x, y, z = [float(c) for c in cp.args[1]]
    nid += 1; new_cp = nid
    recs[new_cp] = Record(new_cp, "CARTESIAN_POINT", ["", [x + delta, y, z]])
    nid += 1; new_vp = nid
    recs[new_vp] = Record(new_vp, "VERTEX_POINT", ["", Ref(new_cp)])

    # for each edge_curve used by target_face that touches target_vp, clone it
    # pointing at new_vp, and rewire the face's oriented edges to the clone.
    used = face_edges(target_face) & target_edges
    ec_remap: dict[int, int] = {}
    for ec in used:
        r = recs[ec]
        v1, v2, curve, sense = r.args[1].id, r.args[2].id, r.args[3], r.args[4]
        nv1 = new_vp if v1 == target_vp else v1
        nv2 = new_vp if v2 == target_vp else v2
        nid += 1; nec = nid
        recs[nec] = Record(nec, "EDGE_CURVE", ["", Ref(nv1), Ref(nv2), curve, sense])
        ec_remap[ec] = nec

    # rewire ORIENTED_EDGEs in target_face's loops
    for b in target_face.args[1]:
        loop = recs[recs[b.id].args[1].id]
        for oe in loop.args[1]:
            oer = recs[oe.id]
            old = oer.args[3].id
            if old in ec_remap:
                oer.args[3] = Ref(ec_remap[old])
    return serialize(recs, name)


def fixture_nonmanifold(name="fixture_nonmanifold") -> str:
    """Add an internal triangular fin that reuses one existing box edge, giving
    that edge face-incidence 3. Non-manifold => invalid in both kernels."""
    recs = _clean_box_records(name)
    nid = max_id(recs)
    # pick an existing EDGE_CURVE and its two vertices
    ec = next(r for r in recs.values() if r.type == "EDGE_CURVE")
    v1, v2 = ec.args[1].id, ec.args[2].id
    p1 = [float(c) for c in recs[recs[v1].args[1].id].args[1]]
    p2 = [float(c) for c in recs[recs[v2].args[1].id].args[1]]
    apex = [(p1[0] + p2[0]) / 2 + 2.0, (p1[1] + p2[1]) / 2 + 2.0,
            (p1[2] + p2[2]) / 2 + 2.0]

    def new(t, *a):
        nonlocal nid
        nid += 1
        recs[nid] = Record(nid, t, list(a))
        return nid

    ap = new("CARTESIAN_POINT", "", apex)
    avp = new("VERTEX_POINT", "", Ref(ap))
    # two new edges v1-apex, apex-v2 (lines)
    def line(a, b):
        pa = [float(c) for c in recs[recs[a].args[1].id].args[1]]
        d = new("DIRECTION", "", [1.0, 0.0, 0.0])
        vec = new("VECTOR", "", Ref(d), 1.0)
        base = new("CARTESIAN_POINT", "", pa)
        ln = new("LINE", "", Ref(base), Ref(vec))
        return new("EDGE_CURVE", "", Ref(a), Ref(b), Ref(ln), True)
    e1 = line(v1, avp)
    e2 = line(avp, v2)
    # oriented edges + loop reusing existing edge ec
    oe1 = new("ORIENTED_EDGE", "", "*", "*", Ref(e1), True)
    oe2 = new("ORIENTED_EDGE", "", "*", "*", Ref(e2), True)
    oe3 = new("ORIENTED_EDGE", "", "*", "*", Ref(ec.id), False)
    loop = new("EDGE_LOOP", "", [Ref(oe1), Ref(oe2), Ref(oe3)])
    bound = new("FACE_OUTER_BOUND", "", Ref(loop), True)
    plpt = new("CARTESIAN_POINT", "", apex)
    axis = new("DIRECTION", "", [0.0, 0.0, 1.0])
    refd = new("DIRECTION", "", [1.0, 0.0, 0.0])
    place = new("AXIS2_PLACEMENT_3D", "", Ref(plpt), Ref(axis), Ref(refd))
    plane = new("PLANE", "", Ref(place))
    fin = new("ADVANCED_FACE", "", [Ref(bound)], Ref(plane), True)
    # attach fin to the closed shell
    shell = next(r for r in recs.values() if r.type == "CLOSED_SHELL")
    shell.args[1].append(Ref(fin))
    return serialize(recs, name)


def fixture_missingface(name="fixture_missingface") -> str:
    """Delete one face from the closed shell -> open shell / Euler parity break.
    Invalid in both kernels (healing cannot invent a face)."""
    recs = _clean_box_records(name)
    shell = next(r for r in recs.values() if r.type == "CLOSED_SHELL")
    shell.args[1] = shell.args[1][:-1]     # drop last face reference
    return serialize(recs, name)


def fixture_weld_polyglot(delta=0.0, name="fixture_weld_polyglot") -> str:
    """Two unit boxes sharing ONE coincident corner represented as two distinct
    VERTEX_POINTs. Kernel A welds them (V-1) -> valid; Kernel B keeps them apart
    -> valid but different mesh. Divergent + both valid => BENIGN_AMBIGUITY.
    (A vertex-welded 'polyglot' -- the residual-risk bucket.)"""
    b1 = _extrude("box1", _rect(10, 10), None, 0, 10)
    t1 = write_step(b1)
    r1 = parse_step(t1)
    # second box translated so its (0,0,0) corner coincides with box1's (10,10,10)
    b2 = _extrude("box2", [(10, 10), (20, 10), (20, 20), (10, 20)], None, 10, 20)
    t2 = write_step(b2)
    r2 = parse_step(t2)
    # merge record id spaces
    off = max_id(r1)
    merged = dict(r1)
    for rid, rec in r2.items():
        nrec = Record(rid + off, rec.type,
                      [_shift(a, off) for a in rec.args])
        merged[nrec.id] = nrec
    # keep both MANIFOLD_SOLID_BREP roots (two solids in one file)
    return serialize(merged, name)


def _shift(a, off):
    if isinstance(a, Ref):
        return Ref(a.id + off)
    if isinstance(a, list):
        return [_shift(x, off) for x in a]
    return a


# ------------------------------------------------------------------------------
def generate_fixtures(out_dir: str) -> dict:
    fdir = os.path.join(out_dir, "fixtures")
    os.makedirs(fdir, exist_ok=True)
    items = [
        ("fixture_crack", fixture_crack(), "crack_sub_tolerance", "flagged"),
        ("fixture_nonmanifold", fixture_nonmanifold(), "nonmanifold_edge", "malformed"),
        ("fixture_missingface", fixture_missingface(), "open_shell_euler", "malformed"),
    ]
    manifest = {"note": "analysis-only invalid/divergent detector test vectors",
                "parts": []}
    for pid, text, kind, expect in items:
        path = os.path.join(fdir, f"{pid}.step")
        with open(path, "w") as fh:
            fh.write(text)
        manifest["parts"].append({
            "id": pid, "path": os.path.relpath(path, out_dir),
            "sha256": sha256_bytes(text.encode()),
            "fixture_kind": kind, "expected_bucket": expect, "label": "adversarial",
        })
    with open(os.path.join(fdir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "brep_sentinel_out"
    m = generate_fixtures(out)
    print(f"generated {len(m['parts'])} adversarial fixtures")
