"""Stage 4 -- per-descriptor validity report from topological invariants.

Given ONE descriptor (from either kernel), independently evaluate the four
B-rep validity invariants and emit a structured report. These are the
mathematical "checksums" a well-formed solid must satisfy; a failure localizes
*where* and *how* the topology is wrong. The adjudicator (stage 5) uses these
reports to decide which kernel's interpretation, if any, is invalid.

Invariants:
  1. euler_poincare       V - E + F - R = 2(S - H), checked per shell:
                          chi_s = V_s - E_s + F_s - R_s must be even and imply
                          genus H_s >= 0.
  2. shell_closure        every edge in a shell is used by exactly two of that
                          shell's faces (watertight).
  3. orientation_coherence each shared manifold edge is traversed once forward
                          and once backward by its two faces (consistent normals).
  4. degeneracy           no zero-length edges, no zero-area faces, no edges with
                          face-incidence != 2 (boundary or non-manifold).
"""
from __future__ import annotations

from .common import Descriptor

ZERO_LEN = 1e-9
ZERO_AREA = 1e-9


def _shell_partition(desc: Descriptor):
    """Map each shell -> (faces, edges, vertices, inner-loop count) it spans."""
    face_by_id = {f.id: f for f in desc.faces}
    out = []
    for sh in desc.shells:
        faces = [face_by_id[fid] for fid in sh.face_ids if fid in face_by_id]
        edges: set[int] = set()
        rings = 0
        for f in faces:
            edges.update(f.outer_loop_edges)
            for loop in f.inner_loops:
                edges.update(loop)
            rings += len(f.inner_loops)
        edge_by_id = {e.id: e for e in desc.edges}
        verts: set[int] = set()
        for eid in edges:
            e = edge_by_id.get(eid)
            if e:
                verts.update(e.vertex_ids)
        out.append({"shell": sh, "F": len(faces), "E": len(edges),
                    "V": len(verts), "R": rings, "faces": faces, "edges": edges})
    return out


def check_euler(desc: Descriptor) -> dict:
    parts = _shell_partition(desc)
    shells_report = []
    holds = True
    for p in parts:
        chi = p["V"] - p["E"] + p["F"] - p["R"]
        even = (chi % 2 == 0)
        H = (2 - chi) // 2 if even else None      # per connected shell: chi=2(1-H)
        ok = even and H is not None and H >= 0
        holds = holds and ok
        shells_report.append({
            "shell_id": p["shell"].id, "kind": p["shell"].kind,
            "V": p["V"], "E": p["E"], "F": p["F"], "R": p["R"],
            "chi": chi, "even": even, "genus_implied": H, "ok": ok,
        })
    if not parts:
        holds = False
    return {"holds": holds, "per_shell": shells_report,
            "detail": "V-E+F-R=2(S-H) per shell" if holds
                      else "Euler-Poincare violated (parity or negative genus)"}


def check_closure(desc: Descriptor) -> dict:
    open_shells = []
    for sh in desc.shells:
        if not sh.closed:
            # find boundary edges of this shell
            use: dict[int, int] = {}
            face_by_id = {f.id: f for f in desc.faces}
            for fid in sh.face_ids:
                f = face_by_id.get(fid)
                if not f:
                    continue
                for loop in [f.outer_loop_edges, *f.inner_loops]:
                    for eid in loop:
                        use[eid] = use.get(eid, 0) + 1
            boundary = sorted(e for e, c in use.items() if c != 2)
            open_shells.append({"shell_id": sh.id, "boundary_edges": boundary})
    holds = len(open_shells) == 0 and len(desc.shells) > 0
    return {"holds": holds, "open_shells": open_shells,
            "detail": "all shells watertight" if holds
                      else "open shell(s): edges not shared by exactly 2 faces"}


def check_orientation(desc: Descriptor) -> dict:
    bad = []
    for eid, uses in desc.edge_uses.items():
        if len(uses) == 2:
            (_f1, o1), (_f2, o2) = uses
            if o1 == o2:
                bad.append({"edge_id": eid, "faces": [uses[0][0], uses[1][0]],
                            "orientations": [o1, o2]})
    holds = len(bad) == 0
    return {"holds": holds, "incoherent_edges": bad,
            "detail": "shared edges oppositely oriented" if holds
                      else "orientation clash on shared edge(s) (inconsistent normals)"}


def check_degeneracy(desc: Descriptor) -> dict:
    zero_len = [e.id for e in desc.edges if e.length <= ZERO_LEN]
    zero_area = [f.id for f in desc.faces if f.area <= ZERO_AREA]
    boundary_edges, nonmanifold = [], []
    for eid, uses in desc.edge_uses.items():
        n = len({u[0] for u in uses})
        if n < 2:
            boundary_edges.append(eid)
        elif n > 2:
            nonmanifold.append({"edge_id": eid, "incidence": n,
                                "faces": sorted({u[0] for u in uses})})
    holds = not (zero_len or zero_area or boundary_edges or nonmanifold)
    return {"holds": holds,
            "zero_length_edges": sorted(zero_len),
            "zero_area_faces": sorted(zero_area),
            "boundary_edges": sorted(boundary_edges),
            "nonmanifold_edges": nonmanifold,
            "detail": "no degenerate entities" if holds
                      else "degenerate/irregular entities present"}


def validity_report(desc: Descriptor) -> dict:
    inv = {
        "euler_poincare": check_euler(desc),
        "shell_closure": check_closure(desc),
        "orientation_coherence": check_orientation(desc),
        "degeneracy": check_degeneracy(desc),
    }
    failures = [k for k, v in inv.items() if not v["holds"]]
    return {
        "kernel_name": desc.kernel_name,
        "kernel_version": desc.kernel_version,
        "source_file": desc.source_file,
        "file_sha256": desc.file_sha256,
        "counts": desc.counts(),
        "invariants": inv,
        "failures": failures,
        "valid": len(failures) == 0 and not desc.parse_errors,
        "parse_errors": desc.parse_errors,
    }


if __name__ == "__main__":
    import json
    import sys
    from . import kernel_b
    d = kernel_b.load(sys.argv[1])
    print(json.dumps(validity_report(d), indent=2))
