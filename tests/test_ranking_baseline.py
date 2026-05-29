from edgelab.backtesting.schema import BacktestResult, BacktestStatus
from edgelab.discovery.library import StrategyDiscoveryLibrary
from edgelab.ranking.baseline import (
    compare_backtest_to_placeholder_baseline,
    compare_discovery_to_required_baseline,
)


def test_backtest_baseline_comparison_marks_sample_improvement() -> None:
    result = BacktestResult(
        strategy_id="relative-strength-pullback",
        symbol="SPY",
        status=BacktestStatus.COMPLETED,
        initial_capital=50_000,
        final_equity=50_500,
        total_return_pct=1.0,
        max_drawdown_pct=1.0,
        trade_count=3,
        winning_trade_count=2,
        losing_trade_count=1,
        win_rate_pct=66.7,
        average_win_pct=1.0,
        average_loss_pct=-0.5,
        profit_factor=2.0,
        exposure_pct=40.0,
    )

    comparison = compare_backtest_to_placeholder_baseline(
        result,
        "Simple sample baseline",
    )

    assert comparison.did_candidate_beat_baseline is True
    assert "too thin to trust" in comparison.improvement_summary


def test_discovery_baseline_comparison_is_requirement_not_success_claim() -> None:
    record = StrategyDiscoveryLibrary.with_samples().get("broad-fear-company-calm-pullback")
    assert record is not None

    comparison = compare_discovery_to_required_baseline(record)

    assert comparison.did_candidate_beat_baseline is False
    assert comparison.baseline_id == "relative-strength-pullback"
    assert "requirement" in comparison.caution
