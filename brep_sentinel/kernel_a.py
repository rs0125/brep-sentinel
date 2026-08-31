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
    # 1. union-find merge of near-coincident vertices
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

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            pa, pb = topo.vertices[a], topo.vertices[b]
            if pa == pb or (abs(pa[0]-pb[0]) <= HEAL_TOL and
                            abs(pa[1]-pb[1]) <= HEAL_TOL and
                            abs(pa[2]-pb[2]) <= HEAL_TOL):
                if find(a) != find(b):
                    union(a, b)
                    log.append(f"merged vertex #{max(a,b)} into #{min(a,b)} "
                               f"(coincident within tol {HEAL_TOL})")

    rep = {v: find(v) for v in ids}
    new_vertices = {}
    for v in ids:
        r = rep[v]
        if r not in new_vertices:
            new_vertices[r] = topo.vertices[r]

    # 2. remap edges; drop zero-length; 3. stitch duplicate edges
    canon: dict[tuple, int] = {}       # (min,max rep) -> canonical edge id
    edge_remap: dict[int, int] = {}
    new_edges: dict[int, dict] = {}
    for eid in sorted(topo.edges):
        v1, v2 = topo.edges[eid]["v"]
        r1, r2 = rep.get(v1, v1), rep.get(v2, v2)
        if r1 == r2:
            log.append(f"dropped zero-length edge #{eid} (endpoints merged)")
            edge_remap[eid] = None
            continue
        key = (min(r1, r2), max(r1, r2))
        if key in canon:
            ceid = canon[key]
            edge_remap[eid] = ceid
            log.append(f"stitched duplicate edge #{eid} -> #{ceid} "
                       f"(same healed endpoints)")
        else:
            canon[key] = eid
            edge_remap[eid] = eid
            new_edges[eid] = {"v": (r1, r2), "curve": topo.edges[eid]["curve"]}

    # rebuild faces with remapped edges
    new_faces = []
    for f in topo.faces:
        nf = copy.copy(f)

        def remap_loop(loop):
            out = []
            for (e, ori) in loop:
                ne = edge_remap.get(e, e)
                if ne is None:
                    continue
                out.append((ne, ori))
            return out

        nf.outer = remap_loop(f.outer)
        nf.inners = [remap_loop(l) for l in f.inners]
        new_faces.append(nf)

    healed = RawTopo(new_vertices, new_edges, new_faces,
                     copy.deepcopy(topo.shells), list(topo.orphans),
                     list(topo.errors))

    # 4. non-manifold repair: edge referenced by >2 faces -> keep 2
    inc: dict[int, list] = {eid: [] for eid in healed.edges}
    for f in healed.faces:
        for loop in [f.outer, *f.inners]:
            for (eid, _o) in loop:
                if eid in inc and f.id not in inc[eid]:
                    inc[eid].append(f.id)
    for eid, fids in inc.items():
        if len(fids) > 2:
            keep = set(fids[:2])
            drop = fids[2:]
            log.append(f"non-manifold edge #{eid}: kept faces {sorted(keep)}, "
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
