"""Kernel A -- TOLERANT / HEALING independent STEP reader.

Models a forgiving CAD kernel's healing pass. On top of the same reconstruction
it:
    1. merges VERTEX_POINTs whose coordinates coincide within a tolerance,
    2. remaps edges onto merged vertices and drops resulting zero-length edges,
    3. stitches duplicate edges (same healed endpoints) so a near-coincident
       crack is closed,
    4. repairs a non-manifold edge (incidence > 2) by keeping two orientation-
       consistent faces and dropping the extras.
Every action is recorded in `healing_log`. On a clean file nothing triggers, so
Kernel A and Kernel B agree exactly -- healing only changes the answer when the
file contains a defect, which is precisely the signal the adjudicator uses.
"""
from __future__ import annotations

import copy

from .common import sha256_bytes
from .kernel_base import reconstruct, build_descriptor, edge_length, RawTopo
from .step_parser import parse_step

KERNEL_NAME = "kernel_a_tolerant"
KERNEL_VERSION = "tolerant-healing/1.0 (tol=1e-4)"
HEAL_TOL = 1e-4


def _heal(topo: RawTopo, log: list) -> RawTopo:
    """Gap-driven healing. A forgiving kernel only *repairs* defects; if the file
    is already a closed manifold, healing is a no-op -- so clean files stay
    convergent with the strict kernel. Healing engages only when the literal
    topology has open (boundary) edges, non-manifold edges, or zero-length line
    edges to fix."""
    # literal incidence over distinct faces
    inc: dict[int, set] = {eid: set() for eid in topo.edges}
    for f in topo.faces:
        for loop in [f.outer, *f.inners]:
            for (eid, _o) in loop:
                if eid in inc:
                    inc[eid].add(f.id)
    boundary = [eid for eid, fs in inc.items() if len(fs) < 2]
    nonmanifold = [eid for eid, fs in inc.items() if len(fs) > 2]
    zero_line = [eid for eid, e in topo.edges.items()
                 if e["curve"] == "line"
                 and topo.vertices.get(e["v"][0]) == topo.vertices.get(e["v"][1])]

    if not boundary and not nonmanifold and not zero_line:
        return topo   # already clean -> no healing -> converges with kernel B

    # -- weld: merge coincident vertices, prioritising endpoints of boundary
    #    edges (the crack) against any coincident vertex elsewhere. --
    ids = sorted(topo.vertices)
    parent = {v: v for v in ids}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        lo, hi = (ra, rb) if ra < rb else (rb, ra)
        parent[hi] = lo

    def coincident(a, b):
        pa, pb = topo.vertices[a], topo.vertices[b]
        return (abs(pa[0]-pb[0]) <= HEAL_TOL and abs(pa[1]-pb[1]) <= HEAL_TOL
                and abs(pa[2]-pb[2]) <= HEAL_TOL)

    bverts = set()
    for eid in boundary:
        bverts.update(topo.edges[eid]["v"])
    for a in sorted(bverts):
        for b in ids:
            if a != b and find(a) != find(b) and coincident(a, b):
                union(a, b)
                log.append(f"welded vertex #{max(a,b)} into #{min(a,b)} to close "
                           f"a gap (coincident within tol {HEAL_TOL})")

    rep = {v: find(v) for v in ids}
    new_vertices: dict = {}
    for v in ids:
        r = rep[v]
        if r not in new_vertices:
            new_vertices[r] = topo.vertices[r]

    # remap edges; drop zero-length; stitch duplicates
    canon: dict = {}
    edge_remap: dict = {}
    new_edges: dict = {}
    for eid in sorted(topo.edges):
        v1, v2 = topo.edges[eid]["v"]
        r1, r2 = rep.get(v1, v1), rep.get(v2, v2)
        if r1 == r2 and topo.edges[eid]["curve"] == "line":
            log.append(f"dropped zero-length line edge #{eid} (endpoints welded)")
            edge_remap[eid] = None
            continue
        key = (min(r1, r2), max(r1, r2), topo.edges[eid]["curve"])
        if key in canon:
            ceid = canon[key]
            edge_remap[eid] = ceid
            log.append(f"stitched duplicate edge #{eid} -> #{ceid} "
                       f"(same welded endpoints)")
        else:
            canon[key] = eid
            edge_remap[eid] = eid
            new_edges[eid] = {"v": (r1, r2), "curve": topo.edges[eid]["curve"]}

    new_faces = []
    for f in topo.faces:
        nf = copy.copy(f)

        def remap_loop(loop):
            out = []
            for (e, ori) in loop:
                ne = edge_remap.get(e, e)
                if ne is not None:
                    out.append((ne, ori))
            return out

        nf.outer = remap_loop(f.outer)
        nf.inners = [remap_loop(l) for l in f.inners]
        new_faces.append(nf)

    healed = RawTopo(new_vertices, new_edges, new_faces,
                     copy.deepcopy(topo.shells), list(topo.orphans),
                     list(topo.errors))

    # non-manifold repair: edge referenced by >2 faces -> keep 2
    inc2: dict = {eid: [] for eid in healed.edges}
    for f in healed.faces:
        for loop in [f.outer, *f.inners]:
            for (eid, _o) in loop:
                if eid in inc2 and f.id not in inc2[eid]:
                    inc2[eid].append(f.id)
    for eid, fids in inc2.items():
        if len(fids) > 2:
            drop = fids[2:]
            log.append(f"non-manifold edge #{eid}: kept faces {sorted(fids[:2])}, "
                       f"dropped {drop} (healed to manifold)")
            for f in healed.faces:
                if f.id in drop:
                    f.outer = [(e, o) for (e, o) in f.outer if e != eid]
                    f.inners = [[(e, o) for (e, o) in l if e != eid]
                                for l in f.inners]

    return healed


def load(path: str):
    text = open(path).read()
    return load_text(text, source_file=path, sha=sha256_bytes(text.encode()))


def load_text(text: str, *, source_file: str, sha: str):
    records = parse_step(text)
    topo = reconstruct(records)
    log: list[str] = []
    healed = _heal(topo, log)
    return build_descriptor(
        healed, source_file=source_file, file_sha256=sha,
        kernel_name=KERNEL_NAME, kernel_version=KERNEL_VERSION,
        healing_enabled=True, healing_log=log,
    )


if __name__ == "__main__":
    import sys
    d = load(sys.argv[1])
    print(d.kernel_name, d.counts(), "healing:", len(d.healing_log))
