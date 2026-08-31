"""Infect real STEP files with the detector's target anomaly classes.

These transforms operate on an arbitrary parsed STEP entity graph (so they work
on downloaded real CAD models, not just the synthetic corpus). Every output is
INERT: the "infection" is a topology-graph anomaly that makes the file
*detectably malformed or kernel-divergent*, NOT a memory-corruption/RCE payload.
No crafted length/count fields, no crash triggers -- consistent with the
project's stated policy. The point is to prove detection on realistic input.

Classes:
  crack        sub-tolerance crack: clone a shared vertex at +delta and rewire
              one incident face -> literal reading is an open shell; a tolerant
              kernel silently heals it shut into a different solid. => FLAGGED
  nonmanifold  add an internal fin reusing an existing edge -> edge incidence 3.
              => MALFORMED
  missingface  delete one face from a closed shell -> open shell / Euler break.
              => MALFORMED
  void         wrap a solid's shell in BREP_WITH_VOIDS with an added enclosed
              cavity -> valid solid, weakened geometry (invariant-invisible;
              caught by the geometric advisory). => CLEAN + advisory
  benign       reorder adjacency / duplicate consistent entities -> non-canonical
              but valid. => CLEAN  (false-positive control)
"""
from __future__ import annotations

from .step_parser import (Record, Ref, parse_step, serialize, max_id, find_roots)
from .perturb import benign_reordered, benign_duplicated


def _new(recs, t, *a):
    nid = max_id(recs) + 1
    recs[nid] = Record(nid, t, list(a))
    return nid


def _point_of(recs, vp_id):
    r = recs[vp_id]
    cp = recs[r.args[1].id]
    return [float(c) for c in cp.args[1]]


def infect_crack(text: str, name: str, delta: float = 1e-6) -> str:
    recs = parse_step(text)
    vp_edges: dict[int, list[int]] = {}
    for r in recs.values():
        if r.type == "EDGE_CURVE":
            for vp in (r.args[1].id, r.args[2].id):
                vp_edges.setdefault(vp, []).append(r.id)

    def face_edges(fr):
        out = set()
        for b in fr.args[1]:
            br = recs.get(b.id)
            if br is None or not isinstance(br.args[1], Ref):
                continue
            loop = recs.get(br.args[1].id)
            if loop is None:
                continue
            for oe in loop.args[1]:
                oer = recs.get(oe.id)
                if oer and len(oer.args) > 3 and isinstance(oer.args[3], Ref):
                    out.add(oer.args[3].id)
        return out

    faces = [r for r in recs.values() if r.type == "ADVANCED_FACE"]
    target_vp = next(vp for vp, es in vp_edges.items() if len(es) >= 2)
    target_edges = set(vp_edges[target_vp])
    target_face = next(f for f in faces if face_edges(f) & target_edges)

    x, y, z = _point_of(recs, target_vp)
    new_cp = _new(recs, "CARTESIAN_POINT", "", [x + delta, y, z])
    new_vp = _new(recs, "VERTEX_POINT", "", Ref(new_cp))

    ec_remap: dict[int, int] = {}
    for ec in face_edges(target_face) & target_edges:
        r = recs[ec]
        v1, v2 = r.args[1].id, r.args[2].id
        nv1 = new_vp if v1 == target_vp else v1
        nv2 = new_vp if v2 == target_vp else v2
        nec = _new(recs, "EDGE_CURVE", "", Ref(nv1), Ref(nv2), r.args[3], r.args[4])
        ec_remap[ec] = nec

    for b in target_face.args[1]:
        loop = recs[recs[b.id].args[1].id]
        for oe in loop.args[1]:
            oer = recs[oe.id]
            if isinstance(oer.args[3], Ref) and oer.args[3].id in ec_remap:
                oer.args[3] = Ref(ec_remap[oer.args[3].id])
    return serialize(recs, name)


def infect_nonmanifold(text: str, name: str) -> str:
    recs = parse_step(text)
    ec = next(r for r in recs.values() if r.type == "EDGE_CURVE")
    v1, v2 = ec.args[1].id, ec.args[2].id
    p1, p2 = _point_of(recs, v1), _point_of(recs, v2)
    apex = [(p1[0] + p2[0]) / 2 + 1.0, (p1[1] + p2[1]) / 2 + 1.0,
            (p1[2] + p2[2]) / 2 + 1.0]
    ap = _new(recs, "CARTESIAN_POINT", "", apex)
    avp = _new(recs, "VERTEX_POINT", "", Ref(ap))

    def line_edge(a, b):
        base = _new(recs, "CARTESIAN_POINT", "", _point_of(recs, a))
        d = _new(recs, "DIRECTION", "", [1.0, 0.0, 0.0])
        vec = _new(recs, "VECTOR", "", Ref(d), 1.0)
        ln = _new(recs, "LINE", "", Ref(base), Ref(vec))
        return _new(recs, "EDGE_CURVE", "", Ref(a), Ref(b), Ref(ln), True)

    e1, e2 = line_edge(v1, avp), line_edge(avp, v2)
    oe1 = _new(recs, "ORIENTED_EDGE", "", "*", "*", Ref(e1), True)
    oe2 = _new(recs, "ORIENTED_EDGE", "", "*", "*", Ref(e2), True)
    oe3 = _new(recs, "ORIENTED_EDGE", "", "*", "*", Ref(ec.id), False)
    loop = _new(recs, "EDGE_LOOP", "", [Ref(oe1), Ref(oe2), Ref(oe3)])
    bound = _new(recs, "FACE_OUTER_BOUND", "", Ref(loop), True)
    plpt = _new(recs, "CARTESIAN_POINT", "", apex)
    axis = _new(recs, "DIRECTION", "", [0.0, 0.0, 1.0])
    refd = _new(recs, "DIRECTION", "", [1.0, 0.0, 0.0])
    place = _new(recs, "AXIS2_PLACEMENT_3D", "", Ref(plpt), Ref(axis), Ref(refd))
    plane = _new(recs, "PLANE", "", Ref(place))
    fin = _new(recs, "ADVANCED_FACE", "", [Ref(bound)], Ref(plane), True)
    shell = next(r for r in recs.values() if r.type == "CLOSED_SHELL")
    shell.args[1].append(Ref(fin))
    return serialize(recs, name)


