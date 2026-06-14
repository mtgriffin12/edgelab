"""Minimal FastAPI app for EdgeLab."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import cast

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
from edgelab.intraday.benchmarks import calculate_opening_benchmarks
from edgelab.intraday.cards import (
    historical_replay_to_markdown_card,
    intraday_simulation_to_markdown_card,
    multi_session_replay_to_markdown_card,
    prop_account_to_markdown_card,
)
from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.firstrate_replay import (
    CachedFirstRateHistoricalDataProvider,
    FirstHourCompleteness,
    FirstHourCompletenessSummary,
    first_hour_completeness_for_import_result,
    summarize_first_hour_completeness,
)
from edgelab.intraday.fixtures import LocalIntradayFixtureProvider
from edgelab.intraday.historical_provider import (
    FuturePaidHistoricalProvider,
    LocalCSVHistoricalIntradayProvider,
)
from edgelab.intraday.historical_schema import (
    HistoricalIntradayImportResult,
    HistoricalIntradaySession,
    utc_now,
)
from edgelab.intraday.pattern_results import MultiSessionPatternRunner
from edgelab.intraday.pattern_results_schema import (
    MultiSessionReplayRequest,
    MultiSessionReplaySummary,
)
from edgelab.intraday.prop_accounts import sample_prop_account_result
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.replay_schema import HistoricalReplayRequest, HistoricalReplayResult
from edgelab.intraday.schema import IntradayBar, IntradayQualityIssue
from edgelab.intraday.setups import IntradaySetupDetector
from edgelab.intraday.simulator import IntradaySimulator
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
intraday_fixture_provider = LocalIntradayFixtureProvider()
historical_intraday_provider = LocalCSVHistoricalIntradayProvider()
firstrate_historical_provider = FirstRateLocalCSVHistoricalProvider()
_firstrate_cached_provider_source: FirstRateLocalCSVHistoricalProvider | None = None
_firstrate_cached_replay_provider: CachedFirstRateHistoricalDataProvider | None = None
future_historical_provider = FuturePaidHistoricalProvider()
intraday_setup_detector = IntradaySetupDetector()
intraday_simulator = IntradaySimulator(
    fixture_provider=intraday_fixture_provider,
    setup_detector=intraday_setup_detector,
)
historical_replay_engine = HistoricalIntradayReplayEngine(
    provider=historical_intraday_provider,
    setup_detector=intraday_setup_detector,
)
multi_session_pattern_runner = MultiSessionPatternRunner(
    provider=historical_intraday_provider,
    replay_engine=historical_replay_engine,
)
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


@dataclass(frozen=True)
class FirstRateMultiSessionCacheKey:
    """Process-local key for expensive FirstRate many-morning summaries."""

    symbol: str
    start_date: date | None
    end_date: date | None
    hold_minutes: int
    slippage_ticks: int
    commission_per_contract: float
    file_signature: tuple[tuple[str, int, int], ...]


@dataclass(frozen=True)
class FirstRateMultiSessionCacheEntry:
    """Cached FirstRate many-morning result."""

    summary: MultiSessionReplaySummary
    completeness: list[FirstHourCompleteness]
    completeness_summary: FirstHourCompletenessSummary
    computed_at: str
    elapsed_ms: int


_firstrate_multi_session_cache: dict[
    FirstRateMultiSessionCacheKey, FirstRateMultiSessionCacheEntry
] = {}
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
        "phase": "Phase 7X-2E FirstRate replay integration",
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


@app.get("/intraday/instruments")
def read_intraday_instruments() -> dict[str, object]:
    """Return synthetic fixture-backed intraday instruments."""

    return {
        "instruments": [
            instrument.model_dump(mode="json")
            for instrument in intraday_fixture_provider.list_instruments()
        ],
        "research_only_status": "Research only",
        "real_money_status": "Not allowed",
    }


@app.get("/intraday/sessions")
def read_intraday_sessions(symbol: str | None = None) -> dict[str, object]:
    """Return available synthetic intraday fixture sessions."""

    return {
        "sessions": intraday_fixture_provider.list_available_sessions(symbol),
        "research_only_status": "Research only",
        "real_money_status": "Not allowed",
    }


@app.get("/intraday/history/provider-capabilities")
def read_historical_intraday_provider_capabilities() -> dict[str, object]:
    """Return historical intraday provider capabilities."""

    return {
        "providers": [
            historical_intraday_provider.provider_capabilities().model_dump(mode="json"),
            firstrate_historical_provider.provider_capabilities().model_dump(mode="json"),
            future_historical_provider.provider_capabilities().model_dump(mode="json"),
        ],
        "plain_english_summary": (
            "Historical intraday import currently supports local CSV files and ignored "
            "FirstRate dry-run files only. "
            "Future paid providers are placeholders and make no external calls."
        ),
        "research_only_status": "Research only",
        "real_money_status": "Not allowed",
    }


@app.get("/intraday/history/sessions")
def read_historical_intraday_sessions() -> dict[str, object]:
    """Return all local historical intraday sessions."""

    result = historical_intraday_provider.load_all_sessions()
    return _historical_import_response(result, include_bars=False)


@app.get("/intraday/history/firstrate/files")
def read_firstrate_files() -> dict[str, object]:
    """Return detected ignored local FirstRate CSV files."""

    detected_files = firstrate_historical_provider.detected_files()
    return {
        "data_dir": str(firstrate_historical_provider.data_dir),
        "files_found": len(detected_files),
        "files": [detected_file.model_dump(mode="json") for detected_file in detected_files],
        "plain_english_summary": (
            "Detected ignored local FirstRate CSV files for dry-run inspection only."
            if detected_files
            else "No ignored local FirstRate CSV files were found for dry-run inspection."
        ),
        "research_only_status": "Research only",
        "real_money_status": "Not allowed",
    }


@app.get("/intraday/history/firstrate/dry-run")
def read_firstrate_dry_run() -> dict[str, object]:
    """Return a dry-run summary for ignored local FirstRate files."""

    return firstrate_historical_provider.dry_run().model_dump(mode="json")


@app.get("/intraday/history/firstrate/{symbol}/sessions")
def read_firstrate_symbol_sessions(symbol: str) -> dict[str, object]:
    """Return normalized FirstRate session summaries for one symbol."""

    sessions = firstrate_historical_provider.list_sessions(symbol)
    if not sessions:
        raise HTTPException(status_code=404, detail="FirstRate sessions not found")
    result = firstrate_historical_provider.load_sessions(symbol)
    return _historical_import_response(result, include_bars=False)


@app.get("/intraday/history/firstrate/{symbol}/sessions/{session_id}")
def read_firstrate_session(symbol: str, session_id: str) -> dict[str, object]:
    """Return one normalized FirstRate session summary."""

    result = firstrate_historical_provider.load_session(symbol, session_id)
    if not result.sessions:
        raise HTTPException(status_code=404, detail="FirstRate session not found")
    return _historical_import_response(result, include_bars=False)


@app.get("/intraday/history/firstrate/{symbol}/sessions/{session_id}/replay")
def read_firstrate_replay(
    symbol: str,
    session_id: str,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return one local FirstRate replay using the historical replay engine."""

    result, completeness = _firstrate_replay_result(
        symbol=symbol,
        session_id=session_id,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    response = cast(dict[str, object], result.model_dump(mode="json"))
    response["first_hour_completeness"] = completeness.model_dump(mode="json")
    return response


@app.get("/intraday/history/firstrate/{symbol}/sessions/{session_id}/replay/card")
def read_firstrate_replay_card(
    symbol: str,
    session_id: str,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> Response:
    """Return one local FirstRate replay as a Markdown card."""

    result, completeness = _firstrate_replay_result(
        symbol=symbol,
        session_id=session_id,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    card = "\n".join(
        [
            historical_replay_to_markdown_card(result),
            "",
            "## First-hour completeness",
            f"- {completeness.plain_english_summary}",
            f"- Label: {completeness.first_hour_completeness_label.value.replace('_', ' ')}",
        ]
    )
    return Response(content=card, media_type="text/plain")


@app.get("/intraday/history/firstrate/{symbol}/multi-session-summary")
def read_firstrate_multi_session_summary(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return a many-morning replay summary for local FirstRate sessions."""

    return _firstrate_multi_session_response(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )


@app.get("/intraday/history/firstrate/{symbol}/pattern-results")
def read_firstrate_pattern_results(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return repeated-pattern results for local FirstRate sessions."""

    return _firstrate_multi_session_response(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )


@app.get("/intraday/history/firstrate/{symbol}/no-trade-analysis")
def read_firstrate_no_trade_analysis(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return sit-out review for local FirstRate sessions."""

    return _firstrate_multi_session_response(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )


@app.get("/intraday/history/{symbol}/sessions")
def read_historical_intraday_symbol_sessions(symbol: str) -> dict[str, object]:
    """Return local historical intraday sessions for one symbol."""

    result = historical_intraday_provider.load_sessions(symbol)
    if not result.sessions:
        raise HTTPException(status_code=404, detail="Historical intraday sessions not found")
    return _historical_import_response(result, include_bars=False)


@app.get("/intraday/history/{symbol}/sessions/{session_id}")
def read_historical_intraday_session(symbol: str, session_id: str) -> dict[str, object]:
    """Return one local historical intraday session summary."""

    result = historical_intraday_provider.load_session(symbol, session_id)
    if not result.sessions:
        raise HTTPException(status_code=404, detail="Historical intraday session not found")
    return _historical_import_response(result, include_bars=False)


@app.get("/intraday/history/{symbol}/sessions/{session_id}/bars")
def read_historical_intraday_session_bars(symbol: str, session_id: str) -> dict[str, object]:
    """Return bars for one local historical intraday session."""

    result = historical_intraday_provider.load_session(symbol, session_id)
    if not result.sessions:
        raise HTTPException(status_code=404, detail="Historical intraday session not found")
    return _historical_import_response(result, include_bars=True)


@app.get("/intraday/replay/sample")
def read_historical_replay_sample() -> dict[str, object]:
    """Return a sample replay from the first ready local historical session."""

    ready_session = _first_ready_historical_session()
    if ready_session is None:
        raise HTTPException(status_code=404, detail="No replay-ready historical session found")
    request = HistoricalReplayRequest(
        symbol=ready_session.symbol,
        session_id=ready_session.session_id,
    )
    return historical_replay_engine.replay(request).model_dump(mode="json")


@app.get("/intraday/replay/{symbol}/{session_id}")
def read_historical_replay(
    symbol: str,
    session_id: str,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return one local historical intraday replay."""

    request = HistoricalReplayRequest(
        symbol=symbol,
        session_id=session_id,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    return historical_replay_engine.replay(request).model_dump(mode="json")


@app.get("/intraday/replay/{symbol}/{session_id}/card", response_class=Response)
def read_historical_replay_card(
    symbol: str,
    session_id: str,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> Response:
    """Return one local historical intraday replay card as Markdown."""

    request = HistoricalReplayRequest(
        symbol=symbol,
        session_id=session_id,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    result = historical_replay_engine.replay(request)
    return Response(content=historical_replay_to_markdown_card(result), media_type="text/plain")


@app.get("/intraday/multi-session-summary")
def read_multi_session_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return a local multi-session historical replay summary."""

    request = _multi_session_request(
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    return multi_session_pattern_runner.run(request).model_dump(mode="json")


@app.get("/intraday/multi-session-summary/card", response_class=Response)
def read_multi_session_summary_card(
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> Response:
    """Return a local multi-session summary card as Markdown."""

    request = _multi_session_request(
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    summary = multi_session_pattern_runner.run(request)
    return Response(content=multi_session_replay_to_markdown_card(summary), media_type="text/plain")


@app.get("/intraday/pattern-results")
def read_pattern_results(
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return local repeated-pattern replay results."""

    request = _multi_session_request(
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    return multi_session_pattern_runner.run(request).model_dump(mode="json")


@app.get("/intraday/pattern-results/{symbol}")
def read_symbol_pattern_results(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return local repeated-pattern replay results for one symbol."""

    request = _multi_session_request(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    return multi_session_pattern_runner.run(request).model_dump(mode="json")


@app.get("/intraday/no-trade-analysis")
def read_no_trade_analysis(
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return local sit-out review from multi-session replay."""

    request = _multi_session_request(
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    return multi_session_pattern_runner.run(request).model_dump(mode="json")


@app.get("/intraday/no-trade-analysis/{symbol}")
def read_symbol_no_trade_analysis(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    """Return local sit-out review for one symbol."""

    request = _multi_session_request(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    return multi_session_pattern_runner.run(request).model_dump(mode="json")


@app.get("/intraday/{symbol}/benchmarks")
def read_intraday_benchmarks(symbol: str, session_id: str | None = None) -> dict[str, object]:
    """Return opening benchmarks for a synthetic intraday session."""

    bars, load_issues = _load_intraday_bars_or_404(symbol, session_id)
    benchmarks = calculate_opening_benchmarks(bars)
    data = benchmarks.model_dump(mode="json")
    data["load_quality_issues"] = [issue.model_dump(mode="json") for issue in load_issues]
    return data


@app.get("/intraday/{symbol}/events")
def read_intraday_events(symbol: str, session_id: str | None = None) -> dict[str, object]:
    """Return detected synthetic intraday events."""

    bars, load_issues = _load_intraday_bars_or_404(symbol, session_id)
    benchmarks = calculate_opening_benchmarks(bars)
    events = intraday_setup_detector.detect_events(bars, benchmarks)
    return {
        "symbol": benchmarks.symbol,
        "session_id": benchmarks.session_id,
        "events": [event.model_dump(mode="json") for event in events],
        "quality_issues": [
            issue.model_dump(mode="json") for issue in [*load_issues, *benchmarks.quality_issues]
        ],
        "real_money_status": "Not allowed",
    }


@app.get("/intraday/{symbol}/setups")
def read_intraday_setups(symbol: str, session_id: str | None = None) -> dict[str, object]:
    """Return detected synthetic setup candidates."""

    bars, load_issues = _load_intraday_bars_or_404(symbol, session_id)
    benchmarks = calculate_opening_benchmarks(bars)
    setups = intraday_setup_detector.detect_setups(bars, benchmarks)
    return {
        "symbol": benchmarks.symbol,
        "session_id": benchmarks.session_id,
        "setup_candidates": [setup.model_dump(mode="json") for setup in setups],
        "quality_issues": [
            issue.model_dump(mode="json") for issue in [*load_issues, *benchmarks.quality_issues]
        ],
        "real_money_status": "Not allowed",
    }


@app.get("/intraday/{symbol}/simulation")
def read_intraday_simulation(symbol: str, session_id: str | None = None) -> dict[str, object]:
    """Return one synthetic intraday simulation."""

    bars, load_issues = _load_intraday_bars_or_404(symbol, session_id)
    result = intraday_simulator.run(bars)
    data = result.model_dump(mode="json")
    data["load_quality_issues"] = [issue.model_dump(mode="json") for issue in load_issues]
    return data


@app.get("/intraday/{symbol}/simulation/card", response_class=Response)
def read_intraday_simulation_card(symbol: str, session_id: str | None = None) -> Response:
    """Return one synthetic intraday simulation card as Markdown."""

    bars, _load_issues = _load_intraday_bars_or_404(symbol, session_id)
    result = intraday_simulator.run(bars)
    return Response(content=intraday_simulation_to_markdown_card(result), media_type="text/plain")


@app.get("/intraday/prop-account/sample")
def read_intraday_prop_account_sample() -> dict[str, object]:
    """Return generic prop-account-style scaling arithmetic."""

    return sample_prop_account_result().model_dump(mode="json")


@app.get("/intraday/prop-account/sample/card", response_class=Response)
def read_intraday_prop_account_sample_card() -> Response:
    """Return generic prop-account-style scaling arithmetic as Markdown."""

    return Response(
        content=prop_account_to_markdown_card(sample_prop_account_result()),
        media_type="text/plain",
    )


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
    intraday_sessions = intraday_fixture_provider.list_available_sessions()
    historical_sessions = historical_intraday_provider.list_sessions()
    firstrate_dry_run = firstrate_historical_provider.dry_run()
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
            "intraday_session_count": len(intraday_sessions),
            "historical_session_count": len(historical_sessions),
            "firstrate_files_found": firstrate_dry_run.files_found,
            "firstrate_symbols": firstrate_dry_run.symbols_detected,
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


@app.get("/ui/intraday-lab", response_class=HTMLResponse)
def read_ui_intraday_lab(request: Request) -> Response:
    """Render the local intraday research spike landing page."""

    return templates.TemplateResponse(
        request=request,
        name="intraday_lab.html",
        context={
            "instruments": intraday_fixture_provider.list_instruments(),
            "sessions": intraday_fixture_provider.list_available_sessions(),
            "firstrate_dry_run": firstrate_historical_provider.dry_run(),
        },
    )


@app.get("/ui/intraday-lab/prop-account-scaling", response_class=HTMLResponse)
def read_ui_intraday_prop_account_scaling(request: Request) -> Response:
    """Render the generic prop-account scaling page."""

    result = sample_prop_account_result()
    return templates.TemplateResponse(
        request=request,
        name="intraday_prop_account_scaling.html",
        context={
            "result": result,
            "card": prop_account_to_markdown_card(result),
        },
    )


@app.get("/ui/intraday-lab/replay", response_class=HTMLResponse)
def read_ui_historical_replay_landing(request: Request) -> Response:
    """Render the historical replay landing page."""

    result = historical_intraday_provider.load_all_sessions()
    return templates.TemplateResponse(
        request=request,
        name="intraday_replay.html",
        context={
            "sessions": result.sessions,
            "quality_issues": result.quality_issues,
        },
    )


@app.get("/ui/intraday-lab/replay/{symbol}/{session_id}", response_class=HTMLResponse)
def read_ui_historical_replay_detail(
    request: Request,
    symbol: str,
    session_id: str,
) -> Response:
    """Render one historical replay story."""

    replay_request = HistoricalReplayRequest(symbol=symbol, session_id=session_id)
    result = historical_replay_engine.replay(replay_request)
    return templates.TemplateResponse(
        request=request,
        name="intraday_replay_detail.html",
        context={
            "result": result,
            "card": historical_replay_to_markdown_card(result),
        },
    )


@app.get("/ui/intraday-lab/multi-session-summary", response_class=HTMLResponse)
def read_ui_multi_session_summary(request: Request) -> Response:
    """Render the many-morning practice test page."""

    summary = multi_session_pattern_runner.run()
    return templates.TemplateResponse(
        request=request,
        name="intraday_multi_session_summary.html",
        context={"summary": summary, "card": multi_session_replay_to_markdown_card(summary)},
    )


@app.get("/ui/intraday-lab/pattern-results", response_class=HTMLResponse)
def read_ui_pattern_results(request: Request) -> Response:
    """Render repeated pattern results."""

    summary = multi_session_pattern_runner.run()
    return templates.TemplateResponse(
        request=request,
        name="intraday_pattern_results.html",
        context={"summary": summary, "card": multi_session_replay_to_markdown_card(summary)},
    )


@app.get("/ui/intraday-lab/no-trade-analysis", response_class=HTMLResponse)
def read_ui_no_trade_analysis(request: Request) -> Response:
    """Render sit-out review."""

    summary = multi_session_pattern_runner.run()
    return templates.TemplateResponse(
        request=request,
        name="intraday_no_trade_analysis.html",
        context={"summary": summary, "card": multi_session_replay_to_markdown_card(summary)},
    )


@app.get("/ui/intraday-lab/firstrate", response_class=HTMLResponse)
def read_ui_firstrate_landing(request: Request) -> Response:
    """Render the FirstRate local study landing page."""

    provider = _firstrate_replay_provider()
    dry_run = firstrate_historical_provider.dry_run()
    completeness = provider.first_hour_completeness_for_sessions()
    symbol_summaries = [
        _firstrate_symbol_summary(provider, symbol) for symbol in dry_run.symbols_detected
    ]
    return templates.TemplateResponse(
        request=request,
        name="firstrate_landing.html",
        context={
            "dry_run": dry_run,
            "completeness_summary": summarize_first_hour_completeness(completeness),
            "symbol_summaries": symbol_summaries,
        },
    )


@app.get("/ui/intraday-lab/firstrate/{symbol}/multi-session-summary", response_class=HTMLResponse)
def read_ui_firstrate_multi_session_summary(request: Request, symbol: str) -> Response:
    """Render the FirstRate many-morning page for one symbol."""

    summary, completeness, completeness_summary, cache_metadata = _firstrate_multi_session_summary(
        symbol=symbol
    )
    return templates.TemplateResponse(
        request=request,
        name="firstrate_multi_session_summary.html",
        context={
            "symbol": symbol.strip().upper(),
            "summary": summary,
            "completeness": completeness,
            "completeness_summary": completeness_summary,
            "cache_metadata": cache_metadata,
            "card": multi_session_replay_to_markdown_card(summary),
        },
    )


@app.get("/ui/intraday-lab/firstrate/{symbol}/{session_id}/replay", response_class=HTMLResponse)
def read_ui_firstrate_replay_detail(
    request: Request,
    symbol: str,
    session_id: str,
) -> Response:
    """Render one FirstRate replay story."""

    result, completeness = _firstrate_replay_result(symbol=symbol, session_id=session_id)
    return templates.TemplateResponse(
        request=request,
        name="firstrate_replay_detail.html",
        context={
            "result": result,
            "completeness": completeness,
            "card": historical_replay_to_markdown_card(result),
        },
    )


@app.get("/ui/intraday-lab/firstrate/{symbol}", response_class=HTMLResponse)
def read_ui_firstrate_symbol(request: Request, symbol: str) -> Response:
    """Render one FirstRate symbol study page."""

    provider = _firstrate_replay_provider()
    summary = _firstrate_symbol_summary(provider, symbol)
    if summary["sessions_found"] == 0:
        raise HTTPException(status_code=404, detail="FirstRate symbol not found")
    sessions = provider.list_sessions(symbol)
    completeness = provider.first_hour_completeness_for_sessions(symbol)
    return templates.TemplateResponse(
        request=request,
        name="firstrate_symbol.html",
        context={
            "symbol": symbol.strip().upper(),
            "summary": summary,
            "sessions": sessions,
            "completeness": completeness,
            "completeness_summary": summarize_first_hour_completeness(completeness),
        },
    )


@app.get("/ui/intraday-lab/{symbol}", response_class=HTMLResponse)
def read_ui_intraday_symbol(
    request: Request, symbol: str, session_id: str | None = None
) -> Response:
    """Render one synthetic intraday research view."""

    bars, load_issues = _load_intraday_bars_or_404(symbol, session_id)
    benchmarks = calculate_opening_benchmarks(bars)
    events = intraday_setup_detector.detect_events(bars, benchmarks)
    setups = intraday_setup_detector.detect_setups(bars, benchmarks)
    result = intraday_simulator.run(bars)
    return templates.TemplateResponse(
        request=request,
        name="intraday_symbol.html",
        context={
            "symbol": benchmarks.symbol,
            "session_id": benchmarks.session_id,
            "sessions": intraday_fixture_provider.list_available_sessions(benchmarks.symbol),
            "benchmarks": benchmarks,
            "events": events,
            "setups": setups,
            "simulation_result": result,
            "quality_issues": [*load_issues, *benchmarks.quality_issues, *result.quality_issues],
            "card": intraday_simulation_to_markdown_card(result),
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
        "Phase 7X intraday research spike",
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


def _load_intraday_bars_or_404(
    symbol: str, session_id: str | None = None
) -> tuple[list[IntradayBar], list[IntradayQualityIssue]]:
    bars, issues = intraday_fixture_provider.load_bars(symbol, session_id)
    if not bars and any(issue.code in {"missing_symbol", "missing_session"} for issue in issues):
        raise HTTPException(status_code=404, detail="Intraday fixture not found")
    return bars, issues


def _historical_import_response(
    result: HistoricalIntradayImportResult, *, include_bars: bool
) -> dict[str, object]:
    response: dict[str, object] = {
        "source": result.source.model_dump(mode="json"),
        "instruments": [instrument.model_dump(mode="json") for instrument in result.instruments],
        "sessions": [session.model_dump(mode="json") for session in result.sessions],
        "bars_loaded": result.bars_loaded,
        "quality_issues": [issue.model_dump(mode="json") for issue in result.quality_issues],
        "plain_english_summary": result.plain_english_summary,
        "research_only_status": result.research_only_status,
        "real_money_status": result.real_money_status,
    }
    if include_bars:
        response["bars"] = [bar.model_dump(mode="json") for bar in result.bars]
    return response


def _first_ready_historical_session() -> HistoricalIntradaySession | None:
    result = historical_intraday_provider.load_all_sessions()
    return next(
        (session for session in result.sessions if session.readiness.value == "ready_for_replay"),
        None,
    )


def _multi_session_request(
    *,
    symbol: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> MultiSessionReplayRequest:
    return MultiSessionReplayRequest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )


def _firstrate_replay_provider() -> CachedFirstRateHistoricalDataProvider:
    global _firstrate_cached_provider_source, _firstrate_cached_replay_provider
    if (
        _firstrate_cached_provider_source is not firstrate_historical_provider
        or _firstrate_cached_replay_provider is None
    ):
        _firstrate_cached_provider_source = firstrate_historical_provider
        _firstrate_cached_replay_provider = CachedFirstRateHistoricalDataProvider(
            firstrate_historical_provider
        )
    return _firstrate_cached_replay_provider


def _firstrate_replay_result(
    *,
    symbol: str,
    session_id: str,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> tuple[HistoricalReplayResult, FirstHourCompleteness]:
    provider = _firstrate_replay_provider()
    import_result = provider.load_session(symbol, session_id)
    if not import_result.sessions:
        raise HTTPException(status_code=404, detail="FirstRate session not found")
    engine = HistoricalIntradayReplayEngine(
        provider=provider,
        setup_detector=intraday_setup_detector,
    )
    replay_request = HistoricalReplayRequest(
        symbol=symbol,
        session_id=session_id,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    result = engine.replay(replay_request)
    completeness = first_hour_completeness_for_import_result(import_result)[0]
    return result, completeness


def _firstrate_multi_session_summary(
    *,
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> tuple[
    MultiSessionReplaySummary,
    list[FirstHourCompleteness],
    FirstHourCompletenessSummary,
    dict[str, object],
]:
    provider = _firstrate_replay_provider()
    replay_request = _multi_session_request(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    cache_key = _firstrate_multi_session_cache_key(provider, replay_request)
    cached_entry = _firstrate_multi_session_cache.get(cache_key)
    if cached_entry is not None:
        return (
            cached_entry.summary,
            cached_entry.completeness,
            cached_entry.completeness_summary,
            _firstrate_cache_metadata(cached_entry, cache_status="cached"),
        )

    started_at = perf_counter()
    engine = HistoricalIntradayReplayEngine(
        provider=provider,
        setup_detector=intraday_setup_detector,
    )
    runner = MultiSessionPatternRunner(provider=provider, replay_engine=engine)
    summary = runner.run(replay_request)
    completeness = provider.first_hour_completeness_for_sessions(symbol, start_date, end_date)
    completeness_summary = summarize_first_hour_completeness(completeness)
    entry = FirstRateMultiSessionCacheEntry(
        summary=summary,
        completeness=completeness,
        completeness_summary=completeness_summary,
        computed_at=utc_now().isoformat(),
        elapsed_ms=round((perf_counter() - started_at) * 1000),
    )
    _firstrate_multi_session_cache[cache_key] = entry
    return (
        summary,
        completeness,
        completeness_summary,
        _firstrate_cache_metadata(
            entry,
            cache_status="fresh",
        ),
    )


def _firstrate_multi_session_response(
    *,
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    hold_minutes: int = 5,
    slippage_ticks: int = 1,
    commission_per_contract: float = 0,
) -> dict[str, object]:
    summary, completeness, completeness_summary, cache_metadata = _firstrate_multi_session_summary(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        hold_minutes=hold_minutes,
        slippage_ticks=slippage_ticks,
        commission_per_contract=commission_per_contract,
    )
    response = cast(dict[str, object], summary.model_dump(mode="json"))
    response["first_hour_completeness_summary"] = completeness_summary.model_dump(mode="json")
    response["first_hour_completeness_by_session"] = [
        item.model_dump(mode="json") for item in completeness
    ]
    response["cache_metadata"] = cache_metadata
    raw_quality_issues = response.get("quality_issues", [])
    quality_issues = (
        [str(issue) for issue in raw_quality_issues] if isinstance(raw_quality_issues, list) else []
    )
    if completeness_summary.minor_gaps or completeness_summary.major_gaps:
        quality_issues.append(completeness_summary.plain_english_summary)
    if completeness_summary.replay_unsafe:
        quality_issues.append(
            "Some local FirstRate mornings have first-hour gaps that are unsafe for replay."
        )
    response["quality_issues"] = quality_issues
    return response


def _firstrate_multi_session_cache_key(
    provider: CachedFirstRateHistoricalDataProvider,
    replay_request: MultiSessionReplayRequest,
) -> FirstRateMultiSessionCacheKey:
    normalized_symbol = replay_request.symbol or ""
    file_signature = tuple(
        (item.path, item.size_bytes, item.modified_time_ns)
        for item in provider.provider.file_cache_signature()
        if not normalized_symbol
        or provider.provider.normalizer.infer_symbol_from_path(Path(item.path)) == normalized_symbol
    )
    return FirstRateMultiSessionCacheKey(
        symbol=normalized_symbol,
        start_date=replay_request.start_date,
        end_date=replay_request.end_date,
        hold_minutes=replay_request.hold_minutes,
        slippage_ticks=replay_request.slippage_ticks,
        commission_per_contract=replay_request.commission_per_contract,
        file_signature=file_signature,
    )


def _firstrate_cache_metadata(
    entry: FirstRateMultiSessionCacheEntry,
    *,
    cache_status: str,
) -> dict[str, object]:
    return {
        "cache_status": cache_status,
        "computed_at": entry.computed_at,
        "elapsed_ms": entry.elapsed_ms,
    }


def _firstrate_symbol_summary(
    provider: CachedFirstRateHistoricalDataProvider,
    symbol: str,
) -> dict[str, object]:
    sessions = provider.list_sessions(symbol)
    completeness = provider.first_hour_completeness_for_sessions(symbol)
    completeness_summary = summarize_first_hour_completeness(completeness)
    ready_sessions = [
        session for session in sessions if session.readiness.value == "ready_for_replay"
    ]
    sample_session = ready_sessions[0] if ready_sessions else sessions[0] if sessions else None
    return {
        "symbol": symbol.strip().upper(),
        "date_range": (
            f"{sessions[0].session_date.isoformat()} to {sessions[-1].session_date.isoformat()}"
            if sessions
            else "No sessions found"
        ),
        "sessions_found": len(sessions),
        "sessions_ready_for_replay": len(ready_sessions),
        "minor_gaps": completeness_summary.minor_gaps,
        "major_gaps": completeness_summary.major_gaps,
        "replay_unsafe": completeness_summary.replay_unsafe,
        "sample_session_id": sample_session.session_id if sample_session else None,
        "completeness_summary": completeness_summary,
    }
