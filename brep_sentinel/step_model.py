"""In-memory B-rep solid model + a STEP (ISO 10303-21) writer.

We model planar-faced solids exactly (straight edges only), which is enough to
build a corpus with *known ground-truth topology* -- cubes, L-blocks, prisms,
blocks with through-holes (genus 1), and solids with enclosed voids (multi-shell).

The writer emits spec-shaped AP242-style entities (MANIFOLD_SOLID_BREP /
BREP_WITH_VOIDS -> CLOSED_SHELL -> ADVANCED_FACE -> FACE_OUTER_BOUND / FACE_BOUND
-> EDGE_LOOP -> ORIENTED_EDGE -> EDGE_CURVE -> VERTEX_POINT / LINE). The two
kernel readers consume this text; they never see the in-memory model.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field


# ------------------------------------------------------------------------------
# Geometry model (authoring side).
# ------------------------------------------------------------------------------
@dataclass
class MVertex:
    id: int
    xyz: tuple[float, float, float]


@dataclass
class MEdge:
    id: int
    v1: int
    v2: int


@dataclass
class MLoop:
    # ordered list of (edge_id, orientation_bool) forming a closed cycle
    oriented: list[tuple[int, bool]]


@dataclass
class MFace:
    id: int
    outer: MLoop
    inners: list[MLoop] = field(default_factory=list)
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    sense: bool = True


@dataclass
class MShell:
    id: int
    face_ids: list[int]
    kind: str = "outer"        # "outer" | "void"


class Solid:
    """Author-side solid: dictionaries of primitives + shells."""

    def __init__(self, name: str):
        self.name = name
        self.vertices: dict[int, MVertex] = {}
        self.edges: dict[int, MEdge] = {}
        self.faces: dict[int, MFace] = {}
        self.shells: list[MShell] = []
        self._ids = itertools.count(1)

    def nid(self) -> int:
        return next(self._ids)

    def add_vertex(self, x: float, y: float, z: float) -> int:
        i = self.nid()
        self.vertices[i] = MVertex(i, (float(x), float(y), float(z)))
        return i

    def add_edge(self, v1: int, v2: int) -> int:
        i = self.nid()
        self.edges[i] = MEdge(i, v1, v2)
        return i

    def add_face(self, outer: list[tuple[int, bool]],
                 inners: list[list[tuple[int, bool]]] | None = None,
                 normal=(0.0, 0.0, 1.0), sense=True) -> int:
        i = self.nid()
        self.faces[i] = MFace(
            i, MLoop(outer),
            [MLoop(l) for l in (inners or [])],
            tuple(float(c) for c in normal), sense,
        )
        return i

    def add_shell(self, face_ids: list[int], kind: str = "outer") -> int:
        i = self.nid()
        self.shells.append(MShell(i, list(face_ids), kind))
        return i

    # -- ground truth Euler-Poincare inputs (authoring side, exact) --
    def ground_truth(self) -> dict:
        V = len(self.vertices)
        E = len(self.edges)
        F = len(self.faces)
        S = len(self.shells)
        R = sum(len(f.inners) for f in self.faces.values())
        # V - E + F - R = 2(S - H)  ->  H = S - (V - E + F - R)/2
        H = S - (V - E + F - R) // 2
        return {"V": V, "E": E, "F": F, "S": S, "R": R, "H": H}


# ------------------------------------------------------------------------------
# STEP writer.
# ------------------------------------------------------------------------------
def _fnum(x: float) -> str:
    """STEP-friendly real literal."""
    if x == int(x):
        return f"{x:.1f}"
    return repr(float(x))


class StepWriter:
    def __init__(self, solid: Solid):
        self.solid = solid
        self.lines: list[str] = []
        self._n = itertools.count(1)
        self._id: dict[str, int] = {}   # dedup helper keyed by content

    def _emit(self, body: str, key: str | None = None) -> int:
        if key is not None and key in self._id:
            return self._id[key]
        n = next(self._n)
        self.lines.append(f"#{n}={body};")
        if key is not None:
            self._id[key] = n
        return n

    def write(self) -> str:
        s = self.solid
        # -- points, directions, vertices --
        vp: dict[int, int] = {}   # model vertex id -> VERTEX_POINT record id
        for v in s.vertices.values():
            x, y, z = v.xyz
            p = self._emit(f"CARTESIAN_POINT('',({_fnum(x)},{_fnum(y)},{_fnum(z)}))")
            vp[v.id] = self._emit(f"VERTEX_POINT('',#{p})")

        # -- edge curves (LINE geometry through the two vertices) --
        ec: dict[int, int] = {}   # model edge id -> EDGE_CURVE record id
        for e in s.edges.values():
            p1 = s.vertices[e.v1].xyz
            p2 = s.vertices[e.v2].xyz
            d = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
            L = math.sqrt(sum(c * c for c in d)) or 1.0
            u = tuple(c / L for c in d)
            base = self._emit(
                f"CARTESIAN_POINT('',({_fnum(p1[0])},{_fnum(p1[1])},{_fnum(p1[2])}))")
            dirn = self._emit(
                f"DIRECTION('',({_fnum(u[0])},{_fnum(u[1])},{_fnum(u[2])}))")
            vec = self._emit(f"VECTOR('',#{dirn},{_fnum(L)})")
            line = self._emit(f"LINE('',#{base},#{vec})")
            ec[e.id] = self._emit(
                f"EDGE_CURVE('',#{vp[e.v1]},#{vp[e.v2]},#{line},.T.)")

        # -- faces --
        face_rec: dict[int, int] = {}
        for f in s.faces.values():
            def loop_record(loop: MLoop) -> int:
                oes = []
                for (eid, ori) in loop.oriented:
                    flag = ".T." if ori else ".F."
                    oe = self._emit(f"ORIENTED_EDGE('',*,*,#{ec[eid]},{flag})")
                    oes.append(oe)
                refs = ",".join(f"#{o}" for o in oes)
                return self._emit(f"EDGE_LOOP('',({refs}))")

            outer_loop = loop_record(f.outer)
            bounds = [self._emit(f"FACE_OUTER_BOUND('',#{outer_loop},.T.)")]
            for inner in f.inners:
                il = loop_record(inner)
                bounds.append(self._emit(f"FACE_BOUND('',#{il},.T.)"))

            # plane placement
            ox, oy, oz = s.vertices[
                s.edges[f.outer.oriented[0][0]].v1].xyz
            op = self._emit(
                f"CARTESIAN_POINT('',({_fnum(ox)},{_fnum(oy)},{_fnum(oz)}))")
            axis = self._emit(
                f"DIRECTION('',({_fnum(f.normal[0])},{_fnum(f.normal[1])},{_fnum(f.normal[2])}))")
            # a reference direction not parallel to axis
            ref = (1.0, 0.0, 0.0)
            if abs(f.normal[0]) > 0.9:
                ref = (0.0, 1.0, 0.0)
            refd = self._emit(
                f"DIRECTION('',({_fnum(ref[0])},{_fnum(ref[1])},{_fnum(ref[2])}))")
            place = self._emit(f"AXIS2_PLACEMENT_3D('',#{op},#{axis},#{refd})")
            plane = self._emit(f"PLANE('',#{place})")
            bref = ",".join(f"#{b}" for b in bounds)
            sense = ".T." if f.sense else ".F."
            face_rec[f.id] = self._emit(
                f"ADVANCED_FACE('',({bref}),#{plane},{sense})")

        # -- shells + solid --
        outer_shells = [sh for sh in s.shells if sh.kind == "outer"]
        void_shells = [sh for sh in s.shells if sh.kind == "void"]
        shell_rec: dict[int, int] = {}
        for sh in s.shells:
            refs = ",".join(f"#{face_rec[fid]}" for fid in sh.face_ids)
            shell_rec[sh.id] = self._emit(f"CLOSED_SHELL('',({refs}))")

        outer = outer_shells[0]
        if void_shells:
            voids = ",".join(f"#{shell_rec[v.id]}" for v in void_shells)
            solid_rec = self._emit(
                f"BREP_WITH_VOIDS('{s.name}',#{shell_rec[outer.id]},({voids}))")
        else:
            solid_rec = self._emit(
                f"MANIFOLD_SOLID_BREP('{s.name}',#{shell_rec[outer.id]})")

        return self._wrap(solid_rec)

    def _wrap(self, root: int) -> str:
        body = "\n".join(self.lines)
        header = (
            "ISO-10303-21;\n"
            "HEADER;\n"
            "FILE_DESCRIPTION((''),'2;1');\n"
            f"FILE_NAME('{self.solid.name}','2026-08-31T00:00:00',(''),(''),"
            "'brep-sentinel-writer','brep-sentinel','');\n"
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\n"
            "ENDSEC;\n"
            "DATA;\n"
        )
        footer = f"\n/* root: #{root} */\nENDSEC;\nEND-ISO-10303-21;\n"
        return header + body + footer


def write_step(solid: Solid) -> str:
    return StepWriter(solid).write()
