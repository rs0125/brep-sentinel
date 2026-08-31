"""Kernel B -- STRICT / LITERAL independent STEP reader.

Interprets the STEP entity graph exactly as written: no vertex merging, no gap
stitching, no orientation repair. Vertex identity is the VERTEX_POINT record id;
edge identity is the EDGE_CURVE record id. Coincident-but-distinct points are
two vertices; a crack stays a crack. This models a low-tolerance/conformance
reader -- the honest witness to what the file literally says.
"""
from __future__ import annotations

from .common import sha256_bytes
from .kernel_base import reconstruct, build_descriptor
from .step_parser import parse_step

KERNEL_NAME = "kernel_b_strict"
KERNEL_VERSION = "strict-literal/1.0 (tol=0)"


def load(path: str):
    text = open(path).read()
    return load_text(text, source_file=path, sha=sha256_bytes(text.encode()))


def load_text(text: str, *, source_file: str, sha: str):
    records = parse_step(text)
    topo = reconstruct(records)
    return build_descriptor(
        topo, source_file=source_file, file_sha256=sha,
        kernel_name=KERNEL_NAME, kernel_version=KERNEL_VERSION,
        healing_enabled=False, healing_log=[],
    )


if __name__ == "__main__":
    import sys
    d = load(sys.argv[1])
    print(d.kernel_name, d.counts(), "errors:", d.parse_errors)
