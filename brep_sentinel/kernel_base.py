"""Shared, geometry-free topology reconstruction from a parsed STEP graph.

Produces a RAW topology (vertices with coords keyed by VERTEX_POINT record id,
edges keyed by EDGE_CURVE record id, faces with oriented-edge loops, shells).
The two kernels consume this raw topology and differ only in interpretation:

    - kernel_b (strict)   : take the graph literally, no merging/healing.
    - kernel_a (tolerant) : merge near-coincident vertices, stitch duplicate
                            edges, drop degeneracies -- like a forgiving CAD
                            kernel's healing pass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .step_parser import Record, Ref, parse_step, find_roots, referenced_ids


@dataclass
class RawFace:
    id: int
    surface_type: str
    normal: list
    sense: bool
    outer: list          # [(edge_curve_id, orientation_bool), ...]
    inners: list         # [[(edge_curve_id, ori), ...], ...]


@dataclass
class RawTopo:
    vertices: dict          # vpoint_id -> (x,y,z)
    edges: dict             # ecurve_id -> {"v": (v1_id, v2_id), "curve": str}
    faces: list             # list[RawFace]
    shells: list            # [{"id":int,"kind":str,"face_ids":[ecurve... no, face ids]}]
    orphans: list           # unreferenced record ids
    errors: list


def _ref(x):
    return x.id if isinstance(x, Ref) else None


def reconstruct(records: dict[int, Record]) -> RawTopo:
    errors: list[str] = []
    vertices: dict[int, tuple] = {}
    edges: dict[int, dict] = {}
    faces: list[RawFace] = []
    shells: list[dict] = []

    def point_xyz(pt_id) -> tuple:
        r = records.get(pt_id)
        if r is None or r.type != "CARTESIAN_POINT":
            return (0.0, 0.0, 0.0)
        coords = r.args[1] if len(r.args) > 1 else r.args[0]
        vals = [float(c) for c in coords if isinstance(c, (int, float))]
        while len(vals) < 3:
            vals.append(0.0)
        return tuple(vals[:3])

    def vertex(vp_id) -> int:
        r = records.get(vp_id)
        if r is None:
            errors.append(f"missing VERTEX_POINT #{vp_id}")
            return vp_id
        pt = _ref(r.args[1]) if len(r.args) > 1 else None
        if vp_id not in vertices:
            vertices[vp_id] = point_xyz(pt)
        return vp_id

    def edge_curve(ec_id) -> int:
        r = records.get(ec_id)
        if r is None:
            errors.append(f"missing EDGE_CURVE #{ec_id}")
            return ec_id
        if ec_id in edges:
            return ec_id
        v1 = vertex(_ref(r.args[1]))
        v2 = vertex(_ref(r.args[2]))
        curve_id = _ref(r.args[3])
        cr = records.get(curve_id)
        ctype = "line"
        if cr is not None:
            ctype = {"LINE": "line", "CIRCLE": "circle",
                     "B_SPLINE_CURVE_WITH_KNOTS": "spline"}.get(cr.type, cr.type.lower())
        edges[ec_id] = {"v": (v1, v2), "curve": ctype}
        return ec_id

    def loop_edges(loop_id) -> list:
        r = records.get(loop_id)
        if r is None or r.type != "EDGE_LOOP":
            errors.append(f"bad EDGE_LOOP #{loop_id}")
            return []
        out = []
        for oe in r.args[1] if r.args and isinstance(r.args[1], list) else []:
            oer = records.get(_ref(oe))
            if oer is None or oer.type != "ORIENTED_EDGE":
                continue
            ec = _ref(oer.args[3])
            ori = oer.args[4]
            ori = bool(ori) if isinstance(ori, bool) else True
            out.append((edge_curve(ec), ori))
        return out

    def face(face_id) -> RawFace:
        r = records[face_id]
        bounds = r.args[1] if isinstance(r.args[1], list) else []
        outer, inners = [], []
        for b in bounds:
            br = records.get(_ref(b))
            if br is None:
                continue
            le = loop_edges(_ref(br.args[1]))
            if br.type == "FACE_OUTER_BOUND":
                outer = le
            else:
                inners.append(le)
        if not outer and inners:
            outer = inners.pop(0)
        plane_id = _ref(r.args[2]) if len(r.args) > 2 else None
        pr = records.get(plane_id)
        stype = "plane"
        normal = [0.0, 0.0, 1.0]
        if pr is not None:
            stype = {"PLANE": "plane", "CYLINDRICAL_SURFACE": "cylinder",
                     "CONICAL_SURFACE": "cone", "SPHERICAL_SURFACE": "sphere",
                     "B_SPLINE_SURFACE_WITH_KNOTS": "spline"}.get(pr.type, pr.type.lower())
            place = records.get(_ref(pr.args[1])) if len(pr.args) > 1 else None
            if place is not None and len(place.args) > 2:
                axis = records.get(_ref(place.args[2]))
                if axis is not None and axis.type == "DIRECTION":
                    normal = [float(c) for c in axis.args[1]
                              if isinstance(c, (int, float))]
        sense = r.args[3] if len(r.args) > 3 else True
        sense = bool(sense) if isinstance(sense, bool) else True
        return RawFace(face_id, stype, normal, sense, outer, inners)

    def shell(shell_id, kind) -> None:
        r = records.get(shell_id)
        if r is None or r.type not in ("CLOSED_SHELL", "OPEN_SHELL"):
            errors.append(f"bad shell #{shell_id}")
            return
        face_ids = []
        for f in r.args[1] if isinstance(r.args[1], list) else []:
            fid = _ref(f)
            fr = records.get(fid)
            if fr is not None and fr.type in ("ADVANCED_FACE", "FACE_SURFACE"):
                faces.append(face(fid))
                face_ids.append(fid)
        shells.append({"id": shell_id, "kind": kind, "face_ids": face_ids,
                       "declared": r.type})

    roots = find_roots(records)
    if not roots:
        errors.append("no solid root (MANIFOLD_SOLID_BREP/BREP_WITH_VOIDS)")
    for root in roots:
        rr = records[root]
        if rr.type == "MANIFOLD_SOLID_BREP":
            shell(_ref(rr.args[1]), "outer")
        elif rr.type == "BREP_WITH_VOIDS":
            shell(_ref(rr.args[1]), "outer")
            for v in rr.args[2] if isinstance(rr.args[2], list) else []:
                shell(_ref(v), "void")

    orphans = sorted(set(records) - referenced_ids(records) - set(roots))
    return RawTopo(vertices, edges, faces, shells, orphans, errors)


def edge_length(topo: RawTopo, ec_id: int) -> float:
    v1, v2 = topo.edges[ec_id]["v"]
    p1, p2 = topo.vertices.get(v1, (0, 0, 0)), topo.vertices.get(v2, (0, 0, 0))
    return math.dist(p1, p2)


# ------------------------------------------------------------------------------
# Descriptor construction (shared by both kernels).
# ------------------------------------------------------------------------------
def _loop_vertices(topo: RawTopo, loop: list) -> list:
    verts = []
    for (eid, ori) in loop:
        if eid not in topo.edges:
            continue
        v1, v2 = topo.edges[eid]["v"]
        verts.append(v1 if ori else v2)
    return verts


def _poly_area(pts: list) -> float:
    if len(pts) < 3:
        return 0.0
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1, z1 = pts[i]
        x2, y2, z2 = pts[(i + 1) % n]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def build_descriptor(topo: RawTopo, *, source_file: str, file_sha256: str,
                     kernel_name: str, kernel_version: str,
                     healing_enabled: bool, healing_log: list | None = None):
    from .common import Descriptor, VertexD, EdgeD, FaceD, ShellD

    # global edge -> distinct face incidence
    inc: dict[int, list] = {eid: [] for eid in topo.edges}
    for f in topo.faces:
        for loop in [f.outer, *f.inners]:
            for (eid, _ori) in loop:
                if eid in inc and f.id not in inc[eid]:
                    inc[eid].append(f.id)

    # per-edge uses (face_id, orientation) across all loops -- carries the
    # orientation needed by the coherence invariant.
    edge_uses: dict = {eid: [] for eid in topo.edges}
    for f in sorted(topo.faces, key=lambda x: x.id):
        for loop in [f.outer, *f.inners]:
            for (eid, ori) in loop:
                if eid in edge_uses:
                    edge_uses[eid].append([f.id, bool(ori)])

    vertices = [VertexD(id=vid, xyz=[round(c, 9) for c in xyz])
                for vid, xyz in sorted(topo.vertices.items())]

    edges = []
    for eid in sorted(topo.edges):
        v1, v2 = topo.edges[eid]["v"]
        edges.append(EdgeD(id=eid, curve_type=topo.edges[eid]["curve"],
                           vertex_ids=[v1, v2],
                           length=round(edge_length(topo, eid), 9),
                           face_ids=sorted(inc.get(eid, []))))

    faces = []
    face_by_id = {}
    for f in sorted(topo.faces, key=lambda x: x.id):
        opts = [topo.vertices.get(v, (0, 0, 0)) for v in _loop_vertices(topo, f.outer)]
        area = _poly_area(opts)
        for inner in f.inners:
            ipts = [topo.vertices.get(v, (0, 0, 0)) for v in _loop_vertices(topo, inner)]
            area -= _poly_area(ipts)
        fd = FaceD(id=f.id, surface_type=f.surface_type, orientation=bool(f.sense),
                   outer_loop_edges=[e for (e, _o) in f.outer],
                   inner_loops=[[e for (e, _o) in inner] for inner in f.inners],
                   area=round(abs(area), 9), normal=[round(c, 6) for c in f.normal])
        faces.append(fd)
        face_by_id[f.id] = fd

    shells = []
    for sh in topo.shells:
        use: dict[int, int] = {}
        for fid in sh["face_ids"]:
            fd = face_by_id.get(fid)
            if fd is None:
                continue
            for loop in [fd.outer_loop_edges, *fd.inner_loops]:
                for eid in loop:
                    use[eid] = use.get(eid, 0) + 1
        closed = bool(use) and all(c == 2 for c in use.values())
        shells.append(ShellD(id=sh["id"], kind=sh["kind"],
                             face_ids=sorted(sh["face_ids"]), closed=closed))

    return Descriptor(
        source_file=source_file, file_sha256=file_sha256,
        kernel_name=kernel_name, kernel_version=kernel_version,
        healing_enabled=healing_enabled,
        vertices=vertices, edges=edges, faces=faces, shells=shells,
        healing_log=list(healing_log or []),
        parse_errors=list(topo.errors),
        edge_uses=edge_uses,
    )
