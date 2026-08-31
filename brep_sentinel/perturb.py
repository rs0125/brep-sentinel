"""Stage 6 -- test-input generator: STRUCTURALLY VALID PERTURBATIONS ONLY.

Per the brief, every file produced here is a well-formed, inert, spec-conforming
STEP solid. We NEVER emit malformed topology references, crafted length/count
fields, degenerate entities, or anything designed to crash/misparse/heal a
kernel into a different solid. Two sanctioned classes:

  benign_redundancy  -- duplicate-but-consistent entities, reordered adjacency
                        lists, extra unreferenced records. Topology is unchanged;
                        the file is merely non-canonical.
  geometric_weakening -- internal void, reduced wall thickness, reentrant notch,
                        produced by legitimate modeling ops and re-exported as
                        valid STEP. The SOLID is weakened but the FILE is valid.

This corpus is primarily a FALSE-POSITIVE stress test: a good detector must NOT
flag any of it as adversarial. (Whether the geometric-weakening solids are
*topologically* invisible to invariant adjudication is exactly the honest
finding the report discusses -- see advisory.py for the complementary geometric
check.)
"""
from __future__ import annotations

import json
import os

from .common import sha256_bytes
from .step_parser import (Record, Ref, parse_step, serialize, max_id,
                          find_roots)
from .step_model import Solid, write_step
from .corpus.generate import _extrude, _rect


# ------------------------------------------------------------------------------
# Benign redundancy (text/graph level; topology invariant).
# ------------------------------------------------------------------------------
def benign_reordered(text: str, name: str) -> str:
    """Cyclically rotate every EDGE_LOOP and rotate CLOSED_SHELL face order.
    Cyclic rotation of a loop is the SAME loop; face order is a set -> identical
    solid, non-canonical serialization."""
    recs = parse_step(text)
    for r in recs.values():
        if r.type == "EDGE_LOOP" and r.args and isinstance(r.args[1], list):
            lst = r.args[1]
            if len(lst) > 1:
                r.args[1] = lst[1:] + lst[:1]
        elif r.type == "CLOSED_SHELL" and len(r.args) > 1 and isinstance(r.args[1], list):
            lst = r.args[1]
            if len(lst) > 1:
                r.args[1] = lst[1:] + lst[:1]
    return serialize(recs, name)


def benign_duplicated(text: str, name: str) -> str:
    """Duplicate consistent CARTESIAN_POINT entities (unreferenced) -- redundant
    but harmless."""
    recs = parse_step(text)
    nid = max_id(recs)
    dups = {}
    for r in list(recs.values()):
        if r.type == "CARTESIAN_POINT" and len(dups) < 8:
            nid += 1
            dups[nid] = Record(nid, "CARTESIAN_POINT", [x for x in r.args])
    recs.update(dups)
    return serialize(recs, name)


def benign_orphans(text: str, name: str) -> str:
    """Append extra unreferenced records + a comment (non-canonical padding)."""
    recs = parse_step(text)
    nid = max_id(recs)
    extra = []
    for k in range(6):
        nid += 1
        extra.append(f"#{nid}=CARTESIAN_POINT('scratch',({k}.0,{k}.0,{k}.0));")
    extra.append("/* benign non-canonical padding: unreferenced scratch records */")
    return serialize(recs, name, extra_lines=extra)


