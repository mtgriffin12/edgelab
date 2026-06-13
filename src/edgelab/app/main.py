"""Minimal FastAPI app for EdgeLab."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from edgelab.app.plain_language import explain, plain_label, why_it_matters, yes_no
from edgelab.backtesting.engine import BacktestEngine
from edgelab.backtesting.schema import BacktestRequest
from edgelab.candidates.cards import candidate_to_markdown_card
from edgelab.candidates.screener import CandidateEquityScreener
from edgelab.data.market_data import LocalFixtureMarketDataProvider
from edgelab.data.sentiment import LocalFixtureSentimentProvider
from edgelab.discovery.cards import discovery_to_markdown_card
from edgelab.discovery.genealogy import StrategyGenealogy
from edgelab.discovery.ledger import ExperimentLedger
from edgelab.discovery.library import StrategyDiscoveryLibrary
from edgelab.discovery.schema import DiscoveryLane
from edgelab.portfolios.cards import model_portfolio_to_markdown_card
from edgelab.portfolios.construction import ModelPortfolioEngine
from edgelab.portfolios.schema import PortfolioStyle
from edgelab.ranking.cards import ranking_scorecard_to_markdown_card
from edgelab.ranking.ranker import StrategyRankingEngine
from edgelab.strategies.cards import strategy_to_markdown_card
from edgelab.strategies.registry import StrategyRegistry

app = FastAPI(title="EdgeLab", version="0.1.0")
strategy_registry = StrategyRegistry.with_samples()
market_data_provider = LocalFixtureMarketDataProvider()
sentiment_provider = LocalFixtureSentimentProvider()
backtest_engine = BacktestEngine()
discovery_library = StrategyDiscoveryLibrary.with_samples()
experiment_ledger = ExperimentLedger.with_samples()
ranking_engine = StrategyRankingEngine(
    strategy_registry=strategy_registry,
    discovery_library=discovery_library,
    market_data_provider=market_data_provider,
    backtest_engine=backtest_engine,
)
candidate_screener = CandidateEquityScreener(
    market_data_provider=market_data_provider,
    sentiment_provider=sentiment_provider,
    strategy_registry=strategy_registry,
    discovery_library=discovery_library,
    ranking_engine=ranking_engine,
)
portfolio_engine = ModelPortfolioEngine(candidate_screener=candidate_screener)
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
        "phase": "Phase 7B model portfolio engine",
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


@app.get("/discovery/ideas")
def list_discovery_ideas() -> list[dict[str, object]]:
    """Return read-only local discovery records."""

    return discovery_library.export_all()


@app.get("/discovery/ideas/{discovery_id}")
def read_discovery_idea(discovery_id: str) -> dict[str, object]:
    """Return one local discovery record."""

    record = discovery_library.get(discovery_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Discovery idea not found")
    return record.model_dump(mode="json")


@app.get("/discovery/ideas/{discovery_id}/card", response_class=Response)
def read_discovery_card(discovery_id: str) -> Response:
    """Return a plain-English Markdown discovery card."""

    record = discovery_library.get(discovery_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Discovery idea not found")
    return Response(content=discovery_to_markdown_card(record), media_type="text/plain")


@app.get("/discovery/lanes")
def read_discovery_lanes() -> dict[str, int]:
    """Return discovery counts by lane."""

    return discovery_library.lane_counts()


@app.get("/discovery/genealogy/{discovery_id}")
def read_discovery_genealogy(discovery_id: str) -> dict[str, object]:
    """Return genealogy details for a discovery record."""

    genealogy = StrategyGenealogy(discovery_library.list_records())
    details = genealogy.genealogy_for(discovery_id)
    if not details["found"]:
        raise HTTPException(status_code=404, detail="Discovery idea not found")
    return details


@app.get("/discovery/ledger")
def read_discovery_ledger() -> list[dict[str, object]]:
    """Return scaffolded local experiment ledger entries."""

    return experiment_ledger.export_all()


@app.get("/rankings/sample")
def read_sample_rankings() -> dict[str, object]:
    """Return a read-only local ranking result."""

    return ranking_engine.rank().model_dump(mode="json")


@app.get("/rankings/scorecards")
def read_ranking_scorecards() -> list[dict[str, object]]:
    """Return all generated local ranking scorecards."""

    return [scorecard.model_dump(mode="json") for scorecard in ranking_engine.rank().scorecards]


@app.get("/rankings/scorecards/{scorecard_id}")
def read_ranking_scorecard(scorecard_id: str) -> dict[str, object]:
    """Return one generated local ranking scorecard."""

    scorecard = ranking_engine.get_scorecard(scorecard_id)
    if scorecard is None:
        raise HTTPException(status_code=404, detail="Ranking scorecard not found")
    return scorecard.model_dump(mode="json")


@app.get("/rankings/scorecards/{scorecard_id}/card", response_class=Response)
def read_ranking_scorecard_card(scorecard_id: str) -> Response:
    """Return one generated local ranking scorecard as Markdown."""

    scorecard = ranking_engine.get_scorecard(scorecard_id)
    if scorecard is None:
        raise HTTPException(status_code=404, detail="Ranking scorecard not found")
    return Response(content=ranking_scorecard_to_markdown_card(scorecard), media_type="text/plain")


@app.get("/rankings/top-research-candidates")
def read_top_research_candidates() -> list[dict[str, object]]:
    """Return highest-ranking local research candidates."""

    return [
        scorecard.model_dump(mode="json")
        for scorecard in ranking_engine.rank().top_research_candidates
    ]


@app.get("/rankings/weak-candidates")
def read_weak_ranking_candidates() -> list[dict[str, object]]:
    """Return weak, unsupported, rejected, or insufficient local candidates."""

    return [
        scorecard.model_dump(mode="json") for scorecard in ranking_engine.rank().weak_candidates
    ]


@app.get("/candidates/sample")
def read_sample_candidates() -> dict[str, object]:
    """Return a sample local research-only candidate screening result."""

    return candidate_screener.screen().model_dump(mode="json")


@app.get("/candidates/equities")
def read_equity_candidates() -> list[dict[str, object]]:
    """Return all local research-only equity candidates."""

    return [
        candidate.model_dump(mode="json") for candidate in candidate_screener.screen().candidates
    ]


@app.get("/candidates/equities/{candidate_id}")
def read_equity_candidate(candidate_id: str) -> dict[str, object]:
    """Return one local research-only equity candidate."""

    candidate = candidate_screener.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate.model_dump(mode="json")


@app.get("/candidates/equities/{candidate_id}/card", response_class=Response)
def read_equity_candidate_card(candidate_id: str) -> Response:
    """Return one local candidate as a Markdown card."""

    candidate = candidate_screener.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return Response(content=candidate_to_markdown_card(candidate), media_type="text/plain")


@app.get("/candidates/symbols")
def read_candidate_symbols() -> dict[str, list[str]]:
    """Return the local fixture symbols used by the candidate screener."""

    return {"symbols": candidate_screener.list_symbols()}


@app.get("/candidates/research-watchlist")
def read_candidate_research_watchlist() -> list[dict[str, object]]:
    """Return local research watchlist candidates."""

    return [
        candidate.model_dump(mode="json") for candidate in candidate_screener.research_watchlist()
    ]


@app.get("/portfolios/sample")
def read_sample_portfolios() -> dict[str, object]:
    """Return a sample local research-only portfolio construction result."""

    return portfolio_engine.construct().model_dump(mode="json")


@app.get("/portfolios/model")
def read_model_portfolios() -> list[dict[str, object]]:
    """Return all local research-only model portfolios."""

    return [
        portfolio.model_dump(mode="json") for portfolio in portfolio_engine.construct().portfolios
    ]


@app.get("/portfolios/model/{portfolio_id}")
def read_model_portfolio(portfolio_id: str) -> dict[str, object]:
    """Return one local model portfolio."""

    portfolio = portfolio_engine.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Model portfolio not found")
    return portfolio.model_dump(mode="json")


@app.get("/portfolios/model/{portfolio_id}/card", response_class=Response)
def read_model_portfolio_card(portfolio_id: str) -> Response:
    """Return one local model portfolio as a Markdown card."""

    portfolio = portfolio_engine.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Model portfolio not found")
    return Response(content=model_portfolio_to_markdown_card(portfolio), media_type="text/plain")


@app.get("/portfolios/styles")
def read_portfolio_styles() -> dict[str, list[str]]:
    """Return available model portfolio styles."""

    return {"styles": [style.value for style in PortfolioStyle]}


@app.get("/portfolios/model/{portfolio_id}/monitoring")
def read_model_portfolio_monitoring(portfolio_id: str) -> dict[str, object]:
    """Return monitoring notes for one local model portfolio."""

    notes = portfolio_engine.monitoring_notes_for(portfolio_id)
    if notes is None:
        raise HTTPException(status_code=404, detail="Model portfolio not found")
    return {"portfolio_id": portfolio_id, "monitoring_notes": notes}


@app.get("/ui", response_class=HTMLResponse)
def read_ui_home(request: Request) -> Response:
    """Render the local research cockpit."""

    strategies = strategy_registry.list_strategies()
    market_symbols = market_data_provider.list_available_symbols()
    sentiment_symbols = sentiment_provider.list_available_symbols()
    sample_backtest = _run_backtest_request(
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY")
    )
    sample_rankings = ranking_engine.rank()
    sample_candidates = candidate_screener.screen()
    sample_portfolios = portfolio_engine.construct()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "strategies": strategies,
            "market_symbols": market_symbols,
            "sentiment_symbols": sentiment_symbols,
            "sample_backtest": sample_backtest,
            "discovery_count": len(discovery_library.list_records()),
            "ranking_count": len(sample_rankings.scorecards),
            "candidate_count": sample_candidates.candidate_count,
            "portfolio_count": sample_portfolios.portfolio_count,
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


@app.get("/ui/discovery-lab", response_class=HTMLResponse)
def read_ui_discovery_lab(request: Request) -> Response:
    """Render the local strategy discovery lab."""

    known_records = discovery_library.filter_by_lane(DiscoveryLane.KNOWN_STRATEGY_LIBRARY)
    innovation_records = discovery_library.filter_by_lane(DiscoveryLane.EDGE_INNOVATION_LAB)
    return templates.TemplateResponse(
        request=request,
        name="discovery_lab.html",
        context={
            "known_records": known_records,
            "innovation_records": innovation_records,
            "lane_counts": discovery_library.lane_counts(),
        },
    )


@app.get("/ui/discovery-lab/{discovery_id}", response_class=HTMLResponse)
def read_ui_discovery_detail(request: Request, discovery_id: str) -> Response:
    """Render one discovery record."""

    record = discovery_library.get(discovery_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Discovery idea not found")
    genealogy = StrategyGenealogy(discovery_library.list_records())
    return templates.TemplateResponse(
        request=request,
        name="discovery_detail.html",
        context={
            "record": record,
            "card": discovery_to_markdown_card(record),
            "genealogy": genealogy.genealogy_for(discovery_id),
        },
    )


@app.get("/ui/rankings", response_class=HTMLResponse)
def read_ui_rankings(request: Request) -> Response:
    """Render the local strategy rankings page."""

    result = ranking_engine.rank()
    return templates.TemplateResponse(
        request=request,
        name="rankings.html",
        context={"ranking_result": result, "scorecards": result.scorecards},
    )


@app.get("/ui/candidates", response_class=HTMLResponse)
def read_ui_candidates(request: Request) -> Response:
    """Render the local candidate equity screener page."""

    result = candidate_screener.screen()
    return templates.TemplateResponse(
        request=request,
        name="candidates.html",
        context={"screening_result": result, "candidates": result.candidates},
    )


@app.get("/ui/candidates/{candidate_id}", response_class=HTMLResponse)
def read_ui_candidate_detail(request: Request, candidate_id: str) -> Response:
    """Render one local candidate card."""

    candidate = candidate_screener.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return templates.TemplateResponse(
        request=request,
        name="candidate_detail.html",
        context={
            "candidate": candidate,
            "card": candidate_to_markdown_card(candidate),
        },
    )


@app.get("/ui/portfolios", response_class=HTMLResponse)
def read_ui_portfolios(request: Request) -> Response:
    """Render the local model portfolio page."""

    result = portfolio_engine.construct()
    return templates.TemplateResponse(
        request=request,
        name="portfolios.html",
        context={"construction_result": result, "portfolios": result.portfolios},
    )


@app.get("/ui/portfolios/{portfolio_id}", response_class=HTMLResponse)
def read_ui_portfolio_detail(request: Request, portfolio_id: str) -> Response:
    """Render one local model portfolio card."""

    portfolio = portfolio_engine.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Model portfolio not found")
    return templates.TemplateResponse(
        request=request,
        name="portfolio_detail.html",
        context={
            "portfolio": portfolio,
            "card": model_portfolio_to_markdown_card(portfolio),
        },
    )


@app.get("/ui/rankings/{scorecard_id}", response_class=HTMLResponse)
def read_ui_ranking_detail(request: Request, scorecard_id: str) -> Response:
    """Render one ranking scorecard."""

    scorecard = ranking_engine.get_scorecard(scorecard_id)
    if scorecard is None:
        raise HTTPException(status_code=404, detail="Ranking scorecard not found")
    return templates.TemplateResponse(
        request=request,
        name="ranking_detail.html",
        context={
            "scorecard": scorecard,
            "card": ranking_scorecard_to_markdown_card(scorecard),
        },
    )


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
        "Phase 5C strategy discovery lab",
        "Phase 6 strategy ranking engine",
        "Phase 7A candidate equity screener",
        "Phase 7B model portfolio engine",
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
    sample_candidates = candidate_screener.screen()
    sample_portfolios = portfolio_engine.construct()
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "strategies": strategies,
            "market_summaries": market_summaries,
            "sentiment_summaries": sentiment_summaries,
            "sample_backtest": sample_backtest,
            "sample_candidates": sample_candidates,
            "sample_portfolios": sample_portfolios,
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
