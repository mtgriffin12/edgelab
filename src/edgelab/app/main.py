"""Minimal FastAPI app for EdgeLab."""

from fastapi import FastAPI, HTTPException, Response

from edgelab.strategies.cards import strategy_to_markdown_card
from edgelab.strategies.registry import StrategyRegistry

app = FastAPI(title="EdgeLab", version="0.1.0")
strategy_registry = StrategyRegistry.with_samples()


@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic application metadata."""

    return {
        "app": "EdgeLab",
        "phase": "Phase 1 strategy specification engine",
        "status": "research-only",
    }


@app.get("/health")
def read_health() -> dict[str, str]:
    """Return service health."""

    return {"status": "ok"}


@app.get("/strategies")
def list_strategies() -> list[dict[str, object]]:
    """Return read-only sample strategies."""

    return strategy_registry.export_all()


@app.get("/strategies/{strategy_id}")
def read_strategy(strategy_id: str) -> dict[str, object]:
    """Return a read-only sample strategy."""

    strategy = strategy_registry.get(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy.model_dump(mode="json")


@app.get("/strategies/{strategy_id}/card", response_class=Response)
def read_strategy_card(strategy_id: str) -> Response:
    """Return a Markdown strategy card as plain text."""

    strategy = strategy_registry.get(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return Response(content=strategy_to_markdown_card(strategy), media_type="text/plain")