# ------------------------------------------------------------------------------
# Geometric weakening (model level; VALID solids, weakened geometry).
# ------------------------------------------------------------------------------
def weakening_void(w=20.0, d=20.0, h=20.0, t=4.0, name="wk_void") -> str:
    """Solid block with a fully-enclosed internal void (cavity). Valid 2-shell
    solid (BREP_WITH_VOIDS); mass/strength reduced, file well-formed."""
    outer = _extrude(name, _rect(w, d), None, 0, h)   # outer shell solid
    # build an inner void box (inverted) inside, as a second shell
    s = outer
    # inner cavity corners
    x0, y0, z0 = w * 0.3, d * 0.3, h * 0.3
    x1, y1, z1 = w * 0.7, d * 0.7, h * 0.7
    P = {}
    for (x, y, z) in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                      (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]:
        P[(x, y, z)] = s.add_vertex(x, y, z)
    v = list(P.values())
    b0, b1, b2, b3, t0, t1, t2, t3 = v
    edge_of = {}

    def E(a, b):
        k = frozenset((a, b))
        if k not in edge_of:
            edge_of[k] = (s.add_edge(a, b), (a, b))
        eid, sd = edge_of[k]
        return eid, sd == (a, b)

    def loop(seq):
        return [E(seq[i], seq[(i + 1) % len(seq)]) for i in range(len(seq))]

    # void faces: normals point INTO the material (outward from the cavity),
    # i.e. reversed relative to a normal outer box, marking it as a void.
    fids = []
    fids.append(s.add_face(loop([b0, b3, b2, b1]), normal=(0, 0, 1)))    # bottom
    fids.append(s.add_face(loop([t0, t1, t2, t3]), normal=(0, 0, -1)))   # top
    fids.append(s.add_face(loop([b0, b1, t1, t0]), normal=(0, 1, 0)))
    fids.append(s.add_face(loop([b1, b2, t2, t1]), normal=(-1, 0, 0)))
    fids.append(s.add_face(loop([b2, b3, t3, t2]), normal=(0, -1, 0)))
    fids.append(s.add_face(loop([b3, b0, t0, t3]), normal=(1, 0, 0)))
    s.add_shell(fids, kind="void")
    return write_step(s)


def weakening_thinwall(name="wk_thinwall") -> str:
    """Block with a through-hole placed off-center so one wall is very thin.
    Valid genus-1 solid."""
    w, d, h = 30.0, 20.0, 10.0
    hole = [(1.0, 8.0), (9.0, 8.0), (9.0, 12.0), (1.0, 12.0)]  # 1.0 mm wall on -x
    s = _extrude(name, _rect(w, d), [hole], 0, h)
    return write_step(s)


def weakening_notch(name="wk_notch") -> str:
    """Block with a sharp reentrant notch cut into a face (stress concentrator).
    Valid genus-0 solid."""
    # rectangle with a thin V-ish rectangular notch on the top edge
    prof = [(0, 0), (20, 0), (20, 10), (11, 10),
            (10.5, 4.0), (9.5, 4.0), (9, 10), (0, 10)]
    s = _extrude(name, prof, None, 0, 8)
    return write_step(s)


# ------------------------------------------------------------------------------
# Driver.
# ------------------------------------------------------------------------------
def generate_perturbations(out_dir: str) -> dict:
    clean_dir = os.path.join(out_dir, "corpus", "clean")
    pdir = os.path.join(out_dir, "perturbed")
    os.makedirs(pdir, exist_ok=True)
    manifest = {"note": "structurally VALID perturbations only", "parts": []}

    def emit(pid, text, ptype, base):
        path = os.path.join(pdir, f"{pid}.step")
        with open(path, "w") as fh:
            fh.write(text)
        manifest["parts"].append({
            "id": pid, "path": os.path.relpath(path, out_dir),
            "sha256": sha256_bytes(text.encode()),
            "perturbation_type": ptype, "base": base, "label": "perturbed",
        })

    # benign redundancy on a spread of clean bases
    bases = ["box_00", "holed_00", "lblock_00", "hexprism_00", "prism_00",
             "ublock_00", "holed2_00", "box_04"]
    for b in bases:
        txt = open(os.path.join(clean_dir, f"{b}.step")).read()
        emit(f"benign_reordered__{b}", benign_reordered(txt, f"benign_reordered__{b}"),
             "benign_reordered", b)
        emit(f"benign_duplicated__{b}", benign_duplicated(txt, f"benign_duplicated__{b}"),
             "benign_duplicated", b)
        emit(f"benign_orphans__{b}", benign_orphans(txt, f"benign_orphans__{b}"),
             "benign_orphans", b)

    # geometric weakening (valid solids)
    emit("weakening_void__00", weakening_void(name="weakening_void__00"),
         "weakening_void", "synthetic_box")
    emit("weakening_void__01", weakening_void(24, 18, 16, name="weakening_void__01"),
         "weakening_void", "synthetic_box")
    emit("weakening_thinwall__00", weakening_thinwall("weakening_thinwall__00"),
         "weakening_thinwall", "synthetic_holed")
    emit("weakening_notch__00", weakening_notch("weakening_notch__00"),
         "weakening_notch", "synthetic_block")

    with open(os.path.join(pdir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "brep_sentinel_out"
    m = generate_perturbations(out)
    print(f"generated {len(m['parts'])} perturbed parts")
    from collections import Counter
    print(dict(Counter(p["perturbation_type"] for p in m["parts"])))
