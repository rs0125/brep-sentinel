"""Shared foundation: kernel/version identity, hashing, deterministic config,
and the normalized JSON *descriptor schema* that both kernels emit.

The descriptor is the contract between the two kernels and every downstream
stage. Both readers -- whatever their internal differences -- MUST produce this
exact shape so the differential/adjudication stage can compare them field by
field.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass, field, asdict
from typing import Any

# ------------------------------------------------------------------------------
# Determinism: single global seed and tolerances, logged into every artifact so
# a run is reproducible from its report alone.
# ------------------------------------------------------------------------------
SEED = 20260831

# Coordinate quantization used when *comparing* points across the two kernels.
# This is only for the differential diff -- each kernel keeps its own internal
# tolerance (that difference is the whole point).
COMPARE_DECIMALS = 6

# Descriptor schema version. Bump if the shape below changes.
SCHEMA_VERSION = "descriptor/1.0"


def env_fingerprint() -> dict[str, Any]:
    """Environment identity logged into artifacts for reproducibility."""
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "seed": SEED,
        "schema_version": SCHEMA_VERSION,
    }


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------------------
# Normalized descriptor schema (dataclasses -> JSON).
# ------------------------------------------------------------------------------
@dataclass
class VertexD:
    id: int
    xyz: list[float]


@dataclass
class EdgeD:
    id: int
    curve_type: str            # "line" | "circle" | ...
    vertex_ids: list[int]      # [v_start, v_end]
    length: float
    face_ids: list[int]        # faces that reference this edge (sorted)

    @property
    def incidence(self) -> int:
        return len(self.face_ids)


@dataclass
class FaceD:
    id: int
    surface_type: str          # "plane" | "cylinder" | ...
    orientation: bool          # face sense flag as interpreted by the kernel
    outer_loop_edges: list[int]
    inner_loops: list[list[int]]   # each inner loop = list of edge ids (rings)
    area: float
    normal: list[float]

    @property
    def n_inner_loops(self) -> int:
        return len(self.inner_loops)


@dataclass
class ShellD:
    id: int
    kind: str                  # "outer" | "void"
    face_ids: list[int]
    closed: bool


@dataclass
class Descriptor:
    """Kernel-agnostic normalized description of a parsed B-rep."""
    source_file: str
    file_sha256: str
    kernel_name: str
    kernel_version: str
    healing_enabled: bool
    schema_version: str = SCHEMA_VERSION

    vertices: list[VertexD] = field(default_factory=list)
    edges: list[EdgeD] = field(default_factory=list)
    faces: list[FaceD] = field(default_factory=list)
    shells: list[ShellD] = field(default_factory=list)

    healing_log: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    # ---- derived topology counts (Euler-Poincare inputs) ----
    @property
    def V(self) -> int:
        return len(self.vertices)

    @property
    def E(self) -> int:
        return len(self.edges)

    @property
    def F(self) -> int:
        return len(self.faces)

    @property
    def S(self) -> int:
        return len(self.shells)

    @property
    def R(self) -> int:
        """Total number of inner loops (rings) across all faces."""
        return sum(f.n_inner_loops for f in self.faces)

    def counts(self) -> dict[str, int]:
        return {"V": self.V, "E": self.E, "F": self.F, "S": self.S, "R": self.R}

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["counts"] = self.counts()
        return d

    def dump(self, path: str) -> None:
        with open(path, "w") as fh:
            json.dump(self.to_json(), fh, indent=2, sort_keys=True)

    @staticmethod
    def load(path: str) -> "Descriptor":
        with open(path) as fh:
            d = json.load(fh)
        return Descriptor.from_json(d)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Descriptor":
        return Descriptor(
            source_file=d["source_file"],
            file_sha256=d["file_sha256"],
            kernel_name=d["kernel_name"],
            kernel_version=d["kernel_version"],
            healing_enabled=d["healing_enabled"],
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            vertices=[VertexD(**v) for v in d["vertices"]],
            edges=[EdgeD(**e) for e in d["edges"]],
            faces=[FaceD(**f) for f in d["faces"]],
            shells=[ShellD(**s) for s in d["shells"]],
            healing_log=d.get("healing_log", []),
            parse_errors=d.get("parse_errors", []),
        )
