"""Minimal FastAPI app for EdgeLab."""

from fastapi import FastAPI

app = FastAPI(title="EdgeLab", version="0.1.0")


@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic application metadata."""

    return {
        "app": "EdgeLab",
        "phase": "Phase 0 scaffold",
        "status": "research-only",
    }


@app.get("/health")
def read_health() -> dict[str, str]:
    """Return service health."""

    return {"status": "ok"}
