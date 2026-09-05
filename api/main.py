"""FastAPI entrypoint for the brep-sentinel API layer.

Run from the REPO ROOT (not from inside api/), so `brep_sentinel` resolves
as a package import:

    pip install -r requirements.txt -r api/requirements-api.txt
    uvicorn api.main:app --reload --port 8000

Then the frontend (Vite dev server, typically localhost:5173) talks to
http://localhost:8000/api/...
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import storage
from .routes import batch, meta, overview, real, single

storage.init_db()  # eager, not on the startup event -- guarantees the table
                    # exists even under test clients that skip ASGI lifespan

app = FastAPI(
    title="brep-sentinel API",
    description="HTTP wrapper around the brep_sentinel CAD malware analysis pipeline.",
    version="0.2.0",
)

# Dev-friendly CORS: the frontend runs on a different origin (Vite's 5173)
# than the API (8000). Tighten allow_origins to a specific list before any
# real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(meta.router)
app.include_router(overview.router)
app.include_router(single.router)
app.include_router(batch.router)
app.include_router(real.router)
