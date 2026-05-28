"""Minimal FastAPI app for EdgeLab."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from edgelab.app.plain_language import explain, plain_label, why_it_matters, yes_no
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
APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
templates.env.globals["plain_label"] = plain_label
templates.env.globals["explain"] = explain
templates.env.globals["why_it_matters"] = why_it_matters
templates.env.globals["yes_no"] = yes_no
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic application metadata."""

    return {
        "app": "EdgeLab",
        "phase": "Phase 5B plain-English UX",
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


@app.get("/ui", response_class=HTMLResponse)
def read_ui_home(request: Request) -> Response:
    """Render the local research cockpit."""

    strategies = strategy_registry.list_strategies()
    market_symbols = market_data_provider.list_available_symbols()
    sentiment_symbols = sentiment_provider.list_available_symbols()
    sample_backtest = _run_backtest_request(
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY")
    )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "strategies": strategies,
            "market_symbols": market_symbols,
            "sentiment_symbols": sentiment_symbols,
            "sample_backtest": sample_backtest,
        },
    )


@app.get("/ui/lab-bench", response_class=HTMLResponse)
def read_ui_lab_bench(request: Request) -> Response:
    """Render the read-only strategy inventory."""

    return templates.TemplateResponse(
        request=request,
        name="lab_bench.html",
        context={"strategies": strategy_registry.list_strategies()},
    )


@app.get("/ui/strategies/{strategy_id}", response_class=HTMLResponse)
def read_ui_strategy_detail(request: Request, strategy_id: str) -> Response:
    """Render a strategy card as readable local HTML."""

    strategy = strategy_registry.get(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return templates.TemplateResponse(
        request=request,
        name="strategy_detail.html",
        context={
            "strategy": strategy,
            "card": strategy_to_markdown_card(strategy),
        },
    )


@app.get("/ui/evidence-board", response_class=HTMLResponse)
def read_ui_evidence_board(request: Request) -> Response:
    """Render fixture-backed backtest evidence."""

    sample_backtest = _run_backtest_request(
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY")
    )
    unsupported_backtest = _run_backtest_request(
        BacktestRequest(strategy_id="earnings-drift-with-confirmation", symbol="SPY")
    )
    return templates.TemplateResponse(
        request=request,
        name="evidence_board.html",
        context={"backtests": [sample_backtest, unsupported_backtest]},
    )


@app.get("/ui/sentiment-lens", response_class=HTMLResponse)
def read_ui_sentiment_lens(request: Request) -> Response:
    """Render descriptive sentiment fixture snapshots."""

    snapshots = [
        sentiment_provider.create_snapshot(symbol).model_dump(mode="json")
        for symbol in sentiment_provider.list_available_symbols()
    ]
    return templates.TemplateResponse(
        request=request,
        name="sentiment_lens.html",
        context={"snapshots": snapshots},
    )


@app.get("/ui/risk-sentinel", response_class=HTMLResponse)
def read_ui_risk_sentinel(request: Request) -> Response:
    """Render deterministic safety posture."""

    return templates.TemplateResponse(request=request, name="risk_sentinel.html", context={})


@app.get("/ui/journal", response_class=HTMLResponse)
def read_ui_journal(request: Request) -> Response:
    """Render a simple audit-style phase journal."""

    entries = [
        "Phase 0 scaffold created",
        "Phase 1 strategy specification engine",
        "Phase 2 market data fixtures",
        "Phase 3 sentiment fixtures",
        "Phase 4 backtesting foundation",
        "Phase 5A local UX shell",
        "Phase 5B plain-English UX language",
    ]
    return templates.TemplateResponse(
        request=request,
        name="journal.html",
        context={"entries": entries},
    )


@app.get("/ui/reports", response_class=HTMLResponse)
def read_ui_reports(request: Request) -> Response:
    """Render text/table summaries of current local fixtures."""

    strategies = strategy_registry.list_strategies()
    market_summaries = [
        market_data_provider.summarize_symbol(symbol).model_dump(mode="json")
        for symbol in market_data_provider.list_available_symbols()
    ]
    sentiment_summaries = [
        sentiment_provider.summarize_symbol(symbol).model_dump(mode="json")
        for symbol in sentiment_provider.list_available_symbols()
    ]
    sample_backtest = _run_backtest_request(
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY")
    )
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "strategies": strategies,
            "market_summaries": market_summaries,
            "sentiment_summaries": sentiment_summaries,
            "sample_backtest": sample_backtest,
        },
    )


def _run_backtest_request(request: BacktestRequest) -> dict[str, object]:
    strategy = strategy_registry.get(request.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    data = market_data_provider.load_bars(request.symbol)
    if not data.bars and any(issue.code == "missing_symbol" for issue in data.quality_issues):
        raise HTTPException(status_code=404, detail="Market data fixture not found")

    result = backtest_engine.run(strategy, data.bars, request)
    return result.model_dump(mode="json")