def infect_missingface(text: str, name: str) -> str:
    recs = parse_step(text)
    shell = next(r for r in recs.values() if r.type == "CLOSED_SHELL"
                 and isinstance(r.args[1], list) and len(r.args[1]) > 1)
    shell.args[1] = shell.args[1][:-1]
    return serialize(recs, name)


def infect_void(text: str, name: str) -> str:
    """Add a fully-enclosed cavity inside the first solid and re-root it as
    BREP_WITH_VOIDS. Valid solid, weakened geometry (advisory catches it)."""
    recs = parse_step(text)
    root = next((r for r in recs.values() if r.type == "MANIFOLD_SOLID_BREP"), None)
    if root is None:
        return text
    outer_shell_ref = root.args[1]
    # bounding box from all cartesian points
    pts = [[float(c) for c in r.args[1]] for r in recs.values()
           if r.type == "CARTESIAN_POINT" and isinstance(r.args[1], list)
           and len(r.args[1]) == 3]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    ctr = [(lo[i] + hi[i]) / 2 for i in range(3)]
    ext = [(hi[i] - lo[i]) * 0.12 + 1e-6 for i in range(3)]
    c0 = [ctr[i] - ext[i] for i in range(3)]
    c1 = [ctr[i] + ext[i] for i in range(3)]

    corners = [(c0[0], c0[1], c0[2]), (c1[0], c0[1], c0[2]),
               (c1[0], c1[1], c0[2]), (c0[0], c1[1], c0[2]),
               (c0[0], c0[1], c1[2]), (c1[0], c0[1], c1[2]),
               (c1[0], c1[1], c1[2]), (c0[0], c1[1], c1[2])]
    vp = []
    for (x, y, z) in corners:
        cp = _new(recs, "CARTESIAN_POINT", "", [x, y, z])
        vp.append(_new(recs, "VERTEX_POINT", "", Ref(cp)))

    edge_of: dict = {}

    def edge(a, b):
        k = frozenset((a, b))
        if k not in edge_of:
            base = _new(recs, "CARTESIAN_POINT", "", _point_of(recs, a))
            d = _new(recs, "DIRECTION", "", [1.0, 0.0, 0.0])
            vec = _new(recs, "VECTOR", "", Ref(d), 1.0)
            ln = _new(recs, "LINE", "", Ref(base), Ref(vec))
            edge_of[k] = (_new(recs, "EDGE_CURVE", "", Ref(a), Ref(b), Ref(ln), True), (a, b))
        eid, sd = edge_of[k]
        return eid, sd == (a, b)

    def face(seq, normal):
        oes = []
        for i in range(len(seq)):
            a, b = seq[i], seq[(i + 1) % len(seq)]
            e, ori = edge(a, b)
            oes.append(_new(recs, "ORIENTED_EDGE", "", "*", "*", Ref(e), ori))
        loop = _new(recs, "EDGE_LOOP", "", [Ref(o) for o in oes])
        bound = _new(recs, "FACE_OUTER_BOUND", "", Ref(loop), True)
        plpt = _new(recs, "CARTESIAN_POINT", "", _point_of(recs, seq[0]))
        axis = _new(recs, "DIRECTION", "", [float(n) for n in normal])
        refd = _new(recs, "DIRECTION", "", [1.0, 0.0, 0.0] if abs(normal[0]) < 0.9
                    else [0.0, 1.0, 0.0])
        place = _new(recs, "AXIS2_PLACEMENT_3D", "", Ref(plpt), Ref(axis), Ref(refd))
        plane = _new(recs, "PLANE", "", Ref(place))
        return _new(recs, "ADVANCED_FACE", "", [Ref(bound)], Ref(plane), True)

    b0, b1, b2, b3, t0, t1, t2, t3 = vp
    fids = [face([b0, b3, b2, b1], (0, 0, 1)), face([t0, t1, t2, t3], (0, 0, -1)),
            face([b0, b1, t1, t0], (0, 1, 0)), face([b1, b2, t2, t1], (-1, 0, 0)),
            face([b2, b3, t3, t2], (0, -1, 0)), face([b3, b0, t0, t3], (1, 0, 0))]
    void_shell = _new(recs, "CLOSED_SHELL", "", [Ref(f) for f in fids])
    # re-root as BREP_WITH_VOIDS
    root.type = "BREP_WITH_VOIDS"
    root.args = [root.args[0], outer_shell_ref, [Ref(void_shell)]]
    return serialize(recs, name)


INFECTIONS = {
    "crack": infect_crack,
    "nonmanifold": infect_nonmanifold,
    "missingface": infect_missingface,
    "void": infect_void,
    "benign_reordered": benign_reordered,
    "benign_duplicated": benign_duplicated,
}

# expected adjudication bucket per infection (for scoring)
EXPECTED = {
    "crack": "flagged", "nonmanifold": "malformed", "missingface": "malformed",
    "void": "clean", "benign_reordered": "clean", "benign_duplicated": "clean",
}
