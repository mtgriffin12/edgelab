"""Minimal FastAPI app for EdgeLab."""

from fastapi import FastAPI, HTTPException, Response

from edgelab.backtesting.engine import BacktestEngine
from edgelab.backtesting.schema import BacktestRequest
from edgelab.data.market_data import LocalFixtureMarketDataProvider
from edgelab.data.sentiment import LocalFixtureSentimentProvider
from edgelab.strategies.cards import strategy_to_markdown_card
from edgelab.strategies.registry import StrategyRegistry

app = FastAPI(title="EdgeLab", version="0.1.0")
strategy_registry = StrategyRegistry.with_samples()
market_data_provider = LocalFixtureMarketDataProvider()
sentiment_provider = LocalFixtureSentimentProvider()
backtest_engine = BacktestEngine()


@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic application metadata."""

    return {
        "app": "EdgeLab",
        "phase": "Phase 4 backtesting engine foundation",
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


@app.get("/market-data/symbols")
def list_market_data_symbols() -> dict[str, list[str]]:
    """Return symbols available in local synthetic fixtures."""

    return {"symbols": market_data_provider.list_available_symbols()}


@app.get("/market-data/{symbol}/bars")
def read_market_data_bars(symbol: str) -> dict[str, object]:
    """Return local synthetic fixture bars for a symbol."""

    data = market_data_provider.load_bars(symbol)
    if not data.bars and any(issue.code == "missing_symbol" for issue in data.quality_issues):
        raise HTTPException(status_code=404, detail="Market data fixture not found")
    return data.model_dump(mode="json")


@app.get("/market-data/{symbol}/summary")
def read_market_data_summary(symbol: str) -> dict[str, object]:
    """Return a local synthetic fixture summary for a symbol."""

    data = market_data_provider.load_bars(symbol)
    if not data.bars and any(issue.code == "missing_symbol" for issue in data.quality_issues):
        raise HTTPException(status_code=404, detail="Market data fixture not found")
    return market_data_provider.summarize_symbol(symbol).model_dump(mode="json")


@app.get("/market-data/{symbol}/quality")
def read_market_data_quality(symbol: str) -> dict[str, object]:
    """Return quality issues for a local synthetic fixture symbol."""

    data = market_data_provider.load_bars(symbol)
    if not data.bars and any(issue.code == "missing_symbol" for issue in data.quality_issues):
        raise HTTPException(status_code=404, detail="Market data fixture not found")
    return {
        "symbol": data.symbol,
        "quality_issues": [issue.model_dump(mode="json") for issue in data.quality_issues],
    }


@app.get("/sentiment/symbols")
def list_sentiment_symbols() -> dict[str, list[str]]:
    """Return symbols available in local synthetic sentiment fixtures."""

    return {"symbols": sentiment_provider.list_available_symbols()}


@app.get("/sentiment/{symbol}/events")
def read_sentiment_events(symbol: str) -> dict[str, object]:
    """Return local synthetic sentiment events for a symbol."""

    events, issues = sentiment_provider.load_events(symbol)
    if not events and any(issue.code == "missing_symbol" for issue in issues):
        raise HTTPException(status_code=404, detail="Sentiment fixture not found")
    return {
        "symbol": symbol.strip().upper(),
        "events": [event.model_dump(mode="json") for event in events],
        "quality_issues": [issue.model_dump(mode="json") for issue in issues],
    }


@app.get("/sentiment/{symbol}/summary")
def read_sentiment_summary(symbol: str) -> dict[str, object]:
    """Return a local synthetic sentiment summary for a symbol."""

    events, issues = sentiment_provider.load_events(symbol)
    if not events and any(issue.code == "missing_symbol" for issue in issues):
        raise HTTPException(status_code=404, detail="Sentiment fixture not found")
    return sentiment_provider.summarize_symbol(symbol).model_dump(mode="json")


@app.get("/sentiment/{symbol}/snapshot")
def read_sentiment_snapshot(symbol: str) -> dict[str, object]:
    """Return a descriptive local synthetic sentiment snapshot for a symbol."""

    events, issues = sentiment_provider.load_events(symbol)
    if not events and any(issue.code == "missing_symbol" for issue in issues):
        raise HTTPException(status_code=404, detail="Sentiment fixture not found")
    return sentiment_provider.create_snapshot(symbol).model_dump(mode="json")


@app.get("/sentiment/{symbol}/quality")
def read_sentiment_quality(symbol: str) -> dict[str, object]:
    """Return quality issues for a local synthetic sentiment fixture symbol."""

    events, issues = sentiment_provider.load_events(symbol)
    if not events and any(issue.code == "missing_symbol" for issue in issues):
        raise HTTPException(status_code=404, detail="Sentiment fixture not found")
    return {
        "symbol": symbol.strip().upper(),
        "quality_issues": [issue.model_dump(mode="json") for issue in issues],
    }


@app.get("/backtests/sample")
def read_sample_backtest() -> dict[str, object]:
    """Return a read-only sample backtest using local fixtures."""

    request = BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY")
    return _run_backtest_request(request)


@app.post("/backtests/run")
def run_backtest(request: BacktestRequest) -> dict[str, object]:
    """Run a local fixture-backed research backtest."""

    return _run_backtest_request(request)


def _run_backtest_request(request: BacktestRequest) -> dict[str, object]:
    strategy = strategy_registry.get(request.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    data = market_data_provider.load_bars(request.symbol)
    if not data.bars and any(issue.code == "missing_symbol" for issue in data.quality_issues):
        raise HTTPException(status_code=404, detail="Market data fixture not found")

    result = backtest_engine.run(strategy, data.bars, request)
    return result.model_dump(mode="json")
