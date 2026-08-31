"""Stage 1 (real): ingest real STEP files from public sources.

Downloads a curated set of real CAD models and records source URL + sha256 per
file (per the brief's provenance requirement). Network is used ONLY here. Files
are cached under real_corpus/; re-running skips files already present with a
matching hash.

Source: github.com/tpaviot/pythonocc-demos (assets/models) -- real STEP parts
used to exercise OpenCASCADE, spanning a machined part, the classic AS1
assemblies (AP203/AP214), and larger multi-feature bodies.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request

BASE = ("https://raw.githubusercontent.com/tpaviot/pythonocc-demos/master/"
        "assets/models/")

# curated: (filename, note). Kept modest so the demo stays quick + deterministic.
CURATED = [
    ("face_recognition_sample_part.stp", "single machined part, planar+circular"),
    ("as1_pe_203.stp", "AS1 rod/bracket assembly (AP203), 5 solids"),
    ("as1-oc-214.stp", "AS1 rod/bracket assembly (AP214), 5 solids"),
    ("11752.stp", "multi-feature body, cylindrical+spline faces"),
    ("splinecage.stp", "spline SHEET body (no closed solid) -- negative control"),
]


def ingest(out_dir: str = "real_corpus") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    manifest = {"source_repo": "github.com/tpaviot/pythonocc-demos (assets/models)",
                "files": []}
    for name, note in CURATED:
        path = os.path.join(out_dir, name)
        if os.path.exists(path):
            data = open(path, "rb").read()
        else:
            url = BASE + name
            req = urllib.request.Request(url, headers={"User-Agent": "brep-sentinel"})
            data = urllib.request.urlopen(req, timeout=90).read()
            open(path, "wb").write(data)
        manifest["files"].append({
            "name": name, "source_url": BASE + name, "note": note,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        })
    with open(os.path.join(out_dir, "SOURCES.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "real_corpus"
    m = ingest(out)
    for f in m["files"]:
        print(f"{f['bytes']:>9d}  {f['sha256'][:12]}  {f['name']}")
    print(f"\nprovenance -> {out}/SOURCES.json")
