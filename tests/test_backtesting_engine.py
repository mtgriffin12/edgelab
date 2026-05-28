from datetime import UTC, datetime

from edgelab.backtesting.engine import BacktestEngine
from edgelab.backtesting.schema import (
    BacktestRequest,
    BacktestStatus,
    ExecutionAssumptions,
)
from edgelab.data.market_data import LocalFixtureMarketDataProvider
from edgelab.data.schema import BarInterval, OHLCVBar
from edgelab.strategies.registry import StrategyRegistry


def load_strategy(strategy_id: str = "relative-strength-pullback"):
    strategy = StrategyRegistry.with_samples().get(strategy_id)
    assert strategy is not None
    return strategy


def load_bars(symbol: str = "SPY") -> list[OHLCVBar]:
    data = LocalFixtureMarketDataProvider().load_bars(symbol)
    assert data.quality_issues == []
    return data.bars


def build_bar(timestamp: datetime, close: float, open_price: float | None = None) -> OHLCVBar:
    base_open = open_price if open_price is not None else close
    return OHLCVBar(
        symbol="TEST",
        timestamp=timestamp,
        interval=BarInterval.DAILY,
        open=base_open,
        high=max(base_open, close) + 1,
        low=min(base_open, close) - 1,
        close=close,
        volume=1000,
        adjusted_close=close,
        source="synthetic_fixture",
        ingested_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def test_engine_runs_with_synthetic_fixture_bars() -> None:
    result = BacktestEngine().run(
        load_strategy(),
        load_bars(),
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY"),
    )

    assert result.status == BacktestStatus.COMPLETED
    assert result.strategy_id == "relative-strength-pullback"
    assert result.symbol == "SPY"
    assert result.trade_count == 1
    assert result.equity_curve
    assert result.conclusion == "research_only"


def test_engine_rejects_unsupported_strategy() -> None:
    result = BacktestEngine().run(
        load_strategy("earnings-drift-with-confirmation"),
        load_bars(),
        BacktestRequest(strategy_id="earnings-drift-with-confirmation", symbol="SPY"),
    )

    assert result.status == BacktestStatus.UNSUPPORTED_STRATEGY
    assert result.trade_count == 0
    assert result.quality_issues[0].code == "unsupported_strategy"


def test_engine_uses_next_bar_execution_without_lookahead() -> None:
    result = BacktestEngine().run(
        load_strategy(),
        load_bars(),
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY"),
    )

    first_trade = result.trades[0]
    assert first_trade.entry_fill.timestamp == datetime(2024, 1, 5, tzinfo=UTC)


def test_engine_respects_max_position_pct() -> None:
    assumptions = ExecutionAssumptions(initial_capital=10_000, max_position_pct=0.10)
    result = BacktestEngine().run(
        load_strategy(),
        load_bars(),
        BacktestRequest(
            strategy_id="relative-strength-pullback",
            symbol="SPY",
            initial_capital=10_000,
            execution_assumptions=assumptions,
        ),
    )

    entry = result.trades[0].entry_fill
    assert entry.quantity * entry.price <= 1000.01


def test_commission_and_slippage_reduce_results() -> None:
    engine = BacktestEngine()
    bars = load_bars()
    strategy = load_strategy()
    no_cost = engine.run(
        strategy,
        bars,
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY"),
    )
    with_cost = engine.run(
        strategy,
        bars,
        BacktestRequest(
            strategy_id="relative-strength-pullback",
            symbol="SPY",
            execution_assumptions=ExecutionAssumptions(
                commission_per_trade=5.0,
                slippage_bps=10.0,
            ),
        ),
    )

    assert with_cost.final_equity < no_cost.final_equity


def test_no_trade_case_returns_insufficient_evidence() -> None:
    bars = [
        build_bar(datetime(2024, 1, 1, tzinfo=UTC), close=10),
        build_bar(datetime(2024, 1, 2, tzinfo=UTC), close=9),
        build_bar(datetime(2024, 1, 3, tzinfo=UTC), close=8),
    ]
    result = BacktestEngine().run(
        load_strategy(),
        bars,
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="TEST"),
    )

    assert result.status == BacktestStatus.COMPLETED
    assert result.trade_count == 0
    assert result.conclusion == "insufficient_evidence"


def test_backtest_result_shape_includes_logs_and_metrics() -> None:
    result = BacktestEngine().run(
        load_strategy(),
        load_bars(),
        BacktestRequest(strategy_id="relative-strength-pullback", symbol="SPY"),
    )

    assert result.final_equity > 0
    assert result.total_return_pct != 0
    assert result.max_drawdown_pct >= 0
    assert result.winning_trade_count + result.losing_trade_count <= result.trade_count
    assert result.win_rate_pct >= 0
    assert result.profit_factor is None or result.profit_factor >= 0
    assert result.trades[0].entry_fill.side == "buy"
    assert result.trades[0].exit_fill.side == "sell"
    assert len(result.equity_curve) == len(load_bars())
